from fastapi import APIRouter, Query
from backend.schemas.rag import UpdateCheckResponse, UpdateRunResponse
from backend.services import update_service

router = APIRouter()


@router.get("/update/check", response_model=UpdateCheckResponse)
async def check_update(force: bool = Query(False, description="true=跳过缓存，真的去 fetch 上游")):
    result = update_service.check_update(force=force)
    return UpdateCheckResponse(**result)


@router.post("/update/run", response_model=UpdateRunResponse)
async def run_update():
    result = update_service.run_update()
    return UpdateRunResponse(**result)


@router.get("/update/status")
async def update_status():
    return update_service.get_update_status()
