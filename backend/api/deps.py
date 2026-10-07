"""FastAPI 依赖：从 Cookie / Authorization 头里取当前用户。

Cookie 优先。原因见 auth_service.SessionToken 的注释：角色卡图片要过鉴权端点，
而 `<img src>` 发不出 Authorization 头，只能靠 Cookie。
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.user import User
from backend.services import auth_service, llm_provider, user_llm_service


def _token_from(request: Request) -> Optional[str]:
    tok = request.cookies.get(auth_service.COOKIE_NAME)
    if tok:
        return tok
    head = request.headers.get("Authorization", "")
    if head.lower().startswith("bearer "):
        return head[7:].strip()
    return None


def current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    return auth_service.resolve_token(db, _token_from(request))


def current_user(user: Optional[User] = Depends(current_user_optional)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def current_admin(user: User = Depends(current_user)) -> User:
    """管理动作（比如触发文档索引更新）只放给管理员。"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="只有管理员能做这个操作")
    return user


# ---------------------------------------------------------------- BYOK 凭证
def llm_credentials(request: Request, db: Session = Depends(get_db),
                    user: Optional[User] = Depends(current_user_optional),
                    ) -> llm_provider.LLMCredentials:
    """大模型凭证，来源优先级：**请求头 → 账号里加密存的 → 都没有就 400**。

    请求头那条给两种场景用：用户选了「只存这台浏览器」，或者临时换一把 Key 试。
    账号那条是「换设备登录也能直接用」。

    刻意**不**回落到服务端 .env 里的 key：公网上那样等于谁都能刷站长的余额。

    base_url 指向内网时 from_headers 会抛 ValueError（SSRF 防护），
    这里转成 400 并把原因原样回给用户 —— 不能让它变成 500 或者静默失败。
    """
    try:
        creds = llm_provider.from_headers(
            request.headers.get(llm_provider.HEADER_PROVIDER, ""),
            request.headers.get(llm_provider.HEADER_KEY, ""),
            request.headers.get(llm_provider.HEADER_MODEL, ""),
            request.headers.get(llm_provider.HEADER_BASE_URL, ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if creds:
        return creds
    if user is not None:
        try:
            creds = user_llm_service.to_credentials(user_llm_service.get(db, user.id))
        except ValueError as e:
            raise HTTPException(status_code=400,
                                detail=f"你账号里存的大模型地址不能用了：{e}")
        if creds:
            return creds
    raise HTTPException(
        status_code=400,
        detail="这个功能要用你自己的大模型 API Key：点右上角「API 设置」填一个"
               "（可以只存这台浏览器，也可以存进你的账号，换设备也能用）。",
    )


def llm_client(creds: llm_provider.LLMCredentials = Depends(llm_credentials)):
    """与 openai SDK 同形状的客户端，可直接 `client.chat.completions.create(...)`。"""
    return llm_provider.build_client(creds)
