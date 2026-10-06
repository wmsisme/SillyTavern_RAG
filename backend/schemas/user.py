from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    invite_code: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    user: UserResponse
    token: str


class AuthConfigResponse(BaseModel):
    """给前端登录页看的：要不要邀请码、当前有没有人来注册过。"""

    invite_required: bool
    has_any_user: bool
    cookie_secure: bool


class OkResponse(BaseModel):
    status: str = "ok"
    message: Optional[str] = None
