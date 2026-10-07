"""IP 封禁：请求进门的第一道关卡。

为什么不塞进限流里：**语义不同**。限流说的是「你太快了，歇会儿」（429），
封禁说的是「你被禁止访问了」（403）。而且封禁必须挡在限流**之前** ——
否则被封的人还在消耗限流额度、日志里还全是他的请求。

⚠️ 两条硬规矩：
  ① 环回地址（127.0.0.1 / ::1）**永远放行**。一旦前面挂了反向代理，
     所有请求在服务端看来都来自 127.0.0.1 —— 那时封任何一个 IP 都等于把全站封掉。
     同理 admin_service.ban_ip() 会拒绝把环回地址写进黑名单。
  ② 取 IP 的逻辑复用 ratelimit.client_ip()：默认**不信任** X-Forwarded-For
     （客户端能随便伪造），只有确实在反代后面才设 TRUST_PROXY=1。

性能：每个请求查一次 SQLite（本地，亚毫秒）。**刻意不做内存缓存** ——
封禁/解封要立即生效，缓存会引入"刚封了却还进得来"的窗口。
真到高并发多 worker 了再引入共享缓存（那时本来也要换 Redis）。
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.ratelimit import client_ip
from backend.models.database import SessionLocal
from backend.services import admin_service


def install_ip_ban_guard(app: FastAPI) -> None:
    @app.middleware("http")
    async def _ip_ban_guard(request: Request, call_next):
        ip = admin_service.normalize_ip(client_ip(request))
        if admin_service.is_whitelisted(ip):
            return await call_next(request)

        db = SessionLocal()
        try:
            ban = admin_service.get_active_ban(db, ip)
        except Exception:
            ban = None          # 查询出问题不许把整个站点拖垮：放行，让业务层照常跑
        finally:
            db.close()

        if ban is not None:
            tip = f"（原因：{ban.reason}）" if ban.reason else ""
            until = f"，解封时间 {ban.expires_at:%Y-%m-%d %H:%M}" if ban.expires_at else ""
            return JSONResponse(
                status_code=403,
                content={"detail": f"这个 IP 已被本站封禁{tip}{until}。"
                                   f"如果你认为这是误封，请联系站长。"},
            )
        return await call_next(request)

    print("[ban] IP 封禁检查已启用（环回地址始终放行）")
