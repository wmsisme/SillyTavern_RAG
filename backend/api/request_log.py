"""请求日志中间件：一行一个请求，落在 logs/app.log。

**必须装在最外层**（main.py 里最后 install，理由见那里的注释，也见本文件的 finally 块）：
被封禁挡掉（403）、被限流拒绝（429）的请求，恰恰是排查滥用时最想看的那些 ——
装在里面的话，它们连一行记录都不会留下。

**记**：方法 / 路径 / 状态码 / 耗时 / 客户端 IP / 请求 ID
**不记**：请求体、查询串、Cookie、任何 header 的值 ——
  查询串里可能有用户的搜索词，header 里有 API Key，两者都不该进日志文件。

慢请求单独打 WARNING（阈值 `REQUEST_SLOW_MS`，默认 3000ms）。
这类日志是「用户觉得卡」的第一个客观证据 —— 在此之前只能靠感觉。
"""
import logging
import os
import time

from fastapi import FastAPI, Request

from backend.api import metrics
from backend.api.ratelimit import client_ip
from backend.services import logging_setup

log = logging.getLogger("backend.request")


def install_request_log(app: FastAPI) -> None:
    slow_ms = int(os.environ.get("REQUEST_SLOW_MS", "3000"))

    @app.middleware("http")
    async def _request_log(request: Request, call_next):
        rid = logging_setup.new_request_id()
        token = logging_setup.request_id_var.set(rid)
        started = time.perf_counter()
        status = 500
        method, path = request.method, request.url.path
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception:
            # 未捕获异常：先在这里记一份带堆栈的，再把异常抛回去交给 FastAPI 的处理链
            # （不吞异常 —— 吞了客户端就拿不到 500，排查时反而少一条线索）
            log.exception("未捕获异常 %s %s", method, path)
            raise
        finally:
            ms = (time.perf_counter() - started) * 1000
            try:
                ip = client_ip(request)
            except Exception:           # 极端情况下 request 状态已不可用，别让日志把响应带崩
                ip = "unknown"
            line, args = "%s %s → %s  %.0fms  ip=%s", (method, path, status, ms, ip)
            if status >= 500:
                log.error(line, *args)
            elif status >= 400:
                log.warning(line, *args)          # 4xx 大概率是探测/滥用，值得单独看见
            elif ms >= slow_ms:
                log.warning(line + f"  ⚠ 慢请求(>{slow_ms}ms)", *args)
            else:
                log.info(line, *args)
            # 顺手把指标喂给 /metrics（它本来就在算耗时和状态码，不必再挂一个中间件）。
            # record() 内部吞掉所有异常：指标丢了事小，请求被带崩事大。
            metrics.record(method, path, status, ms)
            # ⚠️ 顺序要紧：日志写完再还原 contextvar。
            # 反过来写的话 req_id 已经变回 "-"，这条日志就没有请求 ID 了。
            logging_setup.request_id_var.reset(token)

    logging.getLogger(__name__).info(
        "[request-log] 已启用（慢请求阈值 %dms，日志落在 logs/app.log）", slow_ms)
