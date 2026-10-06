from fastapi import APIRouter, Depends, Query

from backend.api.deps import current_admin, current_user
from backend.models.user import User
from backend.schemas.rag import UpdateCheckResponse, UpdateRunResponse
from backend.services import update_service

router = APIRouter()

# 文档索引更新是管理动作：check/status 登录就能看，run 只有管理员能触发
# （run 会真去拉上游仓库、重译重灌，属于重活，不能被普通用户随手点）
#
# ⚠️ 刻意**都是普通 def**：这三个下面全是同步阻塞调用（git fetch / 重译重灌，run 实测 80 秒起步）。
# 写成 async def 会把事件循环卡死整整 80 秒——期间所有人打不开页面。
# 普通 def 会被 FastAPI 丢进线程池，不挡别人。


@router.get("/update/check", response_model=UpdateCheckResponse)
def check_update(force: bool = Query(False, description="true=跳过缓存，真的去 fetch 上游"),
                 user: User = Depends(current_user)):
    result = update_service.check_update(force=force)
    return UpdateCheckResponse(**result)


@router.post("/update/run", response_model=UpdateRunResponse)
def run_update(admin: User = Depends(current_admin)):
    result = update_service.run_update()
    return UpdateRunResponse(**result)


@router.get("/update/status")
def update_status(user: User = Depends(current_user)):
    return update_service.get_update_status()
