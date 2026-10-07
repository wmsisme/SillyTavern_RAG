import json
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String

from backend.models.character_card import CharacterCard
from backend.schemas.character_card import (
    CharacterCardCreate, CharacterCardUpdate,
    CharacterCardResponse, CharacterCardListResponse,
)


def create_card(db: Session, card_data: CharacterCardCreate, user_id: int) -> CharacterCardResponse:
    card = CharacterCard(
        user_id=user_id,
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
        has_status_bar=card_data.has_status_bar,
        status_bar_content=card_data.status_bar_content,
        custom_css=card_data.custom_css,
        first_message=card_data.first_message,
        # 图片一律留空：只有上传端点能写 image_path（见 schemas 里的说明）
        image_path="",
        raw_json=card_data.raw_json,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return CharacterCardResponse.model_validate(card)


def get_card(db: Session, card_id: int, user_id: int) -> Optional[CharacterCardResponse]:
    # 归属校验写在查询里：别人的卡对这里来说「不存在」，而不是「没权限」
    card = (db.query(CharacterCard)
              .filter(CharacterCard.id == card_id, CharacterCard.user_id == user_id)
              .first())
    if card:
        return CharacterCardResponse.model_validate(card)
    return None


def update_card(db: Session, card_id: int, card_data: CharacterCardUpdate,
                user_id: int) -> Optional[CharacterCardResponse]:
    card = (db.query(CharacterCard)
              .filter(CharacterCard.id == card_id, CharacterCard.user_id == user_id)
              .first())
    if not card:
        return None

    update_data = card_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(card, key, value)

    db.commit()
    db.refresh(card)
    return CharacterCardResponse.model_validate(card)


def delete_card(db: Session, card_id: int, user_id: int) -> bool:
    card = (db.query(CharacterCard)
              .filter(CharacterCard.id == card_id, CharacterCard.user_id == user_id)
              .first())
    if not card:
        return False
    db.delete(card)
    db.commit()
    return True


def list_cards(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    tags: Optional[List[str]] = None,
) -> CharacterCardListResponse:
    query = db.query(CharacterCard).filter(CharacterCard.user_id == user_id)

    if search:
        query = query.filter(
            or_(
                CharacterCard.name.contains(search),
                CharacterCard.description.contains(search),
            )
        )


    if tags:
        # 标签筛选必须在**分页之前**下推到 SQL：
        # 原来是对已经取出来的一页做内存过滤，于是 total 退化成「本页命中数」，
        # 前端翻到第 2 页会看到空白（实际数据在后面几页）。
        # 语义与原来保持一致：命中任意一个标签即算匹配。
        # 注意：tags 是 JSON 列，SQLAlchemy 在 SQLite 上按 json.dumps 默认参数落库，
        # 中文标签会存成 \uXXXX 转义形态（实测 '["\\u7a00\\u6709\\u6807\\u7b7e"]'），
        # 所以匹配串必须同样转义后再 LIKE，直接拿中文去匹配永远命中不到。
        conds = []
        for t in tags:
            if not t:
                continue
            needle = json.dumps(t, ensure_ascii=True)[1:-1]
            conds.append(cast(CharacterCard.tags, String).like(f'%"{needle}"%'))
        if conds:
            query = query.filter(or_(*conds))

    total = query.count()

    offset = (page - 1) * page_size
    items = query.order_by(CharacterCard.updated_at.desc()).offset(offset).limit(page_size).all()

    item_responses = [CharacterCardResponse.model_validate(item) for item in items]

    return CharacterCardListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=item_responses,
    )
