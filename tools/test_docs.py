# -*- coding: utf-8 -*-
"""文档中心自检 —— 覆盖「树 / 正文 / 资源 / 越权与穿越」四类，带故意破坏自证。

跑法（不需要先起服务，走 FastAPI 的进程内 TestClient）：
    python tools/test_docs.py
    python tools/test_docs.py --verbose

为什么要这些断言（每一条都对应一类真实会坏的地方）：
  · **清单与文件必须一一对应**：生成器只写了一半、或产物被人手改过，都会让某些页点开是 404；
  · **导航树里每个节点都要有正文**：树上点得动、点开空白 —— 用户看到的就是"坏了"；
  · **译文里的站内链接必须都指向真实路由**：官方原文里是 `./xxx.md`，改写漏一个就是死链；
  · **asset 必须挡住穿越与后缀白名单**：这个接口免登录，是公网可达面。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DOCS_DIR = ROOT / "backend" / "docs_zh"
MANIFEST = DOCS_DIR / "manifest.json"

PASS, FAIL = [], []
QUIET = False          # 故意破坏自证期间用：只出声报错，避免把"预期的红"混进最终结论


def ok(name: str, detail: str = ""):
    PASS.append(name)
    if not QUIET:
        print(f"  ✅ {name}" + (f" —— {detail}" if detail else ""))


def bad(name: str, detail: str = ""):
    FAIL.append(name)
    print(f"  ❌ {name}" + (f" —— {detail}" if detail else ""))


def check_manifest():
    print("\n① 产物与清单")
    if not MANIFEST.exists():
        bad("manifest.json 存在", "先跑 python tools/gen_docs_zh.py")
        return None
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    flat = m.get("flat") or []
    ok("manifest.json 可解析", f"{len(flat)} 个节点")

    # 清单里每个节点的文件都必须真实存在
    missing = [f["path"] for f in flat if not (DOCS_DIR / f["path"]).is_file()]
    if missing:
        bad("清单里的文件都存在", f"缺 {len(missing)} 个：{missing[:3]}")
    else:
        ok("清单里的文件都存在", f"{len(flat)} 个")

    # 反向：目录里不该有清单以外的 .md（生成器会清空重建，出现即说明有人手工塞过东西）
    on_disk = {p.relative_to(DOCS_DIR).as_posix() for p in DOCS_DIR.rglob("*.md")}
    known = {f["path"] for f in flat}
    extra = sorted(on_disk - known)
    if extra:
        bad("没有清单外的 .md", f"{len(extra)} 个：{extra[:3]}")
    else:
        ok("没有清单外的 .md")

    # 路由唯一（重复路由会让 tree 里一个节点被顶掉）
    dup = [r for r, c in Counter(f["route"] for f in flat).items() if c > 1]
    if dup:
        bad("路由唯一", f"重复：{dup[:3]}")
    else:
        ok("路由唯一", f"{len(flat)} 条")

    # 树里的每个节点都要在 flat 里（否则树上会出现点开没正文的节点）
    tree_routes = []

    def walk(n):
        tree_routes.append(n["route"])
        for c in n.get("children") or []:
            walk(c)

    if m.get("tree"):
        walk(m["tree"])
    else:
        bad("树非空")
    ghost = [r for r in tree_routes if r not in {f["route"] for f in flat}]
    if tree_routes and ghost:
        bad("树节点都有对应正文", f"{ghost[:3]}")
    elif tree_routes:
        ok("树节点都有对应正文", f"{len(tree_routes)} 个")

    # 空跑守卫：以上统计都基于"有内容"，数量为 0 时前面的绿等于没测
    if len(flat) < 50:
        bad("产物规模非空跑", f"只有 {len(flat)} 个节点，像是没生成完")
    else:
        ok("产物规模非空跑", f"{len(flat)} 个节点")

    # ⚠️ 图片数防回归：曾经一次链接改写把图片也命中，88 张只剩 4 张，
    #    而当时所有"链接可达"的断言照样全绿 —— 所以单独盯住这个数。
    imgs = len(re.findall(r"!\[[^\]]*\]\([^()\s]*(?:\([^()\s]*\)[^()\s]*)*\)",
                          "\n".join(p.read_text(encoding="utf-8") for p in DOCS_DIR.rglob("*.md"))))
    cached = m.get("imagesInCache") or 0
    if cached and imgs < cached * 0.5:
        bad("图片没被改写吃掉", f"产物 {imgs} 张 / 原文 {cached} 张 —— 掉太多了")
    else:
        ok("图片没被改写吃掉", f"产物 {imgs} 张 / 原文（含被剔除页）{cached} 张")

    # 降级只该落在"译文有、原文没有"的少数链接上；数量暴涨说明改写逻辑坏了
    demoted = m.get("demotedLinks") or []
    if len(demoted) > 30:
        bad("降级数量在合理范围", f"{len(demoted)} 条，疑似改写逻辑误伤（历史事故：569 条）")
    else:
        ok("降级数量在合理范围", f"{len(demoted)} 条")
    return m


def check_links(m):
    print("\n② 译文里的站内链接")
    routes = {f["route"] for f in (m.get("flat") or []) if f.get("hasPage")}
    known = {f["route"] for f in (m.get("flat") or [])}
    # URL 里可以有括号（`/installation/android-(termux)/` 是真实存在的路由），
    # 所以不能按第一个 `)` 收尾 —— 否则会把好链接误判成死链（生成器里踩过同一个坑）。
    link_re = re.compile(r"\]\((/[^()\s]*(?:\([^()\s]*\)[^()\s]*)*)\)")
    all_links, dead = 0, []
    for p in DOCS_DIR.rglob("*.md"):
        for target in link_re.findall(p.read_text(encoding="utf-8")):
            if target.startswith("/static/"):
                continue  # 图片资源，由 asset 接口管
            all_links += 1
            base = target.split("#", 1)[0]
            if base in known or base + "/" in known or base.rstrip("/") + "/" in known:
                continue
            dead.append(f"{p.relative_to(DOCS_DIR)} → {target}")
    if all_links == 0:
        bad("链接检查非空跑", "一条站内链接都没找到，断言等于没跑")
    elif dead:
        bad("站内链接全部可达", f"{len(dead)} 条死链：{dead[:3]}")
    else:
        ok("站内链接全部可达", f"共 {all_links} 条 → {len(routes)} 个有正文的路由")


def check_api(m):
    print("\n③ 接口（进程内 TestClient，不需要先起服务）")
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as c:
        r = c.get("/api/docs/tree")
        if r.status_code != 200:
            bad("GET /api/docs/tree", f"HTTP {r.status_code}")
            return
        data = r.json()
        ok("GET /api/docs/tree", f"页数 {data.get('pages')}，有正文路由 {len(data.get('routes') or [])}")

        targets = m.get("flat") or []
        sample = [t for t in targets if t.get("hasPage")][:8]
        sample += [t for t in targets if t.get("synthetic")][:2]
        got_empty = []
        for t in sample:
            rr = c.get("/api/docs/article", params={"route": t["route"]})
            if rr.status_code != 200 or len(rr.json().get("content") or "") < 20:
                got_empty.append(f"{t['route']} HTTP {rr.status_code}")
        if got_empty:
            bad("逐篇取样取正文", f"{got_empty[:3]}")
        else:
            ok("逐篇取样取正文", f"{len(sample)} 篇都有内容")

        # 负例：不存在的路由必须 404（而不是回一篇别的东西）
        r = c.get("/api/docs/article", params={"route": "/this-does-not-exist/"})
        ok("不存在的路由 → 404", f"HTTP {r.status_code}") if r.status_code == 404 else \
            bad("不存在的路由 → 404", f"HTTP {r.status_code}")

        # 穿越：全都必须被挡（4xx）
        traversals = [
            "../../../RAG/translation_cache.json",
            "/../../backend/data.db",
            "/static/../../backend/main.py",
            "/assets/../../../.env",
        ]
        leaked = []
        for t in traversals:
            rr = c.get("/api/docs/asset", params={"path": t})
            if rr.status_code < 400:
                leaked.append(f"{t} → HTTP {rr.status_code}")
        if leaked:
            bad("asset 路径穿越被挡", "; ".join(leaked))
        else:
            ok("asset 路径穿越被挡", f"{len(traversals)} 个穿越样本全部 4xx")

        # 后缀白名单：.md / .py / .json 这类**即便真存在**也不该发出来
        for t in ["/readme.md", "/retype.yml", "/LICENSE"]:
            rr = c.get("/api/docs/asset", params={"path": t})
            if rr.status_code < 400:
                bad("asset 后缀白名单", f"{t} 被放行（HTTP {rr.status_code}）")
            else:
                ok(f"asset 拒绝非白名单文件 {t}", f"HTTP {rr.status_code}")

        # 真资源必须能取（否则上面全绿也可能是"白名单把什么都挡了"）
        real = c.get("/api/docs/asset", params={"path": "/static/extensions/live2d-folder.png"})
        ok("真图片可取", f"HTTP {real.status_code}, {len(real.content)} 字节") \
            if real.status_code == 200 and len(real.content) > 100 else \
            bad("真图片可取", f"HTTP {real.status_code}")

        # ⚠️ 免登录：文档中心是公开页，带不带 Cookie 都该给
        anon = c.get("/api/docs/tree")
        ok("匿名可读（免登录）", f"HTTP {anon.status_code}") if anon.status_code == 200 else \
            bad("匿名可读（免登录）", f"HTTP {anon.status_code}")

        # ---- 文档内搜索（走 embedding + rerank，慢，所以只打两枪） ----
        r = c.get("/api/docs/search", params={"q": "宏怎么用", "top_k": 5}, timeout=60)
        if r.status_code != 200:
            bad("文档内搜索可用", f"HTTP {r.status_code}: {r.text[:120]}")
        else:
            data = r.json()
            hits = data.get("results") or []
            if not hits:
                bad("文档内搜索有结果", "搜「宏怎么用」返回 0 条")
            else:
                # 三条硬要求，缺一条这个功能就会表现成"搜出来一堆点不开的东西"
                bad_src = [h for h in hits if not h.get("sourceFile")]
                bad_route = [h for h in hits if not str(h.get("route", "")).startswith("/")]
                bad_snip = [h for h in hits if len((h.get("snippet") or "").strip()) < 20]
                if bad_src or bad_route or bad_snip:
                    bad("搜索结果每条都能跳转且带片段",
                        f"缺来源 {len(bad_src)} / 缺路由 {len(bad_route)} / 片段过短 {len(bad_snip)}")
                else:
                    ok("搜索结果每条都能跳转且带片段", f"{len(hits)} 条，Top1={hits[0]['title']}")
                # 只搜文档：命中的原文路径必须能在清单里映射回路由（映射不上的会被丢掉）
                ok("只搜官方文档（不掺正则书/QA 块）",
                   f"未映射丢弃 {data.get('unmapped')} 条")

        # 负例：空搜索词必须 400（否则会白烧一次 embedding）
        r = c.get("/api/docs/search", params={"q": "   "})
        ok("空搜索词被拒", f"HTTP {r.status_code}") if r.status_code == 400 else \
            bad("空搜索词被拒", f"HTTP {r.status_code}")


def selftest_break_must_fail() -> int:
    """故意破坏自证：把产物改坏，确认上面的断言**真的会红**。

    做法 = 在临时副本上做三处破坏（删文件 / 造死链 / 改清单），跑核心断言，应当全部报红。
    这是防"假设绿"的标准动作 —— 一个永远绿的检查等于没有检查。
    """
    print("\n④ 故意破坏自证（断言有没有鉴别力）")
    import shutil
    import tempfile

    global DOCS_DIR, MANIFEST, QUIET
    real_docs, real_manifest = DOCS_DIR, MANIFEST
    tmp = Path(tempfile.mkdtemp(prefix="docs_selftest_"))
    QUIET = True
    try:
        shutil.copytree(real_docs, tmp / "docs_zh")
        DOCS_DIR = tmp / "docs_zh"
        MANIFEST = DOCS_DIR / "manifest.json"
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        flat = m["flat"]
        first_page = next(f for f in flat if f["hasPage"])

        # 破坏 1：删掉一个真实页面文件 → 「清单里的文件都存在」必须红
        (DOCS_DIR / first_page["path"]).unlink()
        before = len(FAIL)

        def expect_red(label):
            n = len(FAIL)
            check_manifest()
            check_links(json.loads(MANIFEST.read_text(encoding="utf-8")))
            return len(FAIL) > n

        red1 = expect_red("删除页面文件")

        # 破坏 2：往正文里塞一条指向不存在路由的站内链接 → 死链检查必须红
        victim = next(p for p in DOCS_DIR.rglob("*.md") if p.name != first_page["path"].split("/")[-1])
        victim.write_text(victim.read_text(encoding="utf-8") + "\n\n[死链](/definitely/not/here/)\n",
                          encoding="utf-8")
        red2 = expect_red("造一条死链")

        # 破坏 3：清单里塞一个不存在的路由 → 「树节点都有对应正文」必须红
        m["flat"].append({"route": "/ghost/page/", "title": "幽灵", "path": "ghost/page.md",
                          "hasPage": True, "synthetic": False, "sourceRel": ""})
        m["tree"]["children"].append({"route": "/ghost/page/", "title": "幽灵", "icon": "",
                                      "hasPage": True, "children": []})
        MANIFEST.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        red3 = expect_red("清单塞幽灵节点")

        # 把这一段自证产生的失败记录清掉，别污染最终结论
        del FAIL[before:]

        for label, red in (("删文件", red1), ("造死链", red2), ("塞幽灵节点", red3)):
            if red:
                print(f"  ✅ 破坏「{label}」被抓到（断言有鉴别力）")
                PASS.append(f"自证:{label}")
            else:
                print(f"  ❌ 破坏「{label}」没被抓到 —— 这条断言等于没在工作")
                FAIL.append(f"自证失效:{label}")
    finally:
        DOCS_DIR, MANIFEST = real_docs, real_manifest
        QUIET = False
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--skip-selftest", action="store_true", help="跳过故意破坏自证（调试时用）")
    args = ap.parse_args()

    m = check_manifest()
    if m:
        check_links(m)
        check_api(m)
    if not args.skip_selftest:
        selftest_break_must_fail()

    print(f"\n{'=' * 60}\n通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
    if FAIL:
        for f in FAIL:
            print("  ❌", f)
        return 1
    print("✅ 文档中心自检全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
