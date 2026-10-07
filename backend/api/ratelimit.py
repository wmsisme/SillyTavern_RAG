"""按 IP 限流（滑动窗口）。

限额口径（2026-10-06 定）：每个 IP 每分钟 50 次。

**但 50 次只算"贵的 / 会被刷的"那些接口**：搜索、问答、AI 生成、工具箱、文档更新。
列表 / 图片 / CRUD 这类日常请求**不计数** —— 否则用户正常翻两页卡库
（一次列表 + 20 张图片）就把自己限住了，看起来像 bug 而不是保护。

登录 / 注册**单独一档**（更严），防的是拿脚本撞密码。

实现说明：
  · 进程内存里的滑动窗口（deque 存时间戳），单进程 uvicorn 够用；
    将来上多 worker 再换 Redis —— 这里刻意不引新依赖。
  · 默认**不信任** X-Forwarded-For（客户端能随便伪造）；只有确实部署在反向代理后面
    才设 TRUST_PROXY=1，那时才读它。
环境变量：RATE_LIMIT_PER_MIN（默认 50）、RATE_LIMIT_AUTH_PER_MIN（默认 10）、
          RATE_LIMIT_ENABLED（默认 1）、TRUST_PROXY（默认 0）
"""
import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Iterable, Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# 贵的 / 会被刷的接口（前缀匹配）
HEAVY_PREFIXES: tuple = (
    "/api/rag/",              # 检索与问答：每次都要调 embedding + rerank
    "/api/cards/generate",    # AI 生成角色卡 / 状态栏 / 开场白
    "/api/cards/suggest-tags",
    "/api/worldbooks/generate",
    "/api/worldbooks/suggest-entries",
    "/api/tools/",            # 工具箱：CPU 与解析都在这
    "/api/llm/test",          # 拿它当免费代理试 key 的，要挡
    "/api/update/",           # 文档索引更新
    "/api/feedback",          # 用户反馈：防刷（正常没人一分钟发 50 条）
)
AUTH_PREFIXES: tuple = (
    "/api/auth/login",
    "/api/auth/register",
)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() not in ("0", "", "false", "no", "off")


PER_MINUTE = _env_int("RATE_LIMIT_PER_MIN", 50)
AUTH_PER_MINUTE = _env_int("RATE_LIMIT_AUTH_PER_MIN", 10)
ENABLED = _env_bool("RATE_LIMIT_ENABLED", True)
TRUST_PROXY = _env_bool("TRUST_PROXY", False)


class SlidingWindow:
    """某类接口的滑动窗口计数器（窗口固定 60 秒）。"""

    def __init__(self, name: str, limit: int, window: float = 60.0, max_keys: int = 20_000):
        self.name = name
        self.limit = limit
        self.window = window
        self.max_keys = max_keys
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def hit(self, key: str, now: Optional[float] = None) -> Tuple[bool, int]:
        """记一次请求。返回 (是否放行, 还要等几秒)。"""
        now = now if now is not None else time.monotonic()
        q = self._hits[key]
        cutoff = now - self.window
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= self.limit:
            retry_after = max(1, int(self.window - (now - q[0])) + 1)
            return False, retry_after
        q.append(now)
        if len(self._hits) > self.max_keys:      # 防内存无限涨：清掉已空的桶
            for k in [k for k, v in self._hits.items() if not v]:
                self._hits.pop(k, None)
        return True, 0

    def reset(self) -> None:
        self._hits.clear()


def client_ip(request: Request) -> str:
    if TRUST_PROXY:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
        real = request.headers.get("x-real-ip", "").strip()
        if real:
            return real
    return request.client.host if request.client else "unknown"


def _match(path: str, prefixes: Iterable[str]) -> bool:
    return any(path.startswith(p) for p in prefixes)


def install_rate_limit(app: FastAPI) -> None:
    """挂到 FastAPI 上。测试里可以设 RATE_LIMIT_ENABLED=0 关掉。"""
    if not ENABLED:
        print("[ratelimit] 已按配置关闭（RATE_LIMIT_ENABLED=0）")
        return

    heavy = SlidingWindow("heavy", PER_MINUTE)
    auth = SlidingWindow("auth", AUTH_PER_MINUTE)
    app.state.rate_limiter_heavy = heavy
    app.state.rate_limiter_auth = auth

    @app.middleware("http")
    async def _rate_limit(request: Request, call_next):
        path = request.url.path
        bucket = auth if _match(path, AUTH_PREFIXES) else (heavy if _match(path, HEAVY_PREFIXES) else None)
        if bucket is not None:
            ip = client_ip(request)
            ok, retry_after = bucket.hit(f"{bucket.name}:{ip}")
            if not ok:
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"请求太频繁了：{bucket.name} 类接口每 IP 每分钟上限 "
                                      f"{bucket.limit} 次，请 {retry_after} 秒后再试。"},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)

    print(f"[ratelimit] 已启用：贵接口 {PER_MINUTE}/分钟/IP，登录注册 {AUTH_PER_MINUTE}/分钟/IP"
          f"{'（信任 X-Forwarded-For）' if TRUST_PROXY else ''}")
