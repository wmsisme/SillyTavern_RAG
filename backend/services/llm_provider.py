"""BYOK（Bring Your Own Key）：每个请求自带 LLM 凭证，服务端不留存。

为什么不做免费额度 / 不用服务端 key 兜底
----------------------------------------
产品口径：**不提供免费额度**，生成类调用一律走用户自带的 Key。
所以**没带凭证时明确报错**，绝不偷偷用服务端的 key ——
否则公网一开，就是谁都能刷服务端的余额。

协议：两家写法，其余 6 家一家不差都是 OpenAI 兼容
--------------------------------------------------
  · **OpenAI 兼容**：DeepSeek / Kimi(Moonshot) / 硅基流动 / 豆包(火山方舟) /
    千问(DashScope 兼容模式) / OpenAI —— 直接用 openai SDK，只换 base_url。
  · **Anthropic**：另一套（POST /v1/messages + x-api-key + anthropic-version），
    这里用 httpx 手写，不引新依赖。

⚠️ 国内服务器直连 OpenAI / Anthropic 大概率不通（要走代理），
   所以那两家"适配好了但多半用不了"是预期内的，不是 bug。

对外接口刻意做成**和 openai SDK 同形状**（client.chat.completions.create(...)），
现有调用点因此几乎不用改：只把「内部拿一个全局 client」换成「把 client 传进来」。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterator, Optional

import httpx

ANTHROPIC_VERSION = "2023-06-01"

# ---------------------------------------------------------------- 平台注册表
# 前端「API 设置」页直接渲染这份表；base_url 只在这里定义一次。
PROVIDERS: dict[str, dict] = {
    "deepseek": {
        "label": "DeepSeek",
        "protocol": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat"],
        "key_hint": "以 sk- 开头，platform.deepseek.com 里创建",
    },
    "siliconflow": {
        "label": "硅基流动",
        "protocol": "openai",
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "Qwen/Qwen2.5-7B-Instruct",
        "models": [
            "Qwen/Qwen2.5-7B-Instruct",
            "deepseek-ai/DeepSeek-V3",
            "Qwen/Qwen3-8B",
        ],
        "key_hint": "以 sk- 开头，cloud.siliconflow.cn 里创建",
    },
    "moonshot": {
        "label": "Kimi（月之暗面）",
        "protocol": "openai",
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "kimi-k2-0905-preview"],
        "key_hint": "以 sk- 开头，platform.moonshot.cn 里创建",
    },
    "dashscope": {
        "label": "千问（阿里云百炼）",
        "protocol": "openai",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "models": ["qwen-plus", "qwen-turbo", "qwen-max"],
        "key_hint": "以 sk- 开头，bailian.console.aliyun.com 里创建",
    },
    "volcengine": {
        "label": "豆包（火山方舟）",
        "protocol": "openai",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-pro-32k",
        "models": ["doubao-pro-32k", "doubao-lite-32k"],
        # 方舟的模型名要用「推理接入点 ID（ep-… ）」，这里给个提醒
        "key_hint": "火山方舟的 key；模型名建议填你的推理接入点 ID（ep- 开头）",
    },
    "openai": {
        "label": "OpenAI",
        "protocol": "openai",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o"],
        "key_hint": "需要服务器能直连 api.openai.com（国内服务器通常不通）",
    },
    "anthropic": {
        "label": "Anthropic（Claude）",
        "protocol": "anthropic",
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-3-5-sonnet-latest",
        "models": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
        "key_hint": "需要服务器能直连 api.anthropic.com（国内服务器通常不通）",
    },
}

HEADER_PROVIDER = "X-LLM-Provider"
HEADER_KEY = "X-LLM-Key"
HEADER_MODEL = "X-LLM-Model"
HEADER_BASE_URL = "X-LLM-Base-Url"


def list_providers() -> list[dict]:
    """给前端用的平台清单（不含任何密钥）。"""
    return [
        {
            "id": pid,
            "label": p["label"],
            "protocol": p["protocol"],
            "default_model": p["default_model"],
            "models": p["models"],
            "key_hint": p["key_hint"],
            "builtin_base_url": p["base_url"],
        }
        for pid, p in PROVIDERS.items()
    ]


@dataclass
class LLMCredentials:
    """一次请求的 LLM 凭证。只在内存里活一次请求，绝不落库/落日志。"""

    provider: str
    api_key: str
    model: str = ""
    base_url: str = ""
    protocol: str = "openai"
    extra_headers: dict = field(default_factory=dict)

    @property
    def effective_model(self) -> str:
        return self.model or PROVIDERS.get(self.provider, {}).get("default_model", "")

    @property
    def effective_base_url(self) -> str:
        return (self.base_url or PROVIDERS.get(self.provider, {}).get("base_url", "")).rstrip("/")

    @property
    def label(self) -> str:
        return PROVIDERS.get(self.provider, {}).get("label", self.provider)

    def masked_key(self) -> str:
        """给日志/错误信息用的打码形态：只留头尾。"""
        k = self.api_key or ""
        if len(k) <= 10:
            return "*" * len(k)
        return f"{k[:6]}…{k[-4:]}"

    def describe(self) -> str:
        return f"{self.label} / {self.effective_model} / key={self.masked_key()}"


def from_headers(provider: str, api_key: str, model: str = "", base_url: str = "",
                 custom_base_url_allowed: bool = True) -> Optional[LLMCredentials]:
    """从请求头构造凭证；缺 provider 或 key 就返回 None（由 api 层转成 400）。"""
    provider = (provider or "").strip().lower()
    api_key = (api_key or "").strip()
    if not provider or not api_key:
        return None
    if provider not in PROVIDERS:
        # 未知平台名：仍然允许，但按 OpenAI 兼容处理，且必须自带 base_url
        if not (base_url or "").strip():
            return None
        return LLMCredentials(provider=provider, api_key=api_key, model=model.strip(),
                              base_url=base_url.strip(), protocol="openai")
    meta = PROVIDERS[provider]
    return LLMCredentials(
        provider=provider,
        api_key=api_key,
        model=(model or "").strip(),
        base_url=(base_url or "").strip() if custom_base_url_allowed else "",
        protocol=meta["protocol"],
    )


# ---------------------------------------------------------------- 同形状适配层
class _Msg:
    __slots__ = ("content",)

    def __init__(self, content: str):
        self.content = content


class _Delta:
    __slots__ = ("content",)

    def __init__(self, content: str):
        self.content = content


class _Choice:
    __slots__ = ("message", "delta")

    def __init__(self, message=None, delta=None):
        self.message = message
        self.delta = delta


class _Resp:
    __slots__ = ("choices",)

    def __init__(self, text: str):
        self.choices = [_Choice(message=_Msg(text))]


class _Chunk:
    __slots__ = ("choices",)

    def __init__(self, text: str):
        self.choices = [_Choice(delta=_Delta(text))]


class _Completions:
    def __init__(self, creds: LLMCredentials):
        self._creds = creds

    def create(self, *, model: str = "", messages: list, temperature: float = 0.7,
               max_tokens: int = 1024, stream: bool = False):
        model = model or self._creds.effective_model
        if self._creds.protocol == "anthropic":
            return _anthropic_create(self._creds, model, messages, temperature, max_tokens, stream)
        return _openai_create(self._creds, model, messages, temperature, max_tokens, stream)


class _Chat:
    def __init__(self, creds: LLMCredentials):
        self.completions = _Completions(creds)


class LLMClient:
    """和 openai SDK 同形状的最小客户端：只用 chat.completions.create(...)。"""

    def __init__(self, creds: LLMCredentials):
        self.creds = creds
        self.chat = _Chat(creds)


def build_client(creds: LLMCredentials) -> LLMClient:
    return LLMClient(creds)


# ---------------------------------------------------------------- 两种协议
def _openai_create(creds: LLMCredentials, model: str, messages: list, temperature: float,
                   max_tokens: int, stream: bool):
    from openai import OpenAI   # 延迟导入：不配 key 的部署少走一段初始化

    client = OpenAI(api_key=creds.api_key, base_url=creds.effective_base_url, timeout=120)
    resp = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature,
        max_tokens=max_tokens, stream=stream,
    )
    if not stream:
        return _Resp((resp.choices[0].message.content or "").strip())

    def gen() -> Iterator[_Chunk]:
        for chunk in resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None)
            if text:
                yield _Chunk(text)

    return gen()


def _anthropic_create(creds: LLMCredentials, model: str, messages: list, temperature: float,
                      max_tokens: int, stream: bool):
    """Anthropic /v1/messages。system 单独一个字段，其余消息只留 user/assistant。"""
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    conv = [{"role": m["role"], "content": m["content"]}
            for m in messages if m.get("role") in ("user", "assistant")]
    if not conv:
        conv = [{"role": "user", "content": ""}]

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": conv,
    }
    if system_parts:
        body["system"] = "\n\n".join(system_parts)

    headers = {
        "x-api-key": creds.api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
        **creds.extra_headers,
    }
    url = f"{creds.effective_base_url}/v1/messages"

    if not stream:
        with httpx.Client(timeout=120) as c:
            r = c.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text")
        return _Resp(text.strip())

    def gen() -> Iterator[_Chunk]:
        with httpx.Client(timeout=120) as c:
            with c.stream("POST", url, headers=headers, json={**body, "stream": True}) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        evt = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if evt.get("type") == "content_block_delta":
                        text = (evt.get("delta") or {}).get("text")
                        if text:
                            yield _Chunk(text)

    return gen()
