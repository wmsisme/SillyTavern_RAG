import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.config import HF_ENDPOINT, FRONTEND_DIR, STATIC_DIR

os.environ.setdefault("HF_ENDPOINT", HF_ENDPOINT)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from backend.models.database import init_db
from backend.api.ban_guard import install_ip_ban_guard
from backend.api.ratelimit import install_rate_limit
from backend.api.request_log import install_request_log
from backend.services.logging_setup import setup_logging

# 顶层就把日志配好：后面那几行「xxx 已启用」也要能落到文件里。
# setup_logging() 幂等，重复调用无副作用。
setup_logging()

# ---------------------------------------------------------------- 生产安全默认
# 交互式文档默认**关掉**（2026-10-07 安全测试发现 /docs、/redoc、/openapi.json
# 在公网是敞开的：等于把一张完整的接口地图递给来访者）。
# 本地想看文档：在 .env 里写 ENABLE_DOCS=1。
def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() not in ("0", "", "false", "no", "off")


ENABLE_DOCS = _flag("ENABLE_DOCS")
CSP_ENABLED = _flag("CSP_ENABLED", "1")

# 请求体上限（2026-10-07 加固）。**分两档**，因为两类请求的代价不一样：
#   · multipart 上传：Starlette 会把它落到磁盘临时文件，内存压力小，
#     真正的天花板由各接口自己卡（工具箱 10MB / 卡图 8MB）——这里放宽到 64MB，
#     只是不让"上传 1GB"这种事跑到解析阶段（那样磁盘先满）。
#   · 其它（JSON 等）：解析结果**整个进内存**，卡紧一点。
# 为什么不全用一个小值：Content-Length 一超就在**读完之前**回 413，
# 客户端（还在往里写 body）看到的是"连接被断开"，而不是那句人话。
# 所以这里只挡"离谱的大"，把"稍微超限"留给接口自己给出友好提示。
MAX_BODY_JSON = 16 * 1024 * 1024
MAX_BODY_MULTIPART = 64 * 1024 * 1024


def _ensure_rag_index():
    from backend.services.rag_service import _get_collection
    col = _get_collection()
    print(f"ChromaDB 索引就绪: {col.count()} 条记录")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _ensure_rag_index()
    yield


app = FastAPI(
    title="SillyTavern RAG 知识库",
    description="SillyTavern 知识库检索与角色卡/世界书管理平台",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    """安全响应头（2026-10-07 补）——原来一个都没有。

    · nosniff      —— 别让浏览器"猜"类型：上传的图片被当成脚本执行就麻烦了
    · X-Frame-Options / frame-ancestors —— 防点击劫持（把本站套进 iframe 骗点击）
    · Referrer-Policy —— 跳到外部站点时不带完整 URL（URL 里可能带查询词）
    · CSP          —— 纵深防御：只准加载本站资源。前端构建产物只有 1 个 JS + 1 个 CSS，
                      没有内联脚本、没有外部 CDN，所以 script-src 'self' 是合身的；
                      style 必须放 'unsafe-inline'（antd 运行时注入样式）。
                      万一页面因此显示异常：.env 里 CSP_ENABLED=0 即可关掉。
    · HSTS         —— 只在 https 请求上加（本机 http://127.0.0.1 访问时加了没用，
                      反而会让浏览器把 localhost 记成强制 https）

    顺手在这里挡住超大请求体（见 MAX_BODY_BYTES）：**能在读完之前拒绝，就别读完再说**。
    """
    cl = request.headers.get("content-length", "")
    if cl.isdigit():
        is_upload = request.headers.get("content-type", "").startswith("multipart/form-data")
        cap = MAX_BODY_MULTIPART if is_upload else MAX_BODY_JSON
        if int(cl) > cap:
            return JSONResponse(
                status_code=413,
                content={"detail": f"请求体太大了（上限 {cap // 1024 // 1024} MB）"},
            )

    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()")
    resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if CSP_ENABLED:
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
        )
    if request.url.scheme == "https":
        resp.headers.setdefault("Strict-Transport-Security", "max-age=15552000")
    return resp


