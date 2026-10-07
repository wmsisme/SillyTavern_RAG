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

import ipaddress
import json
import os
import socket
import threading
from dataclasses import dataclass, field
from typing import Iterator, Optional
from urllib.parse import urlparse

import httpx

ANTHROPIC_VERSION = "2023-06-01"

# ---------------------------------------------------------------- 出网安全
# 背景（2026-10-07 安全测试）：base_url 是**请求头里带进来的**，而 /api/llm/test
# 连登录都不需要。原来后端会照着这个地址直接发请求 —— 等于给任何访客一个
# 「让服务器替我发请求」的开关（SSRF）：实测能探本机端口、把目标响应片段回显在
# 错误信息里（http://127.0.0.1:8000/health → 405 + 对方的 JSON 原文）。
#
# 所以：**凡是要连出去的地址，先证明它指向公网**。判据用 is_global ——
# 一举排除环回 / 私有 / 链路本地 / 保留 / 文档段 / CGNAT（含 Tailscale 的
# 100.64.0.0/10，本机自己就在这个网段里）。
_BLOCKED_IP_HINT = "自定义地址不能指向内网 / 本机地址（服务器安全策略）"

# 单次外部调用的超时：连接一定要短（黑洞地址 8 秒就放弃），读可以长一点
# （大模型生成本来就慢）。原来一个 timeout=120 全包，攻击者指一个"只接受连接、
# 不回包"的地址就能把这一个线程按住两分钟 —— 40 个并发就把 FastAPI 的
# 线程池占满，全站同步接口一起卡死。
LLM_TIMEOUT = httpx.Timeout(connect=8.0, read=120.0, write=20.0, pool=5.0)

# 同时在途的外部调用数（进程级）。超过就快速失败，而不是无限排队把线程吃光。
MAX_CONCURRENT_CALLS = int(os.environ.get("LLM_MAX_CONCURRENT", "8") or 8)
_LLM_SLOTS = threading.BoundedSemaphore(max(1, MAX_CONCURRENT_CALLS))
SLOT_WAIT_SECONDS = 15.0


class LLMBusyError(RuntimeError):
    """在途调用太多，这次没抢到名额（明确告诉用户"稍后再试"，别让他白等）。"""


def _blocked_ip(ip) -> bool:
    return (not ip.is_global) or ip.is_multicast


def validate_base_url(url: str) -> str:
    """校验用户给的 base_url，返回原值；不合规抛 ValueError（消息直接给用户看）。

    两道：① 协议只能是 http/https；② 主机名解析出的**每一个** IP 都必须是公网地址。
    解析用 socket.getaddrinfo（域名与裸 IP 都覆盖），所以 http://127.0.0.1、
    http://[::1]、http://10.0.0.1、http://169.254.169.254（云元数据）都会被挡住。

    残留风险（如实记着）：校验时解析一次、真正连接时又解析一次，
    理论上存在 DNS rebinding 的时间窗。缓解手段是**禁跟随重定向** + 短连接超时，
    要彻底堵死得在连接层校验对端 IP —— 目前这个威胁模型下不值得引那么重的东西。
    """
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("自定义地址必须以 http:// 或 https:// 开头")
    host = parsed.hostname
    if not host:
        raise ValueError("自定义地址里没有主机名")
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"这个地址解析不了：{host}")
    for info in infos:
        addr = info[4][0]
        try:
            # 去掉 IPv6 的 scope id（fe80::1%eth0）
            ip = ipaddress.ip_address(addr.split("%", 1)[0])
        except ValueError:
            continue
        if _blocked_ip(ip):
            raise ValueError(_BLOCKED_IP_HINT)
    return raw


def _http_client() -> httpx.Client:
    """发往外部平台用的 HTTP 客户端。

    两个关键设置：
      · follow_redirects=False —— 否则一个公网域名 302 到 http://127.0.0.1:8000
        就绕过了上面那道校验（校验只发生在发请求之前）。
      · 分项超时 —— 见 LLM_TIMEOUT 的注释。
    """
    return httpx.Client(follow_redirects=False, timeout=LLM_TIMEOUT)

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
    """从请求头构造凭证；缺 provider 或 key 就返回 None（由 api 层转成 400）。

    base_url 不合规（指向内网 / 协议不对）会抛 ValueError ——
    调用方要把它转成 400 并把原话回给用户，而不是当成服务端错误。
    """
    provider = (provider or "").strip().lower()
    api_key = (api_key or "").strip()
    if not provider or not api_key:
        return None
    # 自定义地址先过 SSRF 校验；不允许自定义时一律用注册表里的内置地址
    base_url = validate_base_url(base_url) if custom_base_url_allowed else ""
    if provider not in PROVIDERS:
        # 未知平台名：仍然允许，但按 OpenAI 兼容处理，且必须自带 base_url
        if not base_url:
            return None
        return LLMCredentials(provider=provider, api_key=api_key, model=model.strip(),
                              base_url=base_url, protocol="openai")
    meta = PROVIDERS[provider]
    return LLMCredentials(
        provider=provider,
        api_key=api_key,
        model=(model or "").strip(),
        base_url=base_url,
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
        # 名额从发请求一直占到生成结束（流式也要占）—— 这是防「慢速请求拖死线程池」的关键：
        # 抢不到名额立刻失败，让用户重试，而不是把线程一个个搭进去。
        if not _LLM_SLOTS.acquire(timeout=SLOT_WAIT_SECONDS):
            raise LLMBusyError(
                f"服务器同时在处理的外部调用已达上限（{MAX_CONCURRENT_CALLS} 个），请稍后再试")
        try:
            if self._creds.protocol == "anthropic":
                out = _anthropic_create(self._creds, model, messages, temperature,
                                        max_tokens, stream)
            else:
                out = _openai_create(self._creds, model, messages, temperature,
                                     max_tokens, stream)
        except BaseException:
            _LLM_SLOTS.release()
            raise
        if not stream:
            _LLM_SLOTS.release()
            return out
        return _releasing(out)


def _releasing(gen: Iterator):
    """流式生成器的包装：迭代完（或中途出错 / 客户端断开）就把并发名额还回去。"""
    try:
        yield from gen
    finally:
        _LLM_SLOTS.release()


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

    # timeout 交给 http_client（SDK 在传入 http_client 时以它为准），
    # 关键是 follow_redirects=False —— 挡住"公网域名 302 到 127.0.0.1"这条绕过路
    client = OpenAI(api_key=creds.api_key, base_url=creds.effective_base_url,
                    http_client=_http_client())
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
        # 同一个 client 配置：不跟随重定向 + 分项超时（理由见 _http_client）
        with _http_client() as c:
            r = c.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text")
        return _Resp(text.strip())

    def gen() -> Iterator[_Chunk]:
        with _http_client() as c:
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
