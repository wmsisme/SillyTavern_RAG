import json
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String

from backend.models.world_book import WorldBook
from backend.schemas.world_book import (
    WorldBookCreate, WorldBookUpdate,
    WorldBookResponse, WorldBookListResponse,
)


def create_worldbook(db: Session, data: WorldBookCreate) -> WorldBookResponse:
    wb = WorldBook(
        name=data.name,
        description=data.description,
        tags=data.tags,
        entries=[e.model_dump() for e in data.entries],
    )
    db.add(wb)
    db.commit()
    db.refresh(wb)
    return WorldBookResponse.model_validate(wb)


def get_worldbook(db: Session, wb_id: int) -> Optional[WorldBookResponse]:
    wb = db.query(WorldBook).filter(WorldBook.id == wb_id).first()
    if wb:
        return WorldBookResponse.model_validate(wb)
    return None


def update_worldbook(db: Session, wb_id: int, data: WorldBookUpdate) -> Optional[WorldBookResponse]:
    wb = db.query(WorldBook).filter(WorldBook.id == wb_id).first()
    if not wb:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if "entries" in update_data and update_data["entries"]:
        update_data["entries"] = [
            e.model_dump() if hasattr(e, 'model_dump') else e
            for e in update_data["entries"]
        ]

    for key, value in update_data.items():
        setattr(wb, key, value)

    db.commit()
    db.refresh(wb)
    return WorldBookResponse.model_validate(wb)


def delete_worldbook(db: Session, wb_id: int) -> bool:
    wb = db.query(WorldBook).filter(WorldBook.id == wb_id).first()
    if not wb:
        return False
    db.delete(wb)
    db.commit()
    return True


def list_worldbooks(
    db: Session,
    page: int = 1,
    page_size: int = 5,
    search: str = "",
    tags: Optional[List[str]] = None,
) -> WorldBookListResponse:
    query = db.query(WorldBook)

    if search:
        query = query.filter(
            or_(
                WorldBook.name.contains(search),
                WorldBook.description.contains(search),
            )
        )

    if tags:
        # 同 card_service：标签筛选下推到分页之前，否则 total 与翻页语义都是错的；
        # 且中文标签在库里是 \uXXXX 转义形态，匹配串要先转义。
        conds = []
        for t in tags:
            if not t:
                continue
            needle = json.dumps(t, ensure_ascii=True)[1:-1]
            conds.append(cast(WorldBook.tags, String).like(f'%"{needle}"%'))
        if conds:
            query = query.filter(or_(*conds))

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(WorldBook.updated_at.desc()).offset(offset).limit(page_size).all()

    item_responses = [WorldBookResponse.model_validate(item) for item in items]

    return WorldBookListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=item_responses,
    )
