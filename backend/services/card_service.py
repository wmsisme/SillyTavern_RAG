import json
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.models.character_card import CharacterCard
from backend.schemas.character_card import (
    CharacterCardCreate, CharacterCardUpdate,
    CharacterCardResponse, CharacterCardListResponse,
)


def create_card(db: Session, card_data: CharacterCardCreate) -> CharacterCardResponse:
    card = CharacterCard(
        name=card_data.name,
        age=card_data.age,
        gender=card_data.gender,
        species=card_data.species,
        occupation=card_data.occupation,
        appearance=card_data.appearance,
        personality=card_data.personality,
        background=card_data.background,
        description=card_data.description,
        tags=card_data.tags,
        is_r18=card_data.is_r18,
        has_status_bar=card_data.has_status_bar,
        status_bar_content=card_data.status_bar_content,
        status_bar_content_r18=card_data.status_bar_content_r18,
        custom_css=card_data.custom_css,
        first_message=card_data.first_message,
        image_path=card_data.image_path,
        raw_json=card_data.raw_json,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return CharacterCardResponse.model_validate(card)


def get_card(db: Session, card_id: int) -> Optional[CharacterCardResponse]:
    card = db.query(CharacterCard).filter(CharacterCard.id == card_id).first()
    if card:
        return CharacterCardResponse.model_validate(card)
    return None


def update_card(db: Session, card_id: int, card_data: CharacterCardUpdate) -> Optional[CharacterCardResponse]:
    card = db.query(CharacterCard).filter(CharacterCard.id == card_id).first()
    if not card:
        return None

    update_data = card_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(card, key, value)

    db.commit()
    db.refresh(card)
    return CharacterCardResponse.model_validate(card)


def delete_card(db: Session, card_id: int) -> bool:
    card = db.query(CharacterCard).filter(CharacterCard.id == card_id).first()
    if not card:
        return False
    db.delete(card)
    db.commit()
    return True


def list_cards(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    tags: Optional[List[str]] = None,
    is_r18: Optional[bool] = None,
) -> CharacterCardListResponse:
    query = db.query(CharacterCard)

    if search:
        query = query.filter(
            or_(
                CharacterCard.name.contains(search),
                CharacterCard.description.contains(search),
            )
        )

    if is_r18 is not None:
        query = query.filter(CharacterCard.is_r18 == is_r18)

    total = query.count()

    offset = (page - 1) * page_size
    items = query.order_by(CharacterCard.updated_at.desc()).offset(offset).limit(page_size).all()

    item_responses = [CharacterCardResponse.model_validate(item) for item in items]

    if tags:
        filtered = []
        for item in item_responses:
            item_tags = item.tags or []
            if any(t in item_tags for t in tags):
                filtered.append(item)
        return CharacterCardListResponse(
            total=len(filtered),
            page=page,
            page_size=page_size,
            items=filtered,
        )

    return CharacterCardListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=item_responses,
    )
