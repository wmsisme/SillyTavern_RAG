"""后台管理服务：封禁（账号 / IP）+ 提问记录。

分三层，各管各的：
  · 本文件（service）= 数据怎么存、怎么查、什么算「没答上来」
  · api/ban_guard.py = 请求进门时拦一道（被封的 IP 直接 403）
  · api/admin.py     = 只有管理员能用的 HTTP 接口

环境变量：
  UNANSWERED_THRESHOLD  最高相关度低于多少算「没答上来」，默认 0.45（改完要重启）
  QUERY_LOG_MAX         提问记录最多留多少条，默认 20000（超了从最老的开始裁）
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend.models.admin import IpBan, QueryLog
from backend.models.user import SessionToken, User

# 永远不能封的地址：环回。封了它 = 本机自己都进不来（反代场景下更是全站瘫痪）
IP_WHITELIST = {"127.0.0.1", "::1", "localhost", "localhost.localdomain", ""}


def unanswered_threshold() -> float:
    try:
        return float(os.environ.get("UNANSWERED_THRESHOLD", "") or 0.45)
    except ValueError:
        return 0.45


def _log_max() -> int:
    try:
        return int(os.environ.get("QUERY_LOG_MAX", "") or 20_000)
    except ValueError:
        return 20_000


def normalize_ip(ip: Optional[str]) -> str:
    """统一形态：去空白；IPv4-mapped IPv6（::ffff:1.2.3.4）还原成 IPv4。

    不做还原的话，同一个客户端可能以两种写法落进两条黑名单，封了也不生效。
    """
    s = (ip or "").strip()
    if s.lower().startswith("::ffff:") and "." in s:
        s = s[7:]
    return s


def is_whitelisted(ip: Optional[str]) -> bool:
    return normalize_ip(ip) in IP_WHITELIST


# ------------------------------------------------------------------ IP 黑名单
def get_active_ban(db: Session, ip: Optional[str]) -> Optional[IpBan]:
    """这个 IP 现在是否在封禁中（过期的自动不算）。"""
    ip = normalize_ip(ip)
    if not ip:
        return None
    row = db.query(IpBan).filter(IpBan.ip == ip).first()
    if not row:
        return None
    if row.expires_at and row.expires_at < datetime.now():
        return None
    return row


def ban_ip(db: Session, ip: str, reason: str = "", created_by: str = "",
           days: int = 0) -> IpBan:
    """把一个 IP 拉黑。days=0 表示永久。已存在则更新原因/时长。"""
    ip = normalize_ip(ip)
    if not ip:
        raise ValueError("IP 不能为空")
    if is_whitelisted(ip):
        raise ValueError(f"{ip} 是环回地址，封了会把全站挡在外面，已拒绝")
    expires = datetime.now() + timedelta(days=days) if days and days > 0 else None
    row = db.query(IpBan).filter(IpBan.ip == ip).first()
    if row:
        row.reason = reason or row.reason
        row.created_by = created_by or row.created_by
        row.expires_at = expires
    else:
        row = IpBan(ip=ip, reason=reason, created_by=created_by, expires_at=expires)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def unban_ip(db: Session, ban_id: int) -> bool:
    row = db.query(IpBan).filter(IpBan.id == ban_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def list_ip_bans(db: Session, include_expired: bool = False) -> List[IpBan]:
    q = db.query(IpBan).order_by(IpBan.created_at.desc(), IpBan.id.desc())
    rows = q.all()
    if include_expired:
        return rows
    now = datetime.now()
    return [r for r in rows if not (r.expires_at and r.expires_at < now)]


# ------------------------------------------------------------------ 账号封禁
def ban_user(db: Session, user: User, reason: str = "", kick_sessions: bool = True) -> int:
    """封号 = is_active 置 False（登录与已有会话都会立刻失效，见 auth_service）。

    返回被踢掉的会话数。
    """
    if user.is_admin:
        # 允许封管理员（万一要弃用一个号），但调用方要在 API 层再确认一次
        pass
    user.is_active = False
    user.ban_reason = (reason or "")[:255]
    user.banned_at = datetime.now()
    killed = 0
    if kick_sessions:
        killed = db.query(SessionToken).filter(SessionToken.user_id == user.id).delete()
    db.commit()
    return killed


def unban_user(db: Session, user: User) -> None:
    user.is_active = True
    user.ban_reason = ""
    user.banned_at = None
    db.commit()


# ------------------------------------------------------------------ 提问记录
def _digest_sources(sources) -> str:
    """把当时的检索结果压成摘要（前 5 条的 source + score）。

    为什么要存：用户事后说「这些内容不相关」时，若不知道**当时系统到底给了什么**，
    这条反馈既没法复现、也没法判断是「检索召回错了」还是「文档本身没写清楚」。
    只存来源名与分数、不存正文，一条几百字节。
    """
    items = []
    for s in (sources or [])[:5]:
        if not isinstance(s, dict):
            continue
        try:
            score = round(float(s.get("score") or 0), 4)
        except (TypeError, ValueError):
            score = 0.0
        items.append({
            "source": str(s.get("source") or "")[:120],
            "score": score,
            # 带一小段正文：光有 source 区分度不够（那是个分类名，比如 supplement），
            # 看到「当时给的到底是哪几段」才说得清是召回错了、还是文档自己没写清楚。
            "preview": " ".join(str(s.get("content") or "").split())[:80],
        })
    try:
        return json.dumps(items, ensure_ascii=False)
    except Exception:
        return ""


def log_query(db: Session, *, ip: str, user: Optional[User], kind: str, query: str,
              sources_count: int = 0, top_score: float = 0.0,
              sources=None) -> Optional[QueryLog]:
    """记一条提问。**调用方要 try/except** —— 日志写失败不许影响用户问答。"""
    text_q = (query or "").strip()
    if not text_q:
        return None
    th = unanswered_threshold()
    score = float(top_score or 0.0)
    row = QueryLog(
        created_at=datetime.now(),
        ip=normalize_ip(ip),
        user_id=user.id if user else None,
        username=user.username if user else "",
        kind=kind,
        query=text_q[:2000],
        sources_count=int(sources_count or 0),
        top_score=score,
        # 没召回任何来源，或最高分低于阈值 → 疑似没答上来
        answered=bool(sources_count and score >= th),
        sources_digest=_digest_sources(sources),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    prune_query_logs(db)
    return row


def prune_query_logs(db: Session) -> int:
    """超过上限就从最老的开始裁。返回裁掉的条数。"""
    cap = _log_max()
    total = db.query(func.count(QueryLog.id)).scalar() or 0
    if total <= cap:
        return 0
    drop = total - cap
    ids = [r[0] for r in db.query(QueryLog.id).order_by(QueryLog.id).limit(drop).all()]
    if ids:
        db.query(QueryLog).filter(QueryLog.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    return len(ids)


def list_queries(db: Session, page: int = 1, page_size: int = 50,
                 only_unanswered: bool = False, ip: str = "", username: str = "",
                 kind: str = "", feedback: str = "") -> Tuple[int, List[QueryLog]]:
    q = db.query(QueryLog)
    if only_unanswered:
        q = q.filter(QueryLog.answered.is_(False))
    if feedback:
        q = q.filter(QueryLog.feedback == feedback)
    if ip:
        q = q.filter(QueryLog.ip == normalize_ip(ip))
    if username:
        q = q.filter(QueryLog.username == username)
    if kind:
        q = q.filter(QueryLog.kind == kind)
    total = q.count()
    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    rows = (q.order_by(QueryLog.id.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    return total, rows


def active_ips(db: Session, days: int = 7, limit: int = 50) -> List[dict]:
    """最近活跃的 IP 排行 —— **共享账号的线索就在这里**：

    同一个 IP 上出现过多个不同账号，通常就是「一个人开了号分给一群人用」。
    """
    since = datetime.now() - timedelta(days=max(1, days))
    sql = text("""
        SELECT ip,
               COUNT(*)                                        AS queries,
               COUNT(DISTINCT NULLIF(username, ''))            AS users,
               GROUP_CONCAT(DISTINCT NULLIF(username, ''))     AS names,
               MAX(created_at)                                 AS last_at
        FROM query_logs
        WHERE created_at >= :since AND ip != ''
        GROUP BY ip
        ORDER BY queries DESC
        LIMIT :lim
    """)
    rows = db.execute(sql, {"since": since, "lim": limit}).fetchall()
    now = datetime.now()
    banned_ips = {r.ip for r in db.query(IpBan).all()
                  if not (r.expires_at and r.expires_at < now)}
    out = []
    for r in rows:
        out.append({
            "ip": r[0],
            "queries": r[1] or 0,
            "users": r[2] or 0,
            "usernames": (r[3] or "")[:200],
            "last_at": r[4],
            "banned": r[0] in banned_ips,
        })
    return out


FEEDBACK_KINDS = ("solved", "unsolved", "irrelevant")


def mark_feedback(db: Session, query_log_id: int, kind: str = "unsolved",
                  reason: str = "") -> bool:
    """记用户反馈。**用户说了算** —— 优先级高于阈值判断。

    · solved     → 标记为已解答（哪怕阈值判它没答上来）
    · unsolved   → 没解决，进「该补什么」的清单
    · irrelevant → **检索到内容了、但不相关**：同样进清单；
                   它最容易区分「召回给错了」还是「文档自己没写清楚」，
                   配合 sources_digest 一起看就知道当时系统给了什么。
    """
    row = db.query(QueryLog).filter(QueryLog.id == query_log_id).first()
    if not row:
        return False
    kind = (kind or "unsolved").strip().lower()
    if kind not in FEEDBACK_KINDS:
        kind = "unsolved"
    row.feedback = kind
    row.feedback_reason = (reason or "").strip()[:1000]
    row.feedback_at = datetime.now()
    row.answered = (kind == "solved")
    db.commit()
    return True


# ------------------------------------------------------------------ 概览
def overview(db: Session) -> dict:
    from backend.models.character_card import CharacterCard
    from backend.models.world_book import WorldBook

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    now = datetime.now()
    bans = db.query(IpBan).all()
    return {
        "users_total": db.query(func.count(User.id)).scalar() or 0,
        "users_banned": db.query(func.count(User.id)).filter(User.is_active.is_(False)).scalar() or 0,
        "cards_total": db.query(func.count(CharacterCard.id)).scalar() or 0,
        "worldbooks_total": db.query(func.count(WorldBook.id)).scalar() or 0,
        "queries_today": db.query(func.count(QueryLog.id)).filter(QueryLog.created_at >= today).scalar() or 0,
        "queries_total": db.query(func.count(QueryLog.id)).scalar() or 0,
        "queries_unanswered": db.query(func.count(QueryLog.id)).filter(QueryLog.answered.is_(False)).scalar() or 0,
        "ip_bans_active": len([b for b in bans if not (b.expires_at and b.expires_at < now)]),
        "unanswered_threshold": unanswered_threshold(),
    }


def user_rows(db: Session) -> List[dict]:
    """用户列表 + 每人会话数 / 提问数 / 最后一次提问时间。"""
    sessions = dict(db.query(SessionToken.user_id, func.count(SessionToken.token))
                      .group_by(SessionToken.user_id).all())
    qstats = {r[0]: (r[1], r[2]) for r in
              db.query(QueryLog.user_id, func.count(QueryLog.id), func.max(QueryLog.created_at))
                .filter(QueryLog.user_id.isnot(None)).group_by(QueryLog.user_id).all()}
    out = []
    for u in db.query(User).order_by(User.id).all():
        cnt, last = qstats.get(u.id, (0, None))
        out.append({
            "id": u.id, "username": u.username,
            "is_admin": bool(u.is_admin), "is_active": bool(u.is_active),
            "created_at": u.created_at,
            "ban_reason": u.ban_reason or "", "banned_at": u.banned_at,
            "sessions": sessions.get(u.id, 0),
            "queries": cnt, "last_query_at": last,
        })
    return out
