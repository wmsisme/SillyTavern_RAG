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


class AskResponse(BaseModel):
    answer: str
    sources: List[dict]


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


class HealthResponse(BaseModel):
    status: str
    chroma_count: int
    commit_hash: str
