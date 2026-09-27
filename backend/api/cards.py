import hashlib
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from backend.config import CARD_IMAGE_DIR
from backend.models.database import get_db
from backend.models.character_card import CharacterCard
from backend.schemas.character_card import (
    CharacterCardCreate, CharacterCardUpdate,
    CharacterCardResponse, CharacterCardListResponse,
)
from backend.services import card_service, card_generator

router = APIRouter()

# 角色卡图片：png/jpg/webp/gif，单张上限 8MB
ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def _remove_image_file(image_path: Optional[str]):
    """删掉 backend/static 下的旧图片。

    只处理本服务写出去的 `/static/...` 相对路径，并确认目标确实落在
    card_images 目录内，避免把别处的文件误删。
    """
    if not image_path or not image_path.startswith("/static/"):
        return
    try:
        base = CARD_IMAGE_DIR.resolve()
        target = (base.parent / image_path[len("/static/"):]).resolve()
        if target.is_file() and base in target.parents:
            target.unlink()
    except Exception:
        pass


@router.get("/cards", response_model=CharacterCardListResponse)
def list_cards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    tags: Optional[str] = Query(None, description="逗号分隔的标签"),
    is_r18: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return card_service.list_cards(
        db, page=page, page_size=page_size, search=search, tags=tag_list, is_r18=is_r18
    )


@router.get("/cards/{card_id}", response_model=CharacterCardResponse)
def get_card(card_id: int, db: Session = Depends(get_db)):
    card = card_service.get_card(db, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    return card


@router.post("/cards", response_model=CharacterCardResponse)
def create_card(card: CharacterCardCreate, db: Session = Depends(get_db)):
    return card_service.create_card(db, card)


@router.put("/cards/{card_id}", response_model=CharacterCardResponse)
def update_card(card_id: int, card: CharacterCardUpdate, db: Session = Depends(get_db)):
    result = card_service.update_card(db, card_id, card)
    if not result:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    return result


@router.delete("/cards/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    # 先取出图片路径，删卡时把图片文件一起清掉，免得 static 目录越堆越多
    card = db.query(CharacterCard).filter(CharacterCard.id == card_id).first()
    if card:
        _remove_image_file(card.image_path)
    success = card_service.delete_card(db, card_id)
    if not success:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    return {"status": "ok", "message": "角色卡已删除"}


@router.post("/cards/{card_id}/image", response_model=CharacterCardResponse)
async def upload_card_image(card_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传/替换角色卡图片。

    图片存到 backend/static/card_images/（用户数据，已 gitignore），
    库里只记相对 URL，由 main.py 把 /static 挂出去。
    """
    ext = ALLOWED_IMAGE_TYPES.get((file.content_type or "").lower())
    if not ext:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的图片类型：{file.content_type or '未知'}（支持 png / jpg / webp / gif）",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="图片内容为空")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="图片过大（上限 8MB）")

    card = db.query(CharacterCard).filter(CharacterCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="角色卡未找到")

    CARD_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    name = f"card_{card_id}_{hashlib.md5(data).hexdigest()[:10]}{ext}"
    (CARD_IMAGE_DIR / name).write_bytes(data)

    _remove_image_file(card.image_path)          # 换图时删旧文件
    card.image_path = f"/static/card_images/{name}"
    db.commit()
    db.refresh(card)
    return card


@router.delete("/cards/{card_id}/image", response_model=CharacterCardResponse)
def delete_card_image(card_id: int, db: Session = Depends(get_db)):
    """清空角色卡图片（回到默认图标）"""
    card = db.query(CharacterCard).filter(CharacterCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    _remove_image_file(card.image_path)
    card.image_path = ""
    db.commit()
    db.refresh(card)
    return card


@router.post("/cards/generate")
def generate_card(description: dict, db: Session = Depends(get_db)):
    user_input = description.get("description", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="请提供角色描述")

    card_data = card_generator.generate_from_description(user_input)
    if "error" in card_data:
        raise HTTPException(status_code=500, detail=card_data["error"])

    card_create = CharacterCardCreate(**card_data)
    return card_service.create_card(db, card_create)


@router.post("/cards/generate/preview")
def preview_card(description: dict):
    user_input = description.get("description", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="请提供角色描述")
    return card_generator.generate_from_description(user_input)


@router.post("/cards/generate/status-bar")
def generate_status_bar(data: dict):
    character_info = data.get("character_info", "")
    is_r18 = data.get("is_r18", False)
    if not character_info:
        raise HTTPException(status_code=400, detail="请提供角色信息")
    result = card_generator.generate_status_bar(character_info, is_r18)
    return {"status_bar": result}


@router.post("/cards/generate/greeting")
def generate_greeting(data: dict):
    character_info = data.get("character_info", "")
    is_r18 = data.get("is_r18", False)
    if not character_info:
        raise HTTPException(status_code=400, detail="请提供角色信息")
    result = card_generator.generate_greeting(character_info, is_r18)
    return {"greeting": result}


@router.post("/cards/suggest-tags")
def suggest_tags(data: dict):
    character_info = data.get("character_info", "")
    if not character_info:
        raise HTTPException(status_code=400, detail="请提供角色信息")
    tags = card_generator.suggest_tags(character_info)
    return {"tags": tags}
