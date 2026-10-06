import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from backend.api.deps import llm_client
from backend.schemas.rag import SearchRequest, SearchResponse, AskRequest, AskResponse
from backend.services import rag_service

router = APIRouter()


# ⚠️ rag_search / rag_ask 刻意用普通 def：
# 它们内部是同步阻塞调用（向量检索 + BM25 + 硅基流动的 embedding/rerank + 大模型生成），
# 写成 async def 会**阻塞整个事件循环** —— 一个人提问，其他人连页面静态资源都得排队。
# 普通 def 会被 FastAPI 丢进线程池并发执行。（下面的流式接口不同：它返回同步生成器，
# Starlette 本来就会在线程池里迭代，所以那边保持 async def 反而是对的。）


@router.post("/rag/search", response_model=SearchResponse)
def rag_search(req: SearchRequest):
    try:
        results = rag_service.search(req.query, top_k=req.top_k)
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/ask", response_model=AskResponse)
def rag_ask(req: AskRequest, client=Depends(llm_client)):
    try:
        result = rag_service.ask(req.query, client=client)
        return AskResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/ask/stream")
async def rag_ask_stream(req: AskRequest, client=Depends(llm_client)):
    def generate():
        try:
            # sources 由 rag_service 真实产出（原先是这里固定发空数组，导致前端
            # 「参考来源」面板永远是死代码）；生成失败也会作为 error 事件发出。
            for event in rag_service.ask_stream_events(req.query, client=client):
                yield json.dumps(event, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "data": str(e)}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
