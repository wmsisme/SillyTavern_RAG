from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

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

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(WorldBook.updated_at.desc()).offset(offset).limit(page_size).all()

    item_responses = [WorldBookResponse.model_validate(item) for item in items]

    if tags:
        filtered = []
        for item in item_responses:
            item_tags = item.tags or []
            if any(t in item_tags for t in tags):
                filtered.append(item)
        return WorldBookListResponse(
            total=len(filtered),
            page=page,
            page_size=page_size,
            items=filtered,
        )

    return WorldBookListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=item_responses,
    )
