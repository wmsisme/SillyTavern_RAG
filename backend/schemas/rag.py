from pydantic import BaseModel, Field
from typing import Optional, List

# 查询长度上限（2026-10-07 加固）。
# 实测：20 万字符的 query 也照单全收 —— 这个接口**不需要登录**，
# 而每一次检索都要站长掏 embedding + rerank 的额度、还要占 CPU 分词。
# 2000 字对"一个问题"来说非常宽裕（比它能检索出的文档片段还长）。
MAX_QUERY_CHARS = 2000
MAX_REASON_CHARS = 2000


class SearchRequest(BaseModel):
    query: str = Field("", max_length=MAX_QUERY_CHARS)
    top_k: int = Field(5, ge=1, le=20)       # 原来 top_k 随便传（负数、10 亿都收）


class AskRequest(BaseModel):
    query: str = Field("", max_length=MAX_QUERY_CHARS)


class SearchResult(BaseModel):
    content: str
    source: str
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResult]
    # 这次检索在服务端的记录 id（前端「没解决」按钮要拿它回传）
    query_log_id: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    sources: List[dict]
    query_log_id: Optional[int] = None


class FeedbackRequest(BaseModel):
    """用户对这次检索/回答的评价 —— 比阈值判断更可信，用户说了算。

    kind：
      solved     = 有帮助（覆盖阈值判断，标记为已解答）
      unsolved   = 没解决（答案没帮上忙）
      irrelevant = **检索到内容了，但这些内容不相关**（用户明确说系统给错了）
    reason 选填，原样记进后台 —— 「为什么说不相关」正是补知识库/调检索的依据。
    """

    query_log_id: int
    kind: str = "unsolved"
    reason: str = Field("", max_length=MAX_REASON_CHARS)


class UpdateCheckResponse(BaseModel):
    has_update: bool
    changed_files: List[str]
    current_commit: str
    upstream_commit: str


class UpdateRunResponse(BaseModel):
    status: str
    message: str
    new_vectors: int = 0
    deleted_vectors: int = 0
    # 本次以英文原文入库（翻译失败）的文档，前端可据此提示用户
    translate_failures: List[str] = []
    # 本次更新的实际代价（墙钟秒数 + DeepSeek usage 实测 token）
    elapsed_s: float = 0
    usage: dict = {}


class HealthResponse(BaseModel):
    status: str
    chroma_count: int
    commit_hash: str
