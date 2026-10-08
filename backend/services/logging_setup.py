"""统一日志：让线上不再是黑的。

之前的状态（2026-10-08 之前）：整个 backend 只有 update_service 用了 logging，
其余全是 print —— 而服务是跑在 uvicorn **前台窗口**里的，关掉那个窗口日志就没了。
出问题能拿到的信息只有「用户说刚才点了个啥」。

这个模块负责三件事：
  ① 根 logger → 控制台 + **轮转文件**（默认 logs/app.log，10MB × 5 份）
  ② 统一格式：时间 / 级别 / 模块 / 消息；带请求 ID 时额外带 `req=xxxxxxxx`，
     同一次请求里的多条日志就能串起来（排查时不用靠猜）
  ③ 把 uvicorn 自己的 access / error 日志也接进来 —— 否则它们只打在控制台，
     而且和我们的格式不一致

刻意**不做**的事：不记请求体、不记查询串、不记 Cookie、不记任何 header 的值。
用户的 API Key 就在 header 里（X-LLM-Key），落进日志文件等于泄露 ——
README 里那句「API Key 不落日志」得靠这里守住。

配置项（都从环境变量 / .env 读）：
  LOG_DIR     默认 <项目>/logs
  LOG_LEVEL   默认 INFO
  LOG_MAX_MB  单文件上限，默认 10
  LOG_BACKUPS 保留份数，默认 5
  LOG_TO_FILE 设 0 则只写控制台（调试用）
"""
import logging
import logging.handlers
import os
import uuid
from contextvars import ContextVar
from pathlib import Path

from backend.config import ROOT_DIR

# 当前请求的 ID：由 request_log 中间件设置，_RequestIdFilter 读出来塞进每条日志
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOG_DIR = Path(os.environ.get("LOG_DIR", str(ROOT_DIR / "logs")))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_MAX_MB = int(os.environ.get("LOG_MAX_MB", "10"))
LOG_BACKUPS = int(os.environ.get("LOG_BACKUPS", "5"))
LOG_TO_FILE = os.environ.get("LOG_TO_FILE", "1").strip().lower() not in ("0", "", "false", "no", "off")

_configured = False


def new_request_id() -> str:
    """短 ID 就够：作用是「把同一次请求的多条日志串起来」，不需要全局唯一性。"""
    return uuid.uuid4().hex[:8]


class _RequestIdFilter(logging.Filter):
    """把当前请求 ID 注入每条日志记录。

    用 ContextVar 而不是全局变量：uvicorn 是单进程多协程，全局变量会被并发请求
    互相覆盖 —— 那日志里的 req= 反而变成误导。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.req_id = request_id_var.get()
        return True


def setup_logging() -> None:
    """配好根 logger。**幂等** —— 重复调用只生效一次（--reload 重入、多入口调用都安全）。"""
    global _configured
    if _configured:
        return
    _configured = True

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s [req=%(req_id)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    filt = _RequestIdFilter()

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    for h in list(root.handlers):       # 清掉可能已存在的处理器，避免日志打两遍
        root.removeHandler(h)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.addFilter(filt)
    # ⚠️ handler 上也要设级别（2026-10-08 实测踩到，改第一版时漏了）：
    # root logger 的 level 管不住**从子 logger 传播上来**的记录 —— 那种记录在传播时
    # 不再看 root 的级别，只看各个 handler 的级别（handler 不设 = 0 = 全放行）。
    # jieba 就是这么干的：它 import 时把自己的 logger 设成 DEBUG（**覆盖**掉我们提前设的
    # WARNING），于是词表加载那几行 DEBUG 一路冒到根 logger 上并落进文件。
    # 结论：**设置处（子 logger）和消费处（handler）各守一道才拦得住**。
    console.setLevel(LOG_LEVEL)
    root.addHandler(console)

    log_path = None
    if LOG_TO_FILE:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_path = LOG_DIR / "app.log"
            fh = logging.handlers.RotatingFileHandler(
                log_path, maxBytes=LOG_MAX_MB * 1024 * 1024,
                backupCount=LOG_BACKUPS, encoding="utf-8",
            )
            fh.setFormatter(fmt)
            fh.addFilter(filt)
            fh.setLevel(LOG_LEVEL)      # 同控制台：文件侧也要守一道（理由见上面 handler 那段）
            root.addHandler(fh)
        except OSError as e:
            # 磁盘满 / 只读目录都不该让服务起不来 —— 退化成只打控制台
            log_path = None
            root.warning("日志文件打不开，本次只写控制台：%s", e)

    # uvicorn 的三只 logger 全部交回根 logger：不再各打各的
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    # ⚠️ 关掉 uvicorn 自带的 access log（2026-10-08 实测：不关的话每个请求被记两遍）。
    # 我们那行信息更全 —— 耗时 / 客户端 IP / 请求 ID 都有，它那行只有 IP 和状态码。
    # uvicorn.error 保留（启动、崩溃信息在那儿）。
    logging.getLogger("uvicorn.access").disabled = True

    # 压掉噪音库：jieba 会拿 DEBUG 级打词表加载过程，chromadb / sentence_transformers
    # 之类也爱叨叨，全是每次启动都一样的废话。
    # **httpx 刻意保留 INFO** —— 它那几行「什么时候 POST 了哪个第三方 API」是排查外部依赖
    # 问题时唯一的记录（URL 里不含 key，key 在 header 里，不会因此泄露）。
    for name in ("jieba", "chromadb", "urllib3", "sentence_transformers", "transformers"):
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "日志已就绪 → %s（级别 %s%s）",
        log_path or "仅控制台",
        LOG_LEVEL,
        f"，轮转 {LOG_MAX_MB}MB × {LOG_BACKUPS} 份" if log_path else "",
    )
