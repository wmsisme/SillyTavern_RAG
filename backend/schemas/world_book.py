from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class WorldBookEntry(BaseModel):
    key: str = ""
    content: str = ""
    comment: str = ""
    depth: int = 1
    trigger_words: List[str] = []


class WorldBookBase(BaseModel):
    name: str = "未命名世界书"
    description: str = ""
    tags: List[str] = []
    entries: List[WorldBookEntry] = []


class WorldBookCreate(WorldBookBase):
    pass


class WorldBookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    entries: Optional[List[WorldBookEntry]] = None


class WorldBookResponse(WorldBookBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorldBookListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[WorldBookResponse]
