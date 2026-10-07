"""检索与问答。

⚠️ rag_search / rag_ask 刻意用普通 def：内部是同步阻塞调用（向量检索 + BM25 +
硅基流动的 embedding / rerank + 大模型生成），写成 async def 会**阻塞整个事件循环** ——
一个人提问，其他人连页面静态资源都得排队。普通 def 会被 FastAPI 丢进线程池并发执行。
（流式接口不同：它返回同步生成器，Starlette 本来就在线程池里迭代，所以那边保持 async def 是对的。）

**每个提问都会在服务端留一条记录**（query_logs 表）：站长能在后台看到谁问了什么、
哪些问题没答上来。记录失败绝不影响问答本身（见 _record）。
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.api.deps import current_user_optional, llm_client
from backend.api.ratelimit import client_ip
from backend.models.database import SessionLocal
from backend.models.user import User
from backend.schemas.rag import (
    AskRequest, AskResponse, FeedbackRequest, SearchRequest, SearchResponse,
)
from backend.schemas.user import OkResponse
from backend.services import admin_service, rag_service

router = APIRouter()


def _record(request: Request, user: Optional[User], kind: str, query: str,
            results) -> Optional[int]:
    """记一条提问，返回记录 id（前端「没解决」按钮要拿它回传）。

    自己开 session 而不是用请求级的 Depends(get_db)：流式响应是在依赖清理之后才迭代完的，
    那时请求级 session 可能已经关了。**任何异常都吞掉** —— 这是日志，
    不该让用户的问答跟着失败。
    """
    try:
        db = SessionLocal()
        try:
            top = 0.0
            if results:
                top = float((results[0] or {}).get("score") or 0.0)
            row = admin_service.log_query(
                db, ip=client_ip(request), user=user, kind=kind, query=query,
                sources_count=len(results or []), top_score=top, sources=results)
            return row.id if row else None
        finally:
            db.close()
    except Exception as e:
        print(f"[querylog] 记录失败（不影响问答）：{e}")
        return None


@router.post("/rag/search", response_model=SearchResponse)
def rag_search(req: SearchRequest, request: Request,
               user: Optional[User] = Depends(current_user_optional)):
    q = (req.query or "").strip()
    # 空查询以前会照常跑一遍检索（白白烧一次 embedding + rerank 额度），
    # 现在直接拦住并给人话提示
    if not q:
        raise HTTPException(status_code=400, detail="先输入要查的内容")
    try:
        results = rag_service.search(q, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    log_id = _record(request, user, "search", q, results)
    return SearchResponse(results=results, query_log_id=log_id)


@router.post("/rag/ask", response_model=AskResponse)
def rag_ask(req: AskRequest, request: Request,
            user: Optional[User] = Depends(current_user_optional),
            client=Depends(llm_client)):
    q = (req.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="先输入要问的问题")
    try:
        result = rag_service.ask(q, client=client)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    log_id = _record(request, user, "ask", q, result.get("sources") or [])
    return AskResponse(answer=result["answer"], sources=result["sources"],
                       query_log_id=log_id)


@router.post("/rag/ask/stream")
async def rag_ask_stream(req: AskRequest, request: Request,
                         user: Optional[User] = Depends(current_user_optional),
                         client=Depends(llm_client)):
    q = (req.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="先输入要问的问题")

    def generate():
        log_id = None
        recorded = False
        try:
            for event in rag_service.ask_stream_events(q, client=client):
                # sources 事件一出来就先记账 —— 不等生成完（生成可能中途失败），
                # 而且"有没有召回来源"正是判断答没答上来的关键。
                if not recorded and event.get("type") == "sources":
                    log_id = _record(request, user, "ask_stream", q,
                                     event.get("data") or [])
                    recorded = True
                yield json.dumps(event, ensure_ascii=False) + "\n"
            if not recorded:      # 检索阶段就炸了、连 sources 都没发 —— 也要留痕
                log_id = _record(request, user, "ask_stream", q, [])
            yield json.dumps({"type": "done", "query_log_id": log_id},
                             ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "data": str(e)}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done", "query_log_id": log_id},
                             ensure_ascii=False) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/rag/feedback", response_model=OkResponse)
def rag_feedback(req: FeedbackRequest, request: Request,
                 user: Optional[User] = Depends(current_user_optional)):
    """「这个问题没解决」—— 用户说了算，比阈值判断更可信。

    只允许反馈自己提的问题：同一个账号，或同一个 IP（未登录时）。
    """
    from backend.models.admin import QueryLog

    db = SessionLocal()
    try:
        row = db.query(QueryLog).filter(QueryLog.id == req.query_log_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="找不到这条提问记录")
        my_ip = admin_service.normalize_ip(client_ip(request))
        if not ((user and row.user_id == user.id) or (my_ip and row.ip == my_ip)):
            raise HTTPException(status_code=403, detail="只能反馈自己刚提的问题")
        admin_service.mark_feedback(db, row.id, kind=req.kind, reason=req.reason)
        msg = {
            "solved": "好，那我们继续",
            "irrelevant": "已记下：这些来源不相关 —— 谢谢，这正是我们要改进的地方",
        }.get(req.kind, "已记下：这个问题没解决，我们会想办法补上")
        return OkResponse(message=msg)
    finally:
        db.close()
