import hashlib
import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.api.deps import current_user, llm_client
from backend.config import CARD_IMAGE_DIR
from backend.models.database import get_db
from backend.models.character_card import CharacterCard
from backend.models.user import User
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

# 只信 Content-Type 是不够的（那是客户端说的），再看一眼文件头。
# 起因（2026-10-07 安全测试）：内容随便是什么都能上传成功，等于把图床当文件柜用。
IMAGE_MAGIC = {
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".gif": [b"GIF87a", b"GIF89a"],
    ".webp": [b"RIFF"],
}


def _looks_like_image(data: bytes, ext: str) -> bool:
    if len(data) < 12:
        return False
    if not any(data.startswith(m) for m in IMAGE_MAGIC.get(ext, [])):
        return False
    if ext == ".webp" and data[8:12] != b"WEBP":     # RIFF 是通用容器头
        return False
    return True


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
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    # 参数逐行摆放：便于按行摘取，比改行内容安全
    return card_service.list_cards(
        db, user.id, page=page, page_size=page_size, search=search, tags=tag_list,
    )


@router.get("/cards/{card_id}", response_model=CharacterCardResponse)
def get_card(card_id: int, db: Session = Depends(get_db),
             user: User = Depends(current_user)):
    card = card_service.get_card(db, card_id, user.id)
    if not card:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    return card


@router.post("/cards", response_model=CharacterCardResponse)
def create_card(card: CharacterCardCreate, db: Session = Depends(get_db),
                user: User = Depends(current_user)):
    return card_service.create_card(db, card, user.id)


@router.put("/cards/{card_id}", response_model=CharacterCardResponse)
def update_card(card_id: int, card: CharacterCardUpdate, db: Session = Depends(get_db),
                user: User = Depends(current_user)):
    result = card_service.update_card(db, card_id, card, user.id)
    if not result:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    return result


@router.delete("/cards/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db),
                user: User = Depends(current_user)):
    # 先取出图片路径，删卡时把图片文件一起清掉，免得 static 目录越堆越多
    card = (db.query(CharacterCard)
              .filter(CharacterCard.id == card_id, CharacterCard.user_id == user.id)
              .first())
    if card:
        _remove_image_file(card.image_path)
    success = card_service.delete_card(db, card_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    return {"status": "ok", "message": "角色卡已删除"}


def _resolve_image_path(image_path: Optional[str]) -> Optional[Path]:
    """把库里记的 /static/... 相对路径解析成真实文件；只认 card_images 目录里的。"""
    if not image_path or not image_path.startswith("/static/"):
        return None
    base = CARD_IMAGE_DIR.resolve()
    p = (base.parent / image_path[len("/static/"):]).resolve()
    if p.is_file() and base in p.parents:
        return p
    return None


@router.get("/cards/{card_id}/image")
def get_card_image(card_id: int, db: Session = Depends(get_db),
                   user: User = Depends(current_user)):
    """取角色卡图片。

    图片不再走 /static 静态目录 —— 静态目录不鉴权，拿到 URL 的人就能看，
    那「只有本人能看到自己的卡」就是句空话。这里改成必须带登录态 + 校验归属。
    """
    card = (db.query(CharacterCard)
              .filter(CharacterCard.id == card_id, CharacterCard.user_id == user.id)
              .first())
    if not card:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    p = _resolve_image_path(card.image_path)
    if not p:
        raise HTTPException(status_code=404, detail="这张卡还没有图片")
    return FileResponse(p)


@router.post("/cards/{card_id}/image", response_model=CharacterCardResponse)
async def upload_card_image(card_id: int, file: UploadFile = File(...),
                            db: Session = Depends(get_db),
                            user: User = Depends(current_user)):
    """上传/替换角色卡图片。

    图片存到 backend/static/card_images/（用户数据，已 gitignore）；
    库里的 image_path 只是文件名，对外一律由 /api/cards/{id}/image 鉴权读取。
    """
    ext = ALLOWED_IMAGE_TYPES.get((file.content_type or "").lower())
    if not ext:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的图片类型：{file.content_type or '未知'}（支持 png / jpg / webp / gif）",
        )
    # 只读到"上限 + 1"字节：超限时立刻停手，不把整个大文件拉进内存
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="图片内容为空")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="图片过大（上限 8MB）")
    if not _looks_like_image(data, ext):
        raise HTTPException(status_code=400,
                            detail="这个文件的内容和图片格式对不上（不是真正的图片），换一张试试")

    card = (db.query(CharacterCard)
              .filter(CharacterCard.id == card_id, CharacterCard.user_id == user.id)
              .first())
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
def delete_card_image(card_id: int, db: Session = Depends(get_db),
                      user: User = Depends(current_user)):
    """清空角色卡图片（回到默认图标）"""
    card = (db.query(CharacterCard)
              .filter(CharacterCard.id == card_id, CharacterCard.user_id == user.id)
              .first())
    if not card:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    _remove_image_file(card.image_path)
    card.image_path = ""
    db.commit()
    db.refresh(card)
    return card


@router.post("/cards/generate")
def generate_card(description: dict, db: Session = Depends(get_db),
                  user: User = Depends(current_user), client=Depends(llm_client)):
    user_input = description.get("description", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="请提供角色描述")

    card_data = card_generator.generate_from_description(user_input, client)
    if "error" in card_data:
        raise HTTPException(status_code=500, detail=card_data["error"])

    card_create = CharacterCardCreate(**card_data)
    return card_service.create_card(db, card_create, user.id)


@router.post("/cards/generate/preview")
def preview_card(description: dict, user: User = Depends(current_user),
                 client=Depends(llm_client)):
    user_input = description.get("description", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="请提供角色描述")
    return card_generator.generate_from_description(user_input, client)


@router.post("/cards/generate/status-bar")
def generate_status_bar(data: dict, user: User = Depends(current_user),
                        client=Depends(llm_client)):
    character_info = data.get("character_info", "")
    if not character_info:
        raise HTTPException(status_code=400, detail="请提供角色信息")
    # 实参逐行摆放，便于阅读和逐项调整
    result = card_generator.generate_status_bar(
        character_info,
        client=client,
    )
    return {"status_bar": result}


@router.post("/cards/generate/greeting")
def generate_greeting(data: dict, user: User = Depends(current_user),
                      client=Depends(llm_client)):
    character_info = data.get("character_info", "")
    if not character_info:
        raise HTTPException(status_code=400, detail="请提供角色信息")
    result = card_generator.generate_greeting(
        character_info,
        client=client,
    )
    return {"greeting": result}


@router.post("/cards/suggest-tags")
def suggest_tags(data: dict, user: User = Depends(current_user),
                 client=Depends(llm_client)):
    character_info = data.get("character_info", "")
    if not character_info:
        raise HTTPException(status_code=400, detail="请提供角色信息")
    tags = card_generator.suggest_tags(character_info, client)
    return {"tags": tags}
