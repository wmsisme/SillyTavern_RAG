"""后台管理接口（除「没解决」反馈外，全部只对管理员开放）。

看什么 + 管什么：
  · /admin/overview     一眼看全站状态（用户/卡片/提问/未解答/封禁数）
  · /admin/users        用户列表（含会话数、提问数、最后提问时间）
  · /admin/users/{id}/ban|unban|make-admin
  · /admin/ip-bans      封 IP / 解封 / 列表
  · /admin/active-ips   最近活跃 IP —— **共享账号的线索在这里**（一个 IP 上多个账号）
  · /admin/queries      提问记录（可只看"没答上来"的）
  · /admin/queries/clear 清理记录

保护措施：
  · 不能封自己（否则一键把自己锁在门外）；
  · 环回地址不能被封（service 层拦截，见 admin_service.IP_WHITELIST）；
  · 万一真被锁在外面，还有 CLI 兜底：`python tools/manage_users.py --unban-ip <ip>`。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import current_admin
from backend.models.admin import QueryLog
from backend.models.database import get_db
from backend.models.user import User
from backend.schemas.admin import (
    ActiveIpRow, AdminOverview, AdminUserRow, BanIpRequest, BanRequest,
    IpBanRow, QueryLogPage, QueryLogRow,
)
from backend.schemas.user import OkResponse
from backend.services import admin_service

router = APIRouter()


def _find_user(db: Session, uid: int) -> User:
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="没有这个账号")
    return user


@router.get("/admin/overview", response_model=AdminOverview)
def overview(admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    return AdminOverview(**admin_service.overview(db))


@router.get("/admin/users", response_model=list[AdminUserRow])
def users(admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    return [AdminUserRow(**r) for r in admin_service.user_rows(db)]


@router.post("/admin/users/{uid}/ban", response_model=OkResponse)
def ban_user(uid: int, req: BanRequest, admin: User = Depends(current_admin),
             db: Session = Depends(get_db)):
    if uid == admin.id:
        raise HTTPException(status_code=400, detail="不能封自己")
    user = _find_user(db, uid)
    killed = admin_service.ban_user(db, user, reason=req.reason, kick_sessions=req.kick_sessions)
    why = f"（原因：{user.ban_reason}）" if user.ban_reason else ""
    return OkResponse(message=f"已封禁 {user.username}{why}，顺带踢掉 {killed} 个在线会话")


@router.post("/admin/users/{uid}/unban", response_model=OkResponse)
def unban_user(uid: int, admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    user = _find_user(db, uid)
    admin_service.unban_user(db, user)
    return OkResponse(message=f"已解封 {user.username}，他可以用原密码重新登录")


@router.post("/admin/users/{uid}/make-admin", response_model=OkResponse)
def make_admin(uid: int, admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    user = _find_user(db, uid)
    if user.is_admin:
        return OkResponse(message=f"{user.username} 本来就是管理员")
    user.is_admin = True
    db.commit()
    return OkResponse(message=f"已把 {user.username} 设为管理员")


@router.get("/admin/ip-bans", response_model=list[IpBanRow])
def ip_bans(include_expired: bool = Query(False), admin: User = Depends(current_admin),
            db: Session = Depends(get_db)):
    from datetime import datetime
    now = datetime.now()
    out = []
    for b in admin_service.list_ip_bans(db, include_expired=include_expired):
        out.append(IpBanRow(
            id=b.id, ip=b.ip, reason=b.reason or "", created_by=b.created_by or "",
            created_at=b.created_at, expires_at=b.expires_at,
            expired=bool(b.expires_at and b.expires_at < now),
        ))
    return out


@router.post("/admin/ip-bans", response_model=OkResponse)
def add_ip_ban(req: BanIpRequest, admin: User = Depends(current_admin),
               db: Session = Depends(get_db)):
    try:
        row = admin_service.ban_ip(db, req.ip, reason=req.reason,
                                   created_by=admin.username, days=req.days)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    tail = f"，{req.days} 天后自动解封" if row.expires_at else "（永久）"
    return OkResponse(message=f"已封禁 IP {row.ip}{tail}")


@router.delete("/admin/ip-bans/{ban_id}", response_model=OkResponse)
def remove_ip_ban(ban_id: int, admin: User = Depends(current_admin),
                  db: Session = Depends(get_db)):
    if not admin_service.unban_ip(db, ban_id):
        raise HTTPException(status_code=404, detail="没有这条封禁记录")
    return OkResponse(message="已解封该 IP")


@router.get("/admin/active-ips", response_model=list[ActiveIpRow])
def active_ips(days: int = Query(7, ge=1, le=365), limit: int = Query(50, ge=1, le=200),
               admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    return [ActiveIpRow(**r) for r in admin_service.active_ips(db, days=days, limit=limit)]


@router.get("/admin/queries", response_model=QueryLogPage)
def queries(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
            only_unanswered: bool = Query(False), ip: str = Query(""),
            username: str = Query(""), kind: str = Query(""), feedback: str = Query(""),
            admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    total, rows = admin_service.list_queries(
        db, page=page, page_size=page_size, only_unanswered=only_unanswered,
        ip=ip, username=username, kind=kind, feedback=feedback)
    return QueryLogPage(
        total=total, page=page, page_size=page_size,
        items=[QueryLogRow(
            id=r.id, created_at=r.created_at, ip=r.ip or "", user_id=r.user_id,
            username=r.username or "", kind=r.kind or "search", query=r.query,
            sources_count=r.sources_count or 0, top_score=r.top_score or 0.0,
            answered=bool(r.answered), feedback=r.feedback or "",
            feedback_reason=r.feedback_reason or "", feedback_at=r.feedback_at,
            sources_digest=r.sources_digest or "",
        ) for r in rows],
    )


@router.delete("/admin/queries", response_model=OkResponse)
def clear_queries(only_unanswered: bool = Query(False), admin: User = Depends(current_admin),
                  db: Session = Depends(get_db)):
    q = db.query(QueryLog)
    if only_unanswered:
        q = q.filter(QueryLog.answered.is_(False))
    n = q.delete(synchronize_session=False)
    db.commit()
    return OkResponse(message=f"已删除 {n} 条提问记录")
