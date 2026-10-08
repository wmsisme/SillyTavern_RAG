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
    "/api/errors",            # 前端错误上报：**免登录**，必须防刷 ——
                              # 否则一个坏掉的前端（比如某段代码自己触发崩溃循环）
                              # 能在一分钟内把 client_errors 表灌满
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
# 未登录访客的额度（2026-10-07 加固）：检索接口**不需要登录**，
# 而每一次检索都在烧站长的 embedding / rerank 额度（硅基流动免费档也有 RPM 上限）。
# 登录用户照旧 50，匿名 30 —— 正常人一次问答就是一个请求；
# 之所以不敢压得更低（比如 20）：多个用户可能共用同一个 NAT 出口 IP，
# 匿名档压太狠会把他们一起误伤（测试里 8 个并发请求就撞过这个）。
ANON_PER_MINUTE = _env_int("RATE_LIMIT_ANON_PER_MIN", 30)
AUTH_PER_MINUTE = _env_int("RATE_LIMIT_AUTH_PER_MIN", 10)
ENABLED = _env_bool("RATE_LIMIT_ENABLED", True)
TRUST_PROXY = _env_bool("TRUST_PROXY", False)

# 会话 Cookie 名（判断"这次请求是不是登录用户"）。只为分档用，不校验有效性 ——
# 校验要走数据库，而中间件是每个请求的必经之路，不该在这儿加一次查询。
try:
    from backend.services.auth_service import COOKIE_NAME as SESSION_COOKIE
except Exception:                                   # pragma: no cover
    SESSION_COOKIE = "strag_session"


class SlidingWindow:
    """某类接口的滑动窗口计数器（窗口固定 60 秒）。"""

    def __init__(self, name: str, limit: int, window: float = 60.0, max_keys: int = 20_000):
        self.name = name
        self.limit = limit
        self.window = window
        self.max_keys = max_keys
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def hit(self, key: str, now: Optional[float] = None,
            limit: Optional[int] = None) -> Tuple[bool, int]:
        """记一次请求。返回 (是否放行, 还要等几秒)。

        limit 可以按本次请求覆盖（未登录访客走更小的一档，见 install_rate_limit）。
        """
        cap = self.limit if limit is None else limit
        now = now if now is not None else time.monotonic()
        q = self._hits[key]
        cutoff = now - self.window
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= cap:
            if not q:                      # cap 被配成 0 之类的极端情况：直接拒，别去摸 q[0]
                return False, int(self.window) + 1
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
    """取客户端 IP（挂反代时必须拿到**真实**的那个）。

    ⚠️ TRUST_PROXY 时取的是 X-Forwarded-For 的**最后一段**，不是第一段：
    反向代理是**追加**这个头的（结果是 `客户端伪造的值, …, 真实客户端`），
    取第一段等于让客户端自己报 IP —— 那样限流能被刷穿、封 IP 也封不住任何人。
    只有一层代理时，最后一段就是真实客户端。

    （2026-10-07 为公网映射改的：Tailscale Funnel 代理后面必须能拿到真实 IP，
      否则「按 IP 限流」和「封 IP」这两条安全措施同时失效。）
    """
    if TRUST_PROXY:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            parts = [p.strip() for p in fwd.split(",") if p.strip()]
            if parts:
                return parts[-1]
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
            # 匿名访客额度更低：同一个桶，按"这次带没带会话 Cookie"选档
            anon = not request.cookies.get(SESSION_COOKIE)
            limit = min(bucket.limit, ANON_PER_MINUTE) if anon else bucket.limit
            ok, retry_after = bucket.hit(f"{bucket.name}:{ip}", limit=limit)
            if not ok:
                who = "未登录访客" if anon else "每 IP"
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"请求太频繁了：{bucket.name} 类接口{who}每分钟上限 "
                                      f"{limit} 次，请 {retry_after} 秒后再试。"
                                      f"（登录后额度更高）"},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)

    print(f"[ratelimit] 已启用：贵接口 {PER_MINUTE}/分钟/IP（未登录 {min(PER_MINUTE, ANON_PER_MINUTE)}），"
          f"登录注册 {AUTH_PER_MINUTE}/分钟/IP"
          f"{'（信任 X-Forwarded-For）' if TRUST_PROXY else ''}")
