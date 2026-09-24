from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CharacterCardBase(BaseModel):
    name: str = "未命名角色"
    age: str = ""
    gender: str = ""
    species: str = ""
    occupation: str = ""
    appearance: str = ""
    personality: str = ""
    background: str = ""
    description: str = ""
    tags: List[str] = []
    is_r18: bool = False
    has_status_bar: bool = False
    status_bar_content: str = ""
    status_bar_content_r18: str = ""
    custom_css: str = ""
    first_message: str = ""
    image_path: str = ""


class CharacterCardCreate(CharacterCardBase):
    raw_json: Optional[dict] = None


class CharacterCardUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    species: Optional[str] = None
    occupation: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_r18: Optional[bool] = None
    has_status_bar: Optional[bool] = None
    status_bar_content: Optional[str] = None
    status_bar_content_r18: Optional[str] = None
    custom_css: Optional[str] = None
    first_message: Optional[str] = None
    image_path: Optional[str] = None
    raw_json: Optional[dict] = None


class CharacterCardResponse(CharacterCardBase):
    id: int
    raw_json: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CharacterCardListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CharacterCardResponse]
