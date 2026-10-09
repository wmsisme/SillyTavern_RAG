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


class AttachmentBrief(BaseModel):
    """后台列表里的附件信息（只给必要字段 —— 列表页不需要知道磁盘上的存名）。"""

    id: int
    orig_name: str = ""
    size: int = 0


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
    # 用户评价时顺手投递的文件（2026-10-08）—— 站长勾「这条要拿去更新知识库」之前先看它
    attachments: List[AttachmentBrief] = []
    # 系统当时的回答全文（2026-10-09 加）。达铭：「我还是想能够看到当时系统是怎么回答的，
    # 这样可以更好的更新」—— 后台点开就能看，导出清单里也带着
    answer: str = ""
    # 当时的检索结果摘要（JSON 字符串：前 5 条的 source + score）
    sources_digest: str = ""
    # 站长勾选「这条要拿去更新知识库」
    marked: bool = False
    marked_at: Optional[datetime] = None
    # 同一 IP 短时间内重复问同一个问题时，只留一条、在这里累加
    repeat_count: int = 1


class DeleteQueriesRequest(BaseModel):
    """按 id 删除提问记录（清理测试痕迹用）。"""

    ids: List[int]


# ------------------------------------------------------------------ 用户行为排查
class LoginIpRow(BaseModel):
    """最近登录 IP（同一个 IP 多次只算一行，但带次数与时间范围）。"""

    ip: str
    count: int
    first_at: Optional[datetime] = None
    last_at: Optional[datetime] = None
    agents: str = ""          # 浏览器/系统，辅助判断是不是同一台设备


class UserCardBrief(BaseModel):
    id: int
    name: str
    tags: str = ""
    has_image: bool = False
    updated_at: Optional[datetime] = None


class UserWorldBookBrief(BaseModel):
    id: int
    name: str
    entries: int = 0
    updated_at: Optional[datetime] = None


class UserContentOut(BaseModel):
    """某个用户建了什么（管理员排查违规内容用）。"""

    user_id: int
    username: str
    cards: List[UserCardBrief]
    worldbooks: List[UserWorldBookBrief]


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
    # 可选附件（2026-10-08）：先 POST /api/attachments 拿到 id 再带上来（两段式）。
    # 主要用途是「大佬投递技术档案」—— 站长在后台能看到并下载，
    # 但**绝不自动进知识库**（延续「我来勾选」那条规矩）。
    attachment_ids: List[int] = []


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
    # 用户投递的文件（2026-10-08）—— 这就是「大佬投递技术档案」的落地处：
    # 站长在后台点一下就能下载，看完再决定要不要据此更新知识库（**不自动进库**）
    attachments: List[AttachmentBrief] = []


class UserFeedbackPage(BaseModel):
    total: int
    unhandled: int
    page: int
    page_size: int
    items: List[UserFeedbackRow]
