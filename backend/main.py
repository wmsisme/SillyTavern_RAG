import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import HF_ENDPOINT, FRONTEND_DIR

os.environ.setdefault("HF_ENDPOINT", HF_ENDPOINT)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from backend.models.database import init_db


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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.api.rag import router as rag_router
from backend.api.cards import router as cards_router
from backend.api.worldbooks import router as worldbooks_router
from backend.api.update import router as update_router
from backend.api.tools import router as tools_router
from backend.api.health import router as health_router

app.include_router(health_router, tags=["健康检查"])
app.include_router(rag_router, prefix="/api", tags=["RAG问答"])
app.include_router(cards_router, prefix="/api", tags=["角色卡"])
app.include_router(worldbooks_router, prefix="/api", tags=["世界书"])
app.include_router(update_router, prefix="/api", tags=["文档更新"])
app.include_router(tools_router, prefix="/api/tools", tags=["工具箱"])

_dist_dir = FRONTEND_DIR / "dist"
if _dist_dir.exists() and _dist_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="static")
