"""Prometheus 文本格式的 /metrics —— **零新依赖**。

为什么不装 prometheus_client：这个项目的部署形态是「单容器、本机跑」，
要的指标就那几类（请求数 / 耗时 / 慢请求 / 内存 / 运行时长），自己累计几十行就够，
省一个依赖，也省掉它自带的注册表与多进程那套概念。

**只对本机开放**：指标里带完整的路径清单（等于一张接口地图）和流量分布，不该对公网暴露。
判断用 `client_ip()` —— 注意 `TRUST_PROXY=1` 时它取的是**真实客户端 IP**，
所以经 Funnel 进来的公网请求不是环回地址，会被挡在外面；本机 curl 才拿得到。
对外一律回 404：**不暴露"这里有个 /metrics"**。

**路径必须归一**：`/api/cards/123` → `/api/cards/{id}`。不归一的话，每张卡片都是一个
独立时间序列，指标基数会随数据无限膨胀 —— 这是 Prometheus 用法的头号禁忌，
也会把这台机器的内存吃光。归一之后路径种类是有限的。

数据由 `backend/api/request_log.py` 的中间件在 `finally` 里喂进来（它本来就在算耗时和状态码，
不需要再挂一个中间件）。
"""
import ipaddress
import os
import re
import threading
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from backend.api.ratelimit import client_ip

STARTED_AT = time.time()
SLOW_MS = int(os.environ.get("REQUEST_SLOW_MS", "3000"))

_lock = threading.Lock()
_requests: dict = {}        # (method, path, status) -> 次数
_duration_ms: dict = {}     # path -> 累计耗时(ms)
_slow: dict = {}            # path -> 慢请求次数

_ID_RE = re.compile(r"/\d+")


def normalize_path(path: str) -> str:
    """把路径里的数字段换成 {id} —— 控制指标基数（见模块开头那段说明）。"""
    return _ID_RE.sub("/{id}", path)


def record(method: str, path: str, status: int, ms: float) -> None:
    """记一次请求。**内部吞掉所有异常** —— 指标丢了事小，请求被它带崩事大。"""
    try:
        p = normalize_path(path)
        with _lock:
            key = (method, p, str(status))
            _requests[key] = _requests.get(key, 0) + 1
            _duration_ms[p] = _duration_ms.get(p, 0.0) + ms
            if ms >= SLOW_MS:
                _slow[p] = _slow.get(p, 0) + 1
    except Exception:       # noqa: BLE001
        pass


def _is_local(request: Request) -> bool:
    try:
        return ipaddress.ip_address(client_ip(request)).is_loopback
    except ValueError:      # "unknown" 之类
        return False


def _memory_bytes():
    try:
        import resource
        # Linux 的 ru_maxrss 单位是 KB（macOS 才是字节）。本项目部署在 Linux 容器里，按 KB 算。
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    except Exception:       # noqa: BLE001
        return None


router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def metrics(request: Request):
    if not _is_local(request):
        raise HTTPException(status_code=404, detail="接口不存在")

    with _lock:
        reqs = dict(_requests)
        durs = dict(_duration_ms)
        slow = dict(_slow)

    out = [
        "# HELP strag_up 服务存活（抓不到这一行就是挂了）",
        "# TYPE strag_up gauge",
        "strag_up 1",
        "# HELP strag_uptime_seconds 进程已运行秒数",
        "# TYPE strag_uptime_seconds gauge",
        f"strag_uptime_seconds {time.time() - STARTED_AT:.1f}",
        "# HELP strag_requests_total 请求总数（按 方法/归一化路径/状态码）",
        "# TYPE strag_requests_total counter",
    ]
    for (method, path, status), n in sorted(reqs.items()):
        out.append(f'strag_requests_total{{method="{method}",path="{path}",status="{status}"}} {n}')

    out += [
        "# HELP strag_request_duration_ms_total 各路径累计耗时（毫秒）",
        "# TYPE strag_request_duration_ms_total counter",
    ]
    for path, total in sorted(durs.items()):
        out.append(f'strag_request_duration_ms_total{{path="{path}"}} {total:.1f}')

    out += [
        "# HELP strag_slow_requests_total 慢请求数（超过 REQUEST_SLOW_MS）",
        "# TYPE strag_slow_requests_total counter",
    ]
    for path, n in sorted(slow.items()):
        out.append(f'strag_slow_requests_total{{path="{path}"}} {n}')

    mem = _memory_bytes()
    if mem is not None:
        out += [
            "# HELP strag_process_max_rss_bytes 进程峰值常驻内存",
            "# TYPE strag_process_max_rss_bytes gauge",
            f"strag_process_max_rss_bytes {mem}",
        ]

    return PlainTextResponse(
        "\n".join(out) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
