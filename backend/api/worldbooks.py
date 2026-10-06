from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import current_user, llm_client
from backend.models.database import get_db
from backend.models.user import User
from backend.schemas.world_book import (
    WorldBookCreate, WorldBookUpdate,
    WorldBookResponse, WorldBookListResponse,
)
from backend.services import worldbook_service, worldbook_generator

router = APIRouter()


@router.get("/worldbooks", response_model=WorldBookListResponse)
def list_worldbooks(
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=50),
    search: str = Query(""),
    tags: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return worldbook_service.list_worldbooks(db, user.id, page=page, page_size=page_size,
                                             search=search, tags=tag_list)


@router.get("/worldbooks/{wb_id}", response_model=WorldBookResponse)
def get_worldbook(wb_id: int, db: Session = Depends(get_db),
                  user: User = Depends(current_user)):
    wb = worldbook_service.get_worldbook(db, wb_id, user.id)
    if not wb:
        raise HTTPException(status_code=404, detail="世界书未找到")
    return wb


@router.post("/worldbooks", response_model=WorldBookResponse)
def create_worldbook(data: WorldBookCreate, db: Session = Depends(get_db),
                     user: User = Depends(current_user)):
    return worldbook_service.create_worldbook(db, data, user.id)


@router.put("/worldbooks/{wb_id}", response_model=WorldBookResponse)
def update_worldbook(wb_id: int, data: WorldBookUpdate, db: Session = Depends(get_db),
                     user: User = Depends(current_user)):
    result = worldbook_service.update_worldbook(db, wb_id, data, user.id)
    if not result:
        raise HTTPException(status_code=404, detail="世界书未找到")
    return result


@router.delete("/worldbooks/{wb_id}")
def delete_worldbook(wb_id: int, db: Session = Depends(get_db),
                     user: User = Depends(current_user)):
    success = worldbook_service.delete_worldbook(db, wb_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="世界书未找到")
    return {"status": "ok", "message": "世界书已删除"}


@router.post("/worldbooks/generate/preview")
def preview_worldbook(description: dict, user: User = Depends(current_user),
                      client=Depends(llm_client)):
    user_input = description.get("description", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="请提供世界观描述")
    return worldbook_generator.generate_from_description(user_input, client)


@router.post("/worldbooks/suggest-entries")
def suggest_entries(data: dict, user: User = Depends(current_user),
                    client=Depends(llm_client)):
    info = data.get("description", "")
    existing_keys = data.get("existing_keys", [])
    if not info:
        raise HTTPException(status_code=400, detail="请提供世界观信息")
    entries = worldbook_generator.suggest_entries(info, existing_keys, client)
    return {"entries": entries}
