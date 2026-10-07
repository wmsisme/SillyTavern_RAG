"""注册 / 登录 / 退出 / 改密码。

注册默认开放；设了环境变量 REGISTER_INVITE_CODE 就要求填邀请码（想收着点时用）。
首个注册者自动成为管理员（文档索引更新这类管理动作只给管理员）。
"""
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.api.deps import current_user
from backend.api.ratelimit import client_ip
from backend.models.database import get_db
from backend.models.user import User
from backend.schemas.user import (
    AuthConfigResponse, ChangePasswordRequest, LoginRequest,
    LoginResponse, OkResponse, RegisterRequest, UserResponse,
)
from backend.services import admin_service, auth_service

router = APIRouter()

INVITE_CODE = os.environ.get("REGISTER_INVITE_CODE", "").strip()


def _log_login(db: Session, request: Request, user, action: str) -> None:
    """记一笔登录来源 —— 判断「共享账号」用（一个账号从好几个 IP 登录就很可疑）。

    失败**不影响登录**：这只是观察数据。
    """
    try:
        admin_service.log_login(db, user=user, ip=client_ip(request),
                                user_agent=request.headers.get("user-agent", ""),
                                action=action)
    except Exception as e:
        print(f"[loginlog] 记录失败（不影响登录）：{e}")


def _attach_cookie(resp: Response, token: str, expires) -> None:
    resp.set_cookie(
        key=auth_service.COOKIE_NAME,
        value=token,
        max_age=int((expires - datetime.now()).total_seconds()),
        httponly=True,
        samesite="lax",
        secure=auth_service.cookie_secure(),
        path="/",
    )


@router.get("/auth/config", response_model=AuthConfigResponse)
def auth_config(db: Session = Depends(get_db)):
    return AuthConfigResponse(
        invite_required=bool(INVITE_CODE),
        has_any_user=db.query(User).count() > 0,
        cookie_secure=auth_service.cookie_secure(),
    )


@router.post("/auth/register", response_model=LoginResponse, status_code=201)
def register(req: RegisterRequest, request: Request, resp: Response,
             db: Session = Depends(get_db)):
    try:
        user = auth_service.register(db, req.username, req.password,
                                     invite_code=req.invite_code, expect_invite=INVITE_CODE)
        user, token, expires = auth_service.login(db, req.username, req.password)
    except auth_service.AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _log_login(db, request, user, "register")
    _attach_cookie(resp, token, expires)
    return LoginResponse(user=UserResponse.model_validate(user), token=token)


@router.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request, resp: Response,
          db: Session = Depends(get_db)):
    try:
        user, token, expires = auth_service.login(db, req.username, req.password)
    except auth_service.AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _log_login(db, request, user, "login")
    _attach_cookie(resp, token, expires)
    return LoginResponse(user=UserResponse.model_validate(user), token=token)


@router.post("/auth/logout", response_model=OkResponse)
def logout(req: Request, resp: Response, db: Session = Depends(get_db)):
    token = req.cookies.get(auth_service.COOKIE_NAME)
    if not token:
        head = req.headers.get("Authorization", "")
        if head.lower().startswith("bearer "):
            token = head[7:].strip()
    auth_service.logout(db, token)
    resp.delete_cookie(auth_service.COOKIE_NAME, path="/")
    return OkResponse(message="已退出登录")


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return UserResponse.model_validate(user)


@router.post("/auth/password", response_model=OkResponse)
def change_password(req: ChangePasswordRequest, resp: Response,
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        auth_service.change_password(db, user, req.old_password, req.new_password)
    except auth_service.AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    resp.delete_cookie(auth_service.COOKIE_NAME, path="/")
    return OkResponse(message="密码已修改，请重新登录")
