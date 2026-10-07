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
    has_status_bar: bool = False
    status_bar_content: str = ""
    custom_css: str = ""
    first_message: str = ""
    # ⚠️ image_path 只在**响应**里出现（见 CharacterCardResponse），
    # 创建 / 更新请求里刻意不收 —— 它由上传端点自己写入。
    # 起因（2026-10-07 安全测试）：这个字段原本可以随便传，于是有人能把自己的卡
    # 指向别人的图片路径，读别人的图、甚至删别人的图（图片删除是按这个字段找文件的）。


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
    has_status_bar: Optional[bool] = None
    status_bar_content: Optional[str] = None
    custom_css: Optional[str] = None
    first_message: Optional[str] = None
    raw_json: Optional[dict] = None


class CharacterCardResponse(CharacterCardBase):
    id: int
    # 只有响应带它：值是 /static/card_images/xxx.png，且一定由上传端点写入
    image_path: str = ""
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
