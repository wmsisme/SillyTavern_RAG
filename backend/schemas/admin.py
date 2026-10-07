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
    feedback_total: int = 0
    feedback_unhandled: int = 0


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
    # 站长勾选「这条要拿去更新知识库」
    marked: bool = False
    marked_at: Optional[datetime] = None


class MarkQueriesRequest(BaseModel):
    """站长在后台勾选「这些要拿去更新知识库」。

    勾选权**刻意留在人手上**：用户随便问一句就自动灌进知识库会污染它。
    """

    ids: List[int]
    marked: bool = True


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


# ------------------------------------------------------------------ 用户反馈
class FeedbackCreate(BaseModel):
    """顶部栏「反馈」按钮提交的内容（仅登录用户）。"""

    content: str
    category: str = "其他"          # 建议 / 体验 / 故障 / 其他
    page: str = ""                  # 在哪个页面点的


class UserFeedbackRow(BaseModel):
    id: int
    created_at: Optional[datetime] = None
    user_id: Optional[int] = None
    username: str = ""
    ip: str = ""
    category: str = "其他"
    content: str
    page: str = ""
    handled: bool = False
    handled_at: Optional[datetime] = None
    handled_by: str = ""


class UserFeedbackPage(BaseModel):
    total: int
    unhandled: int
    page: int
    page_size: int
    items: List[UserFeedbackRow]
