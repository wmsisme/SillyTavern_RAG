# -*- coding: utf-8 -*-
"""把「官方英文文档的中文译文」还原成一棵可翻阅的文档树（供线上「文档中心」使用）。

来源与口径
----------
· 译文来源 = `RAG/translation_cache.json`（键 = 英文原文 md5，值 = 带 frontmatter 的中文 markdown）。
  **不重新调 API 翻译** —— 缓存里有 112 篇现成译文，直接复用，0 token。
· 路由 = 译文 frontmatter 里的 `route:`（SillyTavern 官方文档走 mkdocs，含 route/order/icon），
  与英文原文文件里的 route 一致；`route → 英文原文相对路径` 靠 md5 对应（91 篇一一对应）。
· 输出 = `backend/docs_zh/`：一篇一个 .md（路径由 route 推导）+ `manifest.json`（导航树与映射）。

设计要点
--------
1. **中间层路由是「合成索引页」**：`/usage/core-concepts/` 这类父级在原文里没有单独文件
   （那些页面用 `index:` 指向了别处），但它们必须出现在导航树里，否则子页无处可挂。
   所以给它们生成一个只列子页的索引页，链接为**站内路由**，不引用 .md 文件。
2. **链接改写成站内路由**：原文里 `./config-yaml.md`、`../Characters/Author's-Note.md`
   这类相对链接，靠 路径→route 映射换成 `/administration/config-yaml/`，前端才点得动。
   映射不到的（assets、外部链接）原样保留，由前端交给 /api/docs/asset 或外链。
3. **幂等**：输出目录整体重建；`manifest.json` 里记 commit + 译文指纹，
   内容没变就跳过（`--force` 可强制）。
4. **刻意剔除**：`redirect` 页（原文里是"此页已移至…"的跳转壳）、
   `visibility: hidden` 的草稿页、以及灌库时混进来的 `# Index Probe (Temporary)` 探针页。

用法：
    python tools/gen_docs_zh.py            # 幂等生成（内容没变则跳过）
    python tools/gen_docs_zh.py --force    # 强制重建
    python tools/gen_docs_zh.py --check    # 只检查产物是否最新，不做修改（CI/测试用）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = ROOT / "RAG"
DOCS_REPO_DIR = RAG_DIR / "SillyTavern-Docs"
TRANSLATION_CACHE_PATH = RAG_DIR / "translation_cache.json"
OUT_DIR = ROOT / "backend" / "docs_zh"
MANIFEST_NAME = "manifest.json"

ROOT_TITLE = "SillyTavern 官方文档（中文）"

# 译文里可能残留的"重建探针"页（当时为触发索引重建临时加的，已被删除，不该进导航树）
_PROBE_RE = re.compile(r"^#\s*Index Probe", re.I)
# 灌库自检用的临时文档（`/verify/deletion-probe/` 之类）：只验证增量更新会删旧块，不该给读者看
_JUNK_ROUTE_RE = re.compile(r"^/(verify|test|tmp)(/|$)", re.I)
_JUNK_TITLE_RE = re.compile(r"删除探测|deletion[- ]?probe", re.I)

# 允许经 /api/docs/asset 暴露的静态资源后缀（白名单，不给 .md/.py 之类）
ASSET_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".css", ".woff", ".woff2", ".ttf", ".eot", ".txt", ".pdf",
)


# --------------------------------------------------------------------------- #
# 基础解析
# --------------------------------------------------------------------------- #
def split_frontmatter(text: str):
    """拆出 YAML frontmatter（只取标量键值，够用即可）与正文。

    返回 (meta: dict, body: str)。没有 frontmatter 时 meta 为空、body 为原文。
    """
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, text[m.end():]


def first_heading(body: str):
    m = re.search(r"^#\s+(.+?)\s*$", body, re.M)
    return m.group(1).strip() if m else None


def route_to_relpath(route: str) -> Path:
    """`/usage/core-concepts/macros/` → `usage/core-concepts/macros.md`。"""
    parts = [p for p in route.strip("/").split("/") if p]
    if not parts:
        return Path("index.md")
    return Path(*parts[:-1]) / f"{parts[-1]}.md"


def route_depth(route: str) -> int:
    return len([p for p in route.strip("/").split("/") if p])


def build_route_index():
    """route → 英文原文相对路径（靠 md5 反查），并顺带记录原文里所有路由。

    返回 (route_to_rel: dict, md5_to_rel: dict)
    """
    md5_to_rel = {}
    route_to_rel = {}
    if not DOCS_REPO_DIR.exists():
        return route_to_rel, md5_to_rel
    for p in sorted(DOCS_REPO_DIR.rglob("*.md")):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        md5 = hashlib.md5(txt.encode("utf-8")).hexdigest()
        rel = str(p.relative_to(DOCS_REPO_DIR)).replace("\\", "/")
        md5_to_rel[md5] = rel
        meta, _ = split_frontmatter(txt)
        if meta.get("route"):
            route_to_rel[meta["route"]] = rel
    return route_to_rel, md5_to_rel


# --------------------------------------------------------------------------- #
# 内容规整：把 mkdocs 特有写法转成网页 markdown 能渲染的形状
# --------------------------------------------------------------------------- #
ADMONITION_EMOJI = {
    "note": "📝", "info": "ℹ️", "tip": "💡", "hint": "💡", "important": "❗",
    "warning": "⚠️", "caution": "⚠️", "danger": "🚫", "error": "⛔", "bug": "🐞",
    "example": "🧪", "quote": "❝", "abstract": "📌", "success": "✅",
    "question": "❓", "failure": "❌", "attention": "⚠️",
}


def _admonition_icon(kind: str) -> str:
    return ADMONITION_EMOJI.get(kind.lower(), "📌")


# ⚠️ 这个正则是踩了两次坑才对的，注释别删：
#   官方文档里的写法**极不固定**，三种都真实存在：
#     `!!! warning "标题"`（标准）、`!!!warning 免责声明`（无空格、标题无引号）、`!!! 已停止`（无类型）；
#   收尾就是**单独一行** `!!!` 或 `:::`。
#   第一版写成 `\s+` 要求空格 → 418 处一条都没转；
#   第二版 `\s*` + 类型可选 → 收尾行 `!!!` 自己也被当成了「开始标记」，
#   于是正文被塞进空块里，行尾还多出个 "Note"。所以现在**必须要求「类型或标题至少有一个」**。
_ADMONITION_OPEN_RE = re.compile(
    r"^(?P<fence>!!!|\?\?\?\+?)\s*(?P<kind>[A-Za-z][\w-]*)?(?:\s+\"(?P<title>[^\"]*)\")?(?:\s+(?P<inline>\S.*))?\s*$"
)
_ADMONITION_CLOSE_RE = re.compile(r"^(!!!|:::)\s*$")
_HEADING_RE = re.compile(r"^#{1,6}\s")
_FENCE_RE = re.compile(r"^(```|~~~)")


def convert_admonitions(body: str) -> str:
    """`!!!warning "标题"` …（收尾 `!!!`/`:::`）→ markdown 引用块。

    不能直接留原文：`!!!` 在网页 markdown 里就是几个感叹号，正文语义全丢。
    支持两种内容排布：
      · 缩进式（mkdocs 规范写法）—— 内容 4 空格缩进；
      · 无缩进式（官方文档里更常见）—— 从标记行一直吃到收尾行。
    """
    lines = body.split("\n")
    out: list[str] = []
    i = 0
    stats = {"blocks": 0, "unclosed": 0, "stray": 0}

    while i < len(lines):
        raw_line = lines[i]
        m = _ADMONITION_OPEN_RE.match(raw_line.strip())
        kind = (m.group("kind") or "") if m else ""
        title = ((m.group("title") or "").strip() if m else "") or ((m.group("inline") or "").strip() if m else "")
        if not m or not (kind or title):
            # 单独一行的裸 `!!!`：不是开标记（没有类型也没有标题）——当残留标记收掉
            if raw_line.strip() in ("!!!", ":::"):
                out.append(f"> **{_admonition_icon('note')} 提示**")
                stats["stray"] += 1
            else:
                out.append(raw_line)
            i += 1
            continue

        i += 1
        block: list[str] = []
        closed = False
        indented = bool(lines[i].startswith(("    ", "\t"))) if i < len(lines) else False
        while i < len(lines):
            cur = lines[i]
            if _ADMONITION_CLOSE_RE.match(cur.strip()):
                closed = True
                i += 1
                break
            if indented:
                if cur.strip() == "":
                    block.append("")
                    i += 1
                    continue
                if cur.startswith("    "):
                    block.append(cur[4:])
                    i += 1
                    continue
                if cur.startswith("\t"):
                    block.append(cur[1:])
                    i += 1
                    continue
                break
            if cur.strip() == "":
                # 空行后若还是普通段落（非标题/非新标记/非代码块围栏），视为同一提示块的续行
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                ns = nxt.strip()
                if ns and not _HEADING_RE.match(ns) and not _ADMONITION_CLOSE_RE.match(ns) \
                        and not _ADMONITION_OPEN_RE.match(ns) and not _FENCE_RE.match(ns):
                    block.append("")
                    i += 1
                    continue
                i += 1
                break
            block.append(cur)
            i += 1
        while block and block[-1] == "":
            block.pop()
        if not closed:
            stats["unclosed"] += 1
        head = f"{_admonition_icon(kind or 'note')} {title or (kind or 'note').capitalize()}"
        out.append(f"> **{head}**")
        out.append(">")
        for b in block:
            out.append(f"> {b}".rstrip())
        out.append("")
        stats["blocks"] += 1
    return "\n".join(out)


def convert_callouts(body: str) -> str:
    """`:::callout` / `:::warning` … `:::` 容器 → 引用块（内部 markdown 保留）。"""
    lines = body.split("\n")
    out, stack = [], None
    for line in lines:
        m = re.match(r"^:::+\s*([\w-]*)\s*$", line.strip())
        if m:
            if stack is None:
                stack = m.group(1) or "callout"
                if stack and stack.lower() != "callout":
                    out.append(f"> **{_admonition_icon(stack)} {stack.capitalize()}**")
                    out.append(">")
            else:
                stack = None
                out.append("")
            continue
        out.append(f"> {line}".rstrip() if stack else line)
    return "\n".join(out)


def convert_tabs(body: str) -> str:
    """`=== "标题"` 标签页 → 小标题（不引入交互，先把内容摊平可见）。"""
    lines = body.split("\n")
    out, in_tab = [], False
    for line in lines:
        m = re.match(r"^===\s+\"([^\"]+)\"\s*$", line.strip())
        if m:
            if in_tab:
                out.append("")
            out.append(f"**{m.group(1)}**")
            out.append("")
            in_tab = True
            continue
        out.append(line[4:] if in_tab and line.startswith("    ") else line)
    return "\n".join(out)


_LINK_RE = re.compile(r"(?P<bang>!?)\[(?P<text>[^\]]+)\]\((?P<target>[^()\s]*(?:\([^()\s]*\)[^()\s]*)*)\)")
# 只统计图片（方括号前有 `!`），用于"图片数不许掉"的防回归计数
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^()\s]*(?:\([^()\s]*\)[^()\s]*)*\)")


def demote_unknown_links(body: str, known_routes: set, asset_paths: set) -> tuple[str, list[str]]:
    """正文里指向**本站没有的页面**的站内链接 → 降级成纯文本（保留文字，去掉链接）。

    为什么必须做：译文里有些链接指向"译文有、本地原文仓没有"的页面
    （如 `/extensions/translation/`，本地 clone 还停在旧 commit）。
    留着就是一个**点了肯定 404 的链接**；抹掉正文又丢信息 —— 所以留字去链。
    这是生成器的**硬不变量**：产物里不该有指向未知路由的站内链接。

    ⚠️ 两个必须守住的点（都踩过）：
      1. **图片 `![alt](src)` 不是链接，绝不能降级** —— 早期版本用"链接 + 未知目标"直接匹配，
         把图片也命中，改写成 `![alt]` 之后又跟后面某个 `(...)` 拼成怪链接，
         一次吃掉 88 张图里的 84 张（而"站内链接全可达"那类断言照样全绿）。
         所以先排除紧跟在 `!` 后面的方括号。
      2. **外部链接（http/https、mailto、#锚点）原样保留** —— 它们不是本站路由。
    """
    demoted: list[str] = []

    def repl(m):
        if m.group("bang"):            # 图片：原样保留
            return m.group(0)
        text, target = m.group("text"), m.group("target")
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            return m.group(0)          # 外链 / 页内锚点
        bare = target.split("#", 1)[0]
        if bare in known_routes or (bare + "/") in known_routes or bare in asset_paths:
            return m.group(0)
        demoted.append(target)
        return text                    # 留字去链

    new = _LINK_RE.sub(repl, body)
    return new, demoted


def rewrite_links(body: str, rel_path: str, path_to_route: dict) -> tuple[str, list[str]]:
    """把指向别的 .md 的相对链接改写成站内路由；返回 (新正文, 未解析链接列表)。

    ⚠️ 链接正则是踩过坑的：**URL 里可以有括号**——`/installation/android-(termux)/`
    就是官方文档里真实存在的路由。第一版用 `[^)\s]+` 收尾，遇到这种链接会**在第一个
    `)` 处截断**，把好好的站内链接切成 `/installation/android-(termux`，于是变成死链。
    现在专门允许一层配对括号。

    另外官方文档里**存在省略 `.md` 的链接**（`[反向代理](../Administration/reverse-proxying)`），
    所以匹配不到时补一次 `.md` 再查 —— 这类链接同样是站内跳转，不该被当成死链降级掉。
    """
    base = Path(rel_path).parent
    unresolved: list[str] = []

    def repl(m):
        if m.group("bang"):
            return m.group(0)   # `![alt](src)` 是图片，不是链接
        text, target = m.group("text"), m.group("target")
        if re.match(r"^[a-z][a-z0-9+.-]*://", target) or target.startswith("#") or target.startswith("mailto:"):
            return m.group(0)
        anchor = ""
        if "#" in target:
            target, anchor = target.split("#", 1)
            anchor = "#" + anchor
        if not target.lower().endswith(".md"):
            # 站内链接可能省扩展名（`../Administration/reverse-proxying`），
            # 也可能是"目录式"链接（`/Installation/Updating` → `Installation/Updating/index.md`），
            # 还有大小写不统一的（官方文档自己不统一）。逐个兜底，都不中才当资源放过。
            #
            # ⚠️ 根相对的 target（以 `/` 开头）**不能再和 base 拼**：pathlib 会把它当相对路径，
            #    拼出 `/usage/Installation/Updating/index.md` 这种四不像，于是这条永远匹配不上。
            if target.startswith("/"):
                bases = [Path(".")]
            else:
                bases = [base]
            found = None
            for b in bases:
                for cand in (target + ".md", target + "/index.md"):
                    try:
                        probe = (b / cand.lstrip("/")).as_posix()
                    except Exception:
                        continue
                    if probe in path_to_route:
                        found = path_to_route[probe]
                        break
                    lowered = probe.lower()
                    hit = next((r for p, r in path_to_route.items() if p.lower() == lowered), None)
                    if hit:
                        found = hit
                        break
                if found:
                    break
            if found:
                return f"[{text}]({found}{anchor})"
            # 根相对且以 / 结尾：可能直接就是一个路由
            if target.startswith("/"):
                routes = set(path_to_route.values())
                for cand in (target, target.rstrip("/") + "/"):
                    if cand in routes:
                        return f"[{text}]({cand}{anchor})"
            return m.group(0)  # 图片等资源：交给前端按原路径请求 /api/docs/asset
        try:
            resolved = (base / target).as_posix()
        except Exception:
            resolved = target
        # 规范化 ../ 与 ./
        parts: list[str] = []
        for seg in resolved.split("/"):
            if seg in ("", "."):
                continue
            if seg == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(seg)
        norm = "/".join(parts)
        route = path_to_route.get(norm)
        if not route:
            for candidate, r in path_to_route.items():
                if candidate.lower() == norm.lower():
                    route = r
                    break
        if route:
            return f"[{text}]({route}{anchor})"
        unresolved.append(f"{rel_path} -> {target}")
        return m.group(0)

    new = _LINK_RE.sub(repl, body)
    return new, unresolved


# --------------------------------------------------------------------------- #
# 主体
# --------------------------------------------------------------------------- #
def load_translations():
    if not TRANSLATION_CACHE_PATH.exists():
        raise SystemExit(f"找不到翻译缓存：{TRANSLATION_CACHE_PATH}")
    data = json.loads(TRANSLATION_CACHE_PATH.read_text(encoding="utf-8"))
    translations = data.get("translations") or {}
    return data.get("__commit__"), translations


def build_pages(translations: dict, md5_to_rel: dict):
    """译文 → {route: page}，并统计被剔除的条目。

    ⚠️ **译文存在 ≠ 收录**：缓存里保留着一些**本地原文仓还没有文件**的条目
    （上游/我方后续才加、而本地 clone 还停在旧 commit，如 `/extensions/translation/`、
    `/extensions/objective/`）。正文就绪、路由却查无此文件 —— 收进来就是死链与"点开空白"。
    判据用 md5 → 原文文件 的映射（读不到原文 = 不收），**不看 route 在不在**。
    """
    pages: dict[str, dict] = {}
    skipped = {"redirect": [], "hidden": [], "probe": [], "no_route": [], "empty": [], "no_source": []}
    for key, raw in translations.items():
        if _PROBE_RE.search(raw) or _PROBE_RE.search(raw[:400]):
            skipped["probe"].append(key[:8])
            continue
        meta, body = split_frontmatter(raw)
        if meta.get("redirect"):
            skipped["redirect"].append(meta["redirect"])
            continue
        if (meta.get("visibility") or "").lower() == "hidden":
            skipped["hidden"].append(key[:8])
            continue
        route = meta.get("route")
        if not route:
            skipped["no_route"].append(key[:8])
            continue
        if _JUNK_ROUTE_RE.match(route) or _JUNK_TITLE_RE.search(raw[:600]):
            skipped["probe"].append(route)
            continue
        if not body.strip():
            skipped["empty"].append(route)
            continue
        rel = md5_to_rel.get(key, "")
        if not rel:
            # 译文在、原文不在本地仓 —— 见函数 docstring，不收
            skipped["no_source"].append(route)
            continue
        # 标题优先级：title → label → 正文第一个 H1 → 路由兜底。
        # ⚠️ 官方文档**大多用 `label:`**（mkdocs-material 的写法，如「VPN 和隧道」「额外功能」），
        #    只认 title 会让这些页面在导航树里直接显示成一条路由。
        title = meta.get("title") or meta.get("label") or first_heading(body) or route
        pages[route] = {
            "route": route,
            "title": title,
            "icon": meta.get("icon") or "",
            "order": int(meta["order"]) if str(meta.get("order", "")).lstrip("-").isdigit() else None,
            "body": body,
            "source_rel": rel,
        }
    return pages, skipped


def build_tree(pages: dict):
    """按 route 层级建树，缺的中间层补「合成索引页」。"""
    nodes: dict[str, dict] = {}

    def ensure(route: str) -> dict:
        if route not in nodes:
            nodes[route] = {
                "route": route,
                "title": None,
                "icon": "",
                "order": None,
                "synthetic": True,
                "children": [],
            }
        return nodes[route]

    ensure("/")
    for route, page in pages.items():
        parts = [p for p in route.strip("/").split("/") if p]
        cur = "/"
        for idx in range(len(parts)):
            child_route = "/" + "/".join(parts[: idx + 1]) + "/"
            child = ensure(child_route)
            parent = ensure(cur)
            if child_route not in [c["route"] for c in parent["children"]]:
                parent["children"].append(child)
            cur = child_route
        node = nodes[route]
        node.update(
            title=page["title"], icon=page["icon"], order=page["order"],
            synthetic=False, source_rel=page["source_rel"],
        )

    # 排序：先按官方 order（升序，未标 order 的排在标了的后面），再按标题
    def sort_key(n):
        o = n["order"]
        return (0 if o is not None else 1, o if o is not None else 0, n["title"] or n["route"])

    def walk(n):
        n["children"].sort(key=sort_key)
        for c in n["children"]:
            walk(c)

    root = nodes["/"]
    root["title"] = ROOT_TITLE
    root["icon"] = "book"
    walk(root)
    return root, nodes


def render_synthetic_index(node: dict) -> str:
    """合成索引页正文：只列子页，链接用站内路由（不引用 .md）。"""
    lines = [f"# {node['title']}", ""]
    lines.append(f"本节共 {len(node['children'])} 个页面：")
    lines.append("")
    for c in node["children"]:
        note = "" if not c.get("synthetic") else "（小节）"
        lines.append(f"- [{c['title']}]({c['route']}){note}")
    return "\n".join(lines) + "\n"


def render_root_index(root: dict) -> str:
    lines = [f"# {ROOT_TITLE}", ""]
    lines.append("本页是 SillyTavern 官方文档的**全量中文译文**，左侧目录按官方结构组织。")
    lines.append("")
    lines.append("原始英文文档：<https://github.com/SillyTavern/SillyTavern-Docs>（译文随上游更新）。")
    lines.append("")
    for c in root["children"]:
        lines.append(f"## [{c['title']}]({c['route']})")
        leaves = c["children"]
        if leaves:
            lines.append("")
            for l in leaves:
                lines.append(f"- [{l['title']}]({l['route']})")
        lines.append("")
    return "\n".join(lines)


def serialize_tree(node: dict, route_has_page: set) -> dict:
    return {
        "route": node["route"],
        "title": node["title"],
        "icon": node["icon"] or "",
        "hasPage": node["route"] in route_has_page,
        "children": [serialize_tree(c, route_has_page) for c in node["children"]],
    }


def fingerprint(translations: dict) -> str:
    h = hashlib.sha256()
    for k in sorted(translations):
        h.update(k.encode())
        h.update(str(len(translations[k])).encode())
    return h.hexdigest()[:16]


def generate(force: bool = False, check_only: bool = False) -> dict:
    commit, translations = load_translations()
    route_to_rel, md5_to_rel = build_route_index()
    path_to_route = {rel: r for r, rel in route_to_rel.items()}
    fp = fingerprint(translations)
    # 原始译文里的图片总数（未被任何处理碰过）—— 与产物对比即可发现"图片被误伤"
    image_count_in_cache = sum(len(_IMAGE_RE.findall(v)) for v in translations.values())

    manifest_path = OUT_DIR / MANIFEST_NAME
    if manifest_path.exists():
        try:
            old = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            old = {}
        if not force and old.get("fingerprint") == fp and old.get("commit") == commit:
            if check_only:
                return {"status": "up-to-date", **{k: old.get(k) for k in ("commit", "pages", "fingerprint")}}
            return {"status": "skipped", **{k: old.get(k) for k in ("commit", "pages", "fingerprint")}}

    if check_only:
        return {"status": "stale", "commit": commit, "fingerprint": fp}

    pages, skipped = build_pages(translations, md5_to_rel)

    # 链接改写（放在建树前，正文先规整）
    unresolved: list[str] = []
    demoted_all: list[str] = []
    known_routes = set(pages.keys())
    # 文档内引用的静态资源（图片/字体）也算"本站有"：链接到它们不该被降级。
    # 由官方原文仓真实存在的文件枚举而来 —— 不靠猜后缀。
    asset_paths: set[str] = set()
    if DOCS_REPO_DIR.exists():
        for f in DOCS_REPO_DIR.rglob("*"):
            if f.is_file() and f.suffix.lower() in ASSET_SUFFIXES:
                asset_paths.add("/" + f.relative_to(DOCS_REPO_DIR).as_posix())
    for route, page in pages.items():
        body = page["body"]
        body = convert_admonitions(body)
        body = convert_callouts(body)
        body = convert_tabs(body)
        rel = page["source_rel"] or route_to_rel.get(route, "")
        body, miss = rewrite_links(body, rel, path_to_route)
        unresolved.extend(miss)
        # 再扫一遍：指向本站没有的页面 → 降级成纯文本（保证产物零内链死链）
        body, demoted = demote_unknown_links(body, known_routes, asset_paths)
        demoted_all.extend(f"{route} -> {t}" for t in demoted)
        page["body"] = body

    root, nodes = build_tree(pages)

    # 落盘：先清空旧产物（保证被删的页面不会残留在导航树外）
    if OUT_DIR.exists():
        for p in sorted(OUT_DIR.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    route_has_page = set(pages.keys())
    written = 0
    image_count_in_output = 0
    for route, node in nodes.items():
        if node.get("synthetic"):
            body = render_root_index(node) if route == "/" else render_synthetic_index(node)
        else:
            body = pages[route]["body"]
        rel_out = route_to_relpath(route)
        target = OUT_DIR / rel_out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        # 图片计数是**防回归的关键指标**：链接改写/降级那类改动一旦误伤图片，
        # 这里立刻掉数（上一版就吃过 88 → 4 的亏，而当时的断言全绿）。
        image_count_in_output += len(_IMAGE_RE.findall(body))
        written += 1

    flat = []
    def collect(n):
        flat.append({
            "route": n["route"],
            "title": n["title"],
            "path": route_to_relpath(n["route"]).as_posix(),
            "hasPage": n["route"] in route_has_page,
            "synthetic": bool(n.get("synthetic")),
            "sourceRel": n.get("source_rel") or "",
        })
        for c in n["children"]:
            collect(c)

    collect(root)

    manifest = {
        "commit": commit,
        "fingerprint": fp,
        "generatedFrom": str(TRANSLATION_CACHE_PATH),
        "rootTitle": ROOT_TITLE,
        "pages": written,
        "articles": len(pages),
        "images": image_count_in_output,
        "imagesInCache": image_count_in_cache,
        "tree": serialize_tree(root, route_has_page),
        "flat": flat,
        "skipped": skipped,
        "unresolvedLinks": unresolved,
        "demotedLinks": demoted_all,
        "assetSuffixes": list(ASSET_SUFFIXES),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return {
        "status": "generated",
        "commit": commit,
        "fingerprint": fp,
        "pages": written,
        "articles": len(pages),
        "synthetic": written - len(pages),
        "skipped": {k: len(v) for k, v in skipped.items()},
        "unresolved": len(unresolved),
        "demoted": len(demoted_all),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="还原官方文档中文树")
    ap.add_argument("--force", action="store_true", help="忽略指纹，强制重建")
    ap.add_argument("--check", action="store_true", help="只检查产物是否最新")
    args = ap.parse_args(argv)

    result = generate(force=args.force, check_only=args.check)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.check and result.get("status") == "stale":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
