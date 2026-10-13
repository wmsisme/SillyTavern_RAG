# -*- coding: utf-8 -*-
"""「文档中心」接口 —— 把官方文档的中文译文（`backend/docs_zh/`）发给前端。

数据来自 `tools/gen_docs_zh.py` 的产物，本模块**只读**、不翻译、不写盘：
  · GET /api/docs/tree                    导航树 + 元信息（首次访问量）
  · GET /api/docs/article?route=/usage/faq/   单篇正文（markdown）
  · GET /api/docs/asset?path=/assets/x.png    文档内引用的图片/字体

权限口径：**公开可读、免登录**（2026-10-13 达铭定），和首页搜索、工具箱同一档。
所以这里不做登录校验，但必须守住两条线：
  ① **路径穿越**（`..`、绝对路径）—— 解析出的真实路径必须落在允许的根目录内；
  ② **后缀白名单** —— asset 只发文档的图片/字体，别把 .md/.py/.db 之类漏出去。

限流：**刻意不计入** `ratelimit.HEAVY_PREFIXES`。理由与「列表/图片不计数」相同 ——
读文档是纯本地小文件读取，一页正文要连带取图，计进去会让正常翻阅的人自己把自己限住。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from ..config import RAG_DIR, ROOT_DIR

_logger = logging.getLogger("backend.docs")

router = APIRouter()

DOCS_DIR = ROOT_DIR / "backend" / "docs_zh"
MANIFEST_PATH = DOCS_DIR / "manifest.json"
ASSETS_ROOT = RAG_DIR / "SillyTavern-Docs"

# 允许经 asset 接口暴露的后缀（与 gen_docs_zh.ASSET_SUFFIXES 保持一致）
ASSET_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".css", ".woff", ".woff2", ".ttf", ".eot", ".txt", ".pdf",
})
# 单文件上限：文档里的配图都很小，超过这个体积的一律不发（防止哪天塞进大文件当免费图床）
ASSET_MAX_BYTES = 8 * 1024 * 1024


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        # 产物缺失时**不返回空树**：那会表现成"文档中心打不开"，而根因是没生成。
        # 直接把补救命令写进错误里，部署现场一眼能看懂。
        raise HTTPException(
            status_code=503,
            detail="文档中心尚未生成：请先运行 python tools/gen_docs_zh.py",
        )
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # 产物坏了也要说清楚，别静默给空树
        _logger.error("docs manifest 解析失败: %s", exc)
        raise HTTPException(status_code=500, detail="文档中心产物损坏（manifest.json 无法解析）")


def _safe_join(root: Path, rel: str) -> Optional[Path]:
    """把相对路径安全地拼到 root 下；越界（`..`/绝对路径/软链逃逸）返回 None。"""
    if not rel:
        return None
    try:
        candidate = (root / rel.lstrip("/\\")).resolve()
    except (OSError, RuntimeError):
        return None
    root_resolved = root.resolve()
    if candidate == root_resolved or root_resolved not in candidate.parents:
        return None
    return candidate


def route_to_relpath(route: str) -> Optional[str]:
    """`/usage/macros/` → `usage/macros.md`；路由不合法返回 None。

    与生成器同一套规则，但**不允许**空路由（文档中心首页由前端处理，不落到文件）。
    """
    route = (route or "").strip()
    if not route.startswith("/"):
        route = "/" + route
    parts = [p for p in route.strip("/").split("/") if p]
    if not parts:
        return None
    if any(p in (".", "..") for p in parts):
        return None
    return "/".join(parts[:-1] + [f"{parts[-1]}.md"])


@router.get("/docs/tree")
async def docs_tree():
    """导航树 + 元信息。前端进页面只拉一次。"""
    manifest = _load_manifest()
    flat = manifest.get("flat") or []
    return JSONResponse({
        "commit": manifest.get("commit", ""),
        "rootTitle": manifest.get("rootTitle", "官方文档"),
        "pages": manifest.get("pages", 0),
        "articles": manifest.get("articles", 0),
        "synthetic": max(0, int(manifest.get("pages", 0)) - int(manifest.get("articles", 0))),
        "routes": [f["route"] for f in flat if f.get("hasPage")],
        "tree": manifest.get("tree", {}),
    })


@router.get("/docs/article")
async def docs_article(route: str = Query(..., min_length=1, max_length=300)):
    """按路由取一篇正文（含合成索引页）。"""
    manifest = _load_manifest()
    known = {f["route"]: f for f in (manifest.get("flat") or [])}
    normalized = route if route.startswith("/") else "/" + route
    if not normalized.endswith("/"):
        normalized_alt = normalized + "/"
    else:
        normalized_alt = normalized.rstrip("/")
    node = known.get(normalized) or known.get(normalized_alt)
    if not node:
        raise HTTPException(status_code=404, detail="没有这篇文档")

    rel = node.get("path") or route_to_relpath(node["route"])
    # ⚠️ 走**清单里记的路径**，不是凭 route 现拼 —— 清单是生成时写的，改动只在生成器一处
    target = _safe_join(DOCS_DIR, rel or "")
    if not target or not target.is_file():
        _logger.error("清单里的文档不存在：route=%s path=%s", node["route"], rel)
        raise HTTPException(status_code=404, detail="这篇文档的正文缺失（请重新生成文档中心）")

    return JSONResponse({
        "route": node["route"],
        "title": node.get("title") or node["route"],
        "synthetic": bool(node.get("synthetic")),
        # 顶层节点（`/`、`/usage/` …）：前端据此**不再重复渲染正文里的 H1** ——
        # 页头已经把大标题写了一遍，正文再有 H1 就是同一句话连排两行。
        "topLevel": node["route"] == "/" or node["route"].count("/") <= 2,
        "source": node.get("sourceRel") or "",
        "content": target.read_text(encoding="utf-8"),
    })


@router.get("/docs/asset")
async def docs_asset(path: str = Query(..., min_length=1, max_length=500)):
    """文档里引用的静态资源（图片/字体）。只读、白名单后缀。"""
    suffix = Path(path).suffix.lower()
    if suffix not in ASSET_SUFFIXES:
        raise HTTPException(status_code=403, detail="该类型文件不通过此接口提供")
    target = _safe_join(ASSETS_ROOT, path)
    if not target or not target.is_file():
        raise HTTPException(status_code=404, detail="资源不存在")
    try:
        if target.stat().st_size > ASSET_MAX_BYTES:
            raise HTTPException(status_code=413, detail="资源过大")
    except OSError:
        raise HTTPException(status_code=404, detail="资源不存在")
    return FileResponse(target)
