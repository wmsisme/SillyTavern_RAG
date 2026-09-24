import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.schemas.character_card import (
    CharacterCardCreate, CharacterCardUpdate,
    CharacterCardResponse, CharacterCardListResponse,
)
from backend.services import card_service, card_generator

router = APIRouter()


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
    success = card_service.delete_card(db, card_id)
    if not success:
        raise HTTPException(status_code=404, detail="角色卡未找到")
    return {"status": "ok", "message": "角色卡已删除"}


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
