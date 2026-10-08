"""用户主动反馈：顶部栏「反馈」按钮。

与提问记录的分工：
  · QueryLog    = 「用户问了什么」—— 系统自动记，用来抓答不上来的问题；
  · UserFeedback = 「用户主动想说什么」—— 哪里不足、哪里不顺手、哪里报错，
                   这类信息日志里永远不会有，只能靠用户开口。

入口只给**登录用户**看（达铭的要求），服务端同样要求登录 —— 界面藏起来不算权限控制。
提交接口挂在限流里（`/api/feedback`）：正常没人一分钟发 50 条。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.api.deps import current_admin, current_user
from backend.api.ratelimit import client_ip
from backend.models.database import get_db
from backend.models.user import User
from backend.schemas.admin import FeedbackCreate, UserFeedbackPage, UserFeedbackRow
from backend.schemas.user import OkResponse
from backend.services import admin_service, attachment_service

router = APIRouter()

MAX_LEN = 4000


@router.post("/feedback", response_model=OkResponse)
def submit_feedback(req: FeedbackCreate, request: Request,
                    user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    content = (req.content or "").strip()
    if len(content) < 2:
        raise HTTPException(status_code=400, detail="再多写两个字吧，不然我们看不懂你想说什么")
    if len(content) > MAX_LEN:
        raise HTTPException(status_code=400, detail=f"太长了（上限 {MAX_LEN} 字），捡重点说就行")
    try:
        row = admin_service.log_user_feedback(
            db, user=user, ip=client_ip(request), content=content,
            category=req.category, page=req.page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"没存上（{str(e)[:80]}），稍后再试一次")

    # 两段式的第二段：把先上传的那批附件绑到这条反馈上
    # （只绑自己的、且还没绑过的 —— 规则在 attachment_service.bind 里）
    n = attachment_service.bind(db, user, req.attachment_ids,
                                source="feedback", ref_id=getattr(row, "id", None)) if row else 0
    tail = f"，收到了 {n} 个附件" if n else ""
    return OkResponse(message=f"收到，谢谢！站长能看到这条反馈{tail}。")


# ---------------------------------------------------------------- 管理端
@router.get("/admin/feedback", response_model=UserFeedbackPage)
def list_feedback(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
                  only_unhandled: bool = Query(False), category: str = Query(""),
                  admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    total, unhandled, rows = admin_service.list_user_feedback(
        db, page=page, page_size=page_size, only_unhandled=only_unhandled, category=category)
    return UserFeedbackPage(
        total=total, unhandled=unhandled, page=page, page_size=page_size,
        items=[UserFeedbackRow(
            id=r.id, created_at=r.created_at, user_id=r.user_id, username=r.username or "",
            ip=r.ip or "", category=r.category or "其他", content=r.content,
            page=r.page or "", handled=bool(r.handled), handled_at=r.handled_at,
            handled_by=r.handled_by or "",
            # 用户投递的附件 —— 站长点一下就能下载（这就是「收技术档案」的落地处）
            attachments=attachment_service.briefs_for(db, "feedback", r.id),
        ) for r in rows],
    )


@router.post("/admin/feedback/{fid}/handle", response_model=OkResponse)
def handle_feedback(fid: int, handled: bool = Query(True),
                    admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    if not admin_service.mark_user_feedback_handled(db, fid, handled=handled,
                                                    by=admin.username):
        raise HTTPException(status_code=404, detail="没有这条反馈")
    return OkResponse(message="已标记为处理过了" if handled else "已改回未处理")


@router.delete("/admin/feedback/{fid}", response_model=OkResponse)
def delete_feedback(fid: int, admin: User = Depends(current_admin),
                    db: Session = Depends(get_db)):
    if not admin_service.delete_user_feedback(db, fid):
        raise HTTPException(status_code=404, detail="没有这条反馈")
    return OkResponse(message="已删除")
