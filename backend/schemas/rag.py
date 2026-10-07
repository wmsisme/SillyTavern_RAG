from pydantic import BaseModel
from typing import Optional, List


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class AskRequest(BaseModel):
    query: str


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
    reason: str = ""


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
