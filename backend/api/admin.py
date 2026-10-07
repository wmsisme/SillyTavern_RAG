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
    DeleteQueriesRequest, IpBanRow, LoginIpRow, MarkQueriesRequest, QueryLogPage,
    QueryLogRow, UserCardBrief, UserContentOut, UserWorldBookBrief,
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


@router.get("/admin/users/{uid}/logins", response_model=list[LoginIpRow])
def user_logins(uid: int, limit: int = Query(10, ge=1, le=50),
                admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    """这个账号最近从哪些 IP 登录过 —— **判断共享账号**用。

    一个账号短时间内从好几个不同 IP 登录，通常就是「一个人开号、一群人用」。
    """
    _find_user(db, uid)                 # 账号不存在就 404
    return [LoginIpRow(**r) for r in admin_service.login_ip_summary(db, uid, limit=limit)]


@router.get("/admin/users/{uid}/content", response_model=UserContentOut)
def user_content(uid: int, admin: User = Depends(current_admin),
                 db: Session = Depends(get_db)):
    """看某个用户建了哪些角色卡 / 世界书。

    ⚠️ 这是**管理员特权**：普通用户之间「只有本人能看到自己的东西」那条规则不变
    （业务接口照旧按 user_id 过滤），但站长要能查违规内容。
    """
    user = _find_user(db, uid)
    from backend.models.character_card import CharacterCard
    from backend.models.world_book import WorldBook

    def _tags(v) -> str:
        if isinstance(v, list):
            return "、".join(str(x) for x in v[:6])
        return str(v or "")[:80]

    cards = (db.query(CharacterCard).filter(CharacterCard.user_id == uid)
               .order_by(CharacterCard.id.desc()).all())
    wbs = (db.query(WorldBook).filter(WorldBook.user_id == uid)
             .order_by(WorldBook.id.desc()).all())
    return UserContentOut(
        user_id=uid,
        username=user.username,
        cards=[UserCardBrief(id=c.id, name=c.name, tags=_tags(c.tags),
                             has_image=bool(c.image_path), updated_at=c.updated_at)
               for c in cards],
        worldbooks=[UserWorldBookBrief(
            id=w.id, name=w.name,
            entries=len(w.entries) if isinstance(w.entries, list) else 0,
            updated_at=w.updated_at) for w in wbs],
    )


@router.get("/admin/cards/{cid}")
def admin_card_detail(cid: int, admin: User = Depends(current_admin),
                      db: Session = Depends(get_db)):
    """看某张角色卡的**完整内容**（查违规内容用）。

    ⚠️ 只返回**中性字段** —— 各版本可能不存在的列一律不碰，引用它们会直接报错。
    """
    from backend.models.character_card import CharacterCard
    card = db.query(CharacterCard).filter(CharacterCard.id == cid).first()
    if not card:
        raise HTTPException(status_code=404, detail="角色卡不存在")
    return {
        "id": card.id, "user_id": card.user_id, "name": card.name,
        "age": card.age or "", "gender": card.gender or "",
        "species": card.species or "", "occupation": card.occupation or "",
        "appearance": card.appearance or "", "personality": card.personality or "",
        "background": card.background or "", "description": card.description or "",
        "tags": card.tags or [],
        "has_status_bar": bool(card.has_status_bar),
        "status_bar_content": card.status_bar_content or "",
        "first_message": card.first_message or "",
        "has_image": bool(card.image_path),
        "created_at": card.created_at, "updated_at": card.updated_at,
    }


@router.get("/admin/worldbooks/{wid}")
def admin_worldbook_detail(wid: int, admin: User = Depends(current_admin),
                           db: Session = Depends(get_db)):
    """看某本世界书的**完整内容**（含全部条目）。"""
    from backend.models.world_book import WorldBook
    wb = db.query(WorldBook).filter(WorldBook.id == wid).first()
    if not wb:
        raise HTTPException(status_code=404, detail="世界书不存在")
    return {
        "id": wb.id, "user_id": wb.user_id, "name": wb.name,
        "description": wb.description or "",
        "tags": wb.tags or [],
        "entries": wb.entries or [],
        "created_at": wb.created_at, "updated_at": wb.updated_at,
    }


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
            marked_only: bool = Query(False),
            admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    total, rows = admin_service.list_queries(
        db, page=page, page_size=page_size, only_unanswered=only_unanswered,
        ip=ip, username=username, kind=kind, feedback=feedback, marked_only=marked_only)
    return QueryLogPage(
        total=total, page=page, page_size=page_size,
        items=[QueryLogRow(
            id=r.id, created_at=r.created_at, ip=r.ip or "", user_id=r.user_id,
            username=r.username or "", kind=r.kind or "search", query=r.query,
            sources_count=r.sources_count or 0, top_score=r.top_score or 0.0,
            answered=bool(r.answered), feedback=r.feedback or "",
            feedback_reason=r.feedback_reason or "", feedback_at=r.feedback_at,
            sources_digest=r.sources_digest or "",
            marked=bool(r.marked), marked_at=r.marked_at,
            repeat_count=int(r.repeat_count or 1),
        ) for r in rows],
    )


@router.post("/admin/queries/mark", response_model=OkResponse)
def mark_queries(req: MarkQueriesRequest, admin: User = Depends(current_admin),
                 db: Session = Depends(get_db)):
    """勾选 / 取消勾选「这条要拿去更新知识库」。

    **勾选权刻意留在人手上** —— 用户随便问一句就自动灌库，
    会把知识库污染成一堆"用户随口一问"的转录。
    """
    n = admin_service.mark_queries(db, req.ids, marked=req.marked)
    if req.marked:
        return OkResponse(message=f"已把 {n} 条加入待更新清单（点『只看待更新』能看回来）")
    return OkResponse(message=f"已把 {n} 条移出待更新清单")


@router.post("/admin/queries/delete", response_model=OkResponse)
def delete_queries(req: DeleteQueriesRequest, admin: User = Depends(current_admin),
                   db: Session = Depends(get_db)):
    """按 id 删除若干条提问记录 —— 站长清理自己测试痕迹用。"""
    n = admin_service.delete_queries(db, req.ids)
    if not n:
        return OkResponse(message="没有匹配的记录（可能已经被删过）")
    return OkResponse(message=f"已删除 {n} 条提问记录")


@router.get("/admin/queries/export")
def export_queries(marked_only: bool = Query(True), admin: User = Depends(current_admin),
                   db: Session = Depends(get_db)):
    """导出待更新清单（Markdown）：前端直接下载，也方便整份拿来处理。"""
    from fastapi.responses import PlainTextResponse
    text = admin_service.export_update_queue(db, only_marked=marked_only)
    return PlainTextResponse(
        text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="update-queue.md"'},
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
