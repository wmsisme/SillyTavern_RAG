"""LLM 平台清单 + 连通性自检 + 「Key 存账号」的设置读写。

三种存取方式，优先级从高到低：
  ① 请求头（X-LLM-Key…）—— 临时用一次、或用户选了「只存这台浏览器」；
  ② 账号里加密存的 —— 换设备登录也能用（用户选「保存到我的账号」）；
  ③ 都没有 → 400，明确告诉他去设置。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import current_user, llm_client, llm_credentials
from backend.models.database import get_db
from backend.models.user import User
from backend.schemas.llm import LLMSettingsIn, LLMSettingsOut
from backend.services import llm_provider, user_llm_service

router = APIRouter()


@router.get("/llm/providers")
def list_providers():
    """平台元信息（公开）：前端下拉框用它渲染，不含任何密钥。"""
    return {"providers": llm_provider.list_providers()}


@router.get("/llm/settings", response_model=LLMSettingsOut)
def get_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_llm_service.public_view(user_llm_service.get(db, user.id))


@router.put("/llm/settings", response_model=LLMSettingsOut)
def put_settings(body: LLMSettingsIn, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    try:
        row = user_llm_service.save(db, user.id, body.provider, body.api_key,
                                    body.model, body.base_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return user_llm_service.public_view(row)


@router.delete("/llm/settings", response_model=LLMSettingsOut)
def delete_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    user_llm_service.clear(db, user.id)
    return user_llm_service.public_view(None)


@router.post("/llm/test")
def test_llm(client=Depends(llm_client), creds=Depends(llm_credentials)):
    """用当前生效的凭证发一次极小的调用，验证 Key 是否真的可用。

    不需要登录也能用（只要带了请求头凭证）；失败也返回 HTTP 200 + {ok:false}：
    这不是服务错误，是"这把 Key 能不能用"的答案，前端要显示成一句人话。
    """
    try:
        resp = client.chat.completions.create(
            messages=[{"role": "user", "content": "只回复两个字：可以"}],
            max_tokens=16,
            temperature=0,
        )
        reply = (resp.choices[0].message.content or "").strip()
        return {"ok": True, "model": creds.effective_model,
                "provider": creds.label, "reply": reply[:50]}
    except Exception as e:
        # 平台返回的错误里 Key 通常是打码的（如 ****-key），仍截断一下更稳
        return {"ok": False, "model": creds.effective_model, "provider": creds.label,
                "error": f"{type(e).__name__}: {str(e)[:200]}"}
