"""后台管理的出入参（仅管理员可用，路由见 api/admin.py）。"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AdminOverview(BaseModel):
    users_total: int
    users_banned: int
    cards_total: int
    worldbooks_total: int
    queries_today: int
    queries_total: int
    queries_unanswered: int
    ip_bans_active: int
    unanswered_threshold: float


class AdminUserRow(BaseModel):
    id: int
    username: str
    is_admin: bool
    is_active: bool
    created_at: Optional[datetime] = None
    ban_reason: str = ""
    banned_at: Optional[datetime] = None
    sessions: int = 0
    queries: int = 0
    last_query_at: Optional[datetime] = None


class BanRequest(BaseModel):
    reason: str = ""
    # 顺带把该用户名下的所有会话踢掉（默认就踢；封了还留着登录态没有意义）
    kick_sessions: bool = True


class BanIpRequest(BaseModel):
    ip: str
    reason: str = ""
    days: int = 0          # 0 = 永久；>0 = 这么多天后自动失效


class IpBanRow(BaseModel):
    id: int
    ip: str
    reason: str = ""
    created_by: str = ""
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    expired: bool = False


class QueryLogRow(BaseModel):
    id: int
    created_at: Optional[datetime] = None
    ip: str = ""
    user_id: Optional[int] = None
    username: str = ""
    kind: str = "search"
    query: str
    sources_count: int = 0
    top_score: float = 0.0
    answered: bool = True
    feedback: str = ""
    feedback_reason: str = ""
    feedback_at: Optional[datetime] = None
    # 当时的检索结果摘要（JSON 字符串：前 5 条的 source + score）
    sources_digest: str = ""


class QueryLogPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[QueryLogRow]


class ActiveIpRow(BaseModel):
    ip: str
    queries: int
    users: int                       # 这个 IP 上出现过几个账号（共享账号的线索）
    usernames: str = ""              # 拼好的用户名列表，最多几个
    last_at: Optional[datetime] = None
    banned: bool = False