# 顺序有讲究：**封禁挡在限流之前** —— 已被封的 IP 不该继续消耗限流额度，
# 日志里也不该继续刷它的请求。
#
# ⚠️ Starlette 的 add_middleware 是往列表**头部插**的，所以**后安装的在外层、先执行**。
# 想让封禁先跑，就得**后安装它** —— 顺序写反过一次（2026-10-07 复查发现），
# 结果是限流跑在封禁前面：被封的 IP 照样消耗额度、拿到的还是 429 而不是"你被封了"。
#
# 请求日志**最后安装 = 最外层**（2026-10-08 加）：这样被封禁/限流挡掉的请求
# 也会留下一行日志 —— 那些 403 / 429 恰恰是排查滥用时最需要看的。
# 装在里面的话，被挡的请求在日志里根本不存在，"某个 IP 被挡了多少次"就永远查不到。
install_rate_limit(app)
install_ip_ban_guard(app)
install_request_log(app)

from backend.api.rag import router as rag_router
from backend.api.cards import router as cards_router
from backend.api.worldbooks import router as worldbooks_router
from backend.api.update import router as update_router
from backend.api.tools import router as tools_router
from backend.api.health import router as health_router
from backend.api.auth import router as auth_router
from backend.api.llm import router as llm_router
from backend.api.admin import router as admin_router
from backend.api.errors import router as errors_router
from backend.api.feedback import router as feedback_router
from backend.api.metrics import router as metrics_router

app.include_router(health_router, tags=["健康检查"])
app.include_router(auth_router, prefix="/api", tags=["账号"])
app.include_router(llm_router, prefix="/api", tags=["大模型平台"])
app.include_router(rag_router, prefix="/api", tags=["RAG问答"])
app.include_router(cards_router, prefix="/api", tags=["角色卡"])
app.include_router(worldbooks_router, prefix="/api", tags=["世界书"])
app.include_router(update_router, prefix="/api", tags=["文档更新"])
app.include_router(tools_router, prefix="/api/tools", tags=["工具箱"])
app.include_router(admin_router, prefix="/api", tags=["后台管理"])
app.include_router(feedback_router, prefix="/api", tags=["用户反馈"])
app.include_router(errors_router, prefix="/api", tags=["前端错误上报"])
# /metrics 不挂 /api 前缀 —— Prometheus 的惯例就是根路径。
# 它自带「只看本机」的判断（见 backend/api/metrics.py）：公网请求拿到的是 404。
app.include_router(metrics_router, tags=["运维"])

# 目录先建出来（上传要用），但**不再**挂成静态目录：
# StaticFiles 不鉴权，拿到 URL 的人就能看 —— 那「只有本人能看到自己的卡」就是假的。
# 图片统一走 /api/cards/{id}/image，校验登录态 + 归属后再发文件（见 api/cards.py）。
STATIC_DIR.mkdir(parents=True, exist_ok=True)

_dist_dir = FRONTEND_DIR / "dist"
if _dist_dir.exists() and _dist_dir.is_dir():
    _dist_root = _dist_dir.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """前端静态文件 + SPA 兜底。

        为什么不用 `app.mount(StaticFiles(html=True))`：那样**深链接会 404** ——
        别人直接打开 `/login`、`/cards` 这类前端路由会看到 404，
        而开发模式（Vite）下一切正常，**只有上线才发现**（2026-10-06 在容器里实测踩到）。
        这里显式约定：文件存在就发文件，否则回退 index.html。
        """
        if full_path.startswith("api/") or full_path in ("health", "metrics"):
            # 接口路径不兜底，老老实实 404 —— 免得打错的 API 拿到一个 200 的 HTML。
            # ⚠️ metrics 必须列在这里：它是根路径下的接口（Prometheus 惯例），
            # 不特判的话会被兜底成 index.html —— 那 "只看本机" 那道判断就形同虚设，
            # 公网也能拿到一份前端页面，还会让抓取端拿到一堆 HTML 而以为是空的。
            raise HTTPException(status_code=404, detail="接口不存在")
        candidate = (_dist_root / full_path).resolve()
        if full_path and candidate.is_file() and str(candidate).startswith(str(_dist_root)):
            return FileResponse(candidate)
        # 带扩展名的 = 资源请求（.png/.js/.css…），找不到就该 404，不能回退成页面。
        # 这条不是洁癖：老的角色卡直链 /static/card_images/xxx.png 一旦被兜底成 index.html，
        # 就变成"200 + 一坨 HTML"，把「静态目录不再对外」这条安全断言冲掉了。
        if "." in full_path.rsplit("/", 1)[-1]:
            raise HTTPException(status_code=404, detail="资源不存在")
        index = _dist_root / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="前端还没构建（缺少 frontend/dist）")
