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
    """「这个问题没解决」按钮。比阈值判断更可信 —— 用户说了算。"""

    query_log_id: int
    solved: bool = False


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
