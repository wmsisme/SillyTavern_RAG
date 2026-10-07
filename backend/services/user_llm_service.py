"""账号里存的大模型配置：读写、加密、对外形态。

对外只暴露「有没有配 / 前 6 后 4 打码 / 平台与模型」——**原文永不出网**。
"""
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.user import UserLLMSettings
from backend.services import llm_provider, secret_box


def get(db: Session, user_id: int) -> Optional[UserLLMSettings]:
    return db.query(UserLLMSettings).filter(UserLLMSettings.user_id == user_id).first()


def save(db: Session, user_id: int, provider: str, api_key: str,
         model: str = "", base_url: str = "") -> UserLLMSettings:
    """保存配置。

    api_key 传空字符串 = **保留原来那把**（只改平台 / 模型 / 自定义地址）——
    否则用户每次改个模型都要重新粘贴一遍 Key。
    """
    provider = (provider or "").strip().lower()
    if not provider:
        raise ValueError("平台不能为空")
    row = get(db, user_id)
    api_key = (api_key or "").strip()
    if not api_key and row is None:
        raise ValueError("请填 API Key")
    # 地址在**存的时候**就校验（指向内网直接拒绝并说明原因）——
    # 别让它先落库、等下次请求才炸，那时用户早忘了自己填过什么
    base_url = llm_provider.validate_base_url((base_url or "").strip())
    if row is None:
        row = UserLLMSettings(user_id=user_id)
        db.add(row)
    row.provider = provider
    row.model = (model or "").strip()
    row.base_url = base_url
    if api_key:
        row.api_key_enc = secret_box.encrypt(api_key)
    db.commit()
    db.refresh(row)
    return row


def clear(db: Session, user_id: int) -> bool:
    row = get(db, user_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def to_credentials(row: Optional[UserLLMSettings]) -> Optional[llm_provider.LLMCredentials]:
    """解密成凭证供本次请求使用；解不开（换了 SECRET_KEY）就返回 None。"""
    if row is None:
        return None
    api_key = secret_box.decrypt(row.api_key_enc)
    if not api_key:
        return None
    return llm_provider.from_headers(row.provider or "", api_key,
                                     row.model or "", row.base_url or "")


def public_view(row: Optional[UserLLMSettings]) -> dict:
    """给前端的形态：能用来说明"配的是哪家、key 是哪一把"，但拿不到原文。"""
    if row is None:
        return {"configured": False, "provider": "", "model": "", "base_url": "",
                "masked_key": "", "updated_at": None, "decryptable": True}
    api_key = secret_box.decrypt(row.api_key_enc)
    masked = ""
    if api_key:
        masked = f"{api_key[:6]}…{api_key[-4:]}" if len(api_key) > 10 else "*" * len(api_key)
    return {
        "configured": True,
        "provider": row.provider or "",
        "model": row.model or "",
        "base_url": row.base_url or "",
        "masked_key": masked,
        # 解不开时明确告诉前端：不是没配，是密钥变了，让用户重填
        "decryptable": bool(api_key),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
