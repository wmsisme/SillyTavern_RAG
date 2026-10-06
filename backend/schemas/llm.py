from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LLMSettingsIn(BaseModel):
    """用户提交的大模型配置。

    api_key 只在这一次请求里出现，落库即加密；传空字符串 = 保留已存的那把
    （用户只想改模型/平台时，不用重新粘贴 Key）。
    """

    provider: str
    api_key: str = ""
    model: str = ""
    base_url: str = ""


class LLMSettingsOut(BaseModel):
    """回给前端的形态：**不含 Key 原文**，只有打码。"""

    configured: bool
    provider: str = ""
    model: str = ""
    base_url: str = ""
    masked_key: str = ""
    decryptable: bool = True
    updated_at: Optional[datetime] = None
