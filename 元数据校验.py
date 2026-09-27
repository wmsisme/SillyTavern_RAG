"""
RAG metadata 体检脚本

2026-09-27 改动：
- 原来每个 source 只抽样 10 条（README 已知问题 7），现在**全量校验**（分页拉取，不省略）；
- 原来只查白名单里的两个 source，`source` 是文档相对路径之类的记录永远看不见，
  现在先统计**全库 source 分布**并标出"计划外"的取值；
- 逐条打印改成汇总打印（1945 条全打印没法看），问题条目才逐条列出。
"""
import os
import sys
from collections import Counter
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import chromadb  # noqa: E402

ROOT_DIR = Path(r"d:\code_item\酒馆rag")
CHROMA_DIR = ROOT_DIR / "RAG" / "chroma_db"
COLLECTION_NAME = "sillytavern_docs"

# 需要逐条校验字段的 source（全量，不抽样）
REQUIRED_SOURCES = ["translated_official_docs", "supplement"]

# 已知/合法的 source 前缀 —— 其余取值会被标成"计划外"
KNOWN_SOURCE_PREFIXES = (
    "translated_official_docs", "supplement", "loop_supplement", "st_docs",
    "learn-regex", "mastering-regex", "bm25_match",
)

BATCH = 500
PREVIEW_PER_SOURCE = 3

print("=" * 60)
print("  RAG metadata 验证脚本（全量）")
print("=" * 60)

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
try:
    collection = client.get_collection(COLLECTION_NAME)
except Exception as e:
    print(f"获取集合失败: {e}")
    sys.exit(1)

try:
    total = collection.count()
except Exception as e:
    print(f"count() 失败(HNSW索引可能不兼容): {e}")
    total = 0
print(f"集合: {COLLECTION_NAME} | 总文档数: {total}")


def fetch_all(where=None):
    """分页把符合条件的记录全部取出来（不再抽样）。"""
    out = {"ids": [], "metadatas": [], "documents": []}
    offset = 0
    while True:
        kwargs = dict(limit=BATCH, offset=offset, include=["metadatas", "documents"])
        if where:
            kwargs["where"] = where
        try:
            r = collection.get(**kwargs)
        except Exception as e:
            print(f"  [跳过] 查询失败: {e}")
            return out
        ids = r.get("ids") or []
        if not ids:
            break
        out["ids"].extend(ids)
        out["metadatas"].extend(r.get("metadatas") or [])
        out["documents"].extend(r.get("documents") or [])
        if len(ids) < BATCH:
            break
        offset += BATCH
    return out


all_pass = True

# ---------- 1. 全库 source 分布 ----------
print(f"\n{'=' * 60}")
print("  全库 source 分布（顺带暴露计划外的取值）")
print(f"{'=' * 60}")

every = fetch_all()
print(f"  实际取回 {len(every['ids'])} 条（集合 count = {total}）"
      + ("" if len(every["ids"]) == total else "  ⚠ 与 count() 不一致"))

def src_prefix(s: str) -> str:
    for p in ("learn-regex", "mastering-regex"):
        if s.startswith(p):
            return p + "_*"
    return s or "(空)"

dist = Counter(src_prefix(m.get("source", "")) for m in every["metadatas"])
for src, n in dist.most_common():
    unexpected = "" if any(src.startswith(p) or src == p for p in KNOWN_SOURCE_PREFIXES) else "  ⚠ 计划外"
    print(f"  {n:>6}  {src}{unexpected}")

bad_src = [s for s in dist if not any(s.startswith(p) or s == p for p in KNOWN_SOURCE_PREFIXES)]
if bad_src:
    all_pass = False
    print(f"  ❌ 出现计划外的 source 取值: {bad_src}")

# ---------- 2. 逐条字段校验（全量） ----------
for src_filter in REQUIRED_SOURCES:
    print(f"\n{'=' * 60}")
    print(f"  检查 source='{src_filter}'（全量）")
    print(f"{'=' * 60}")

    data = fetch_all(where={"source": src_filter})
    count = len(data["ids"])
    print(f"  记录数: {count}")
    if count == 0:
        print(f"  [信息] 暂无 source='{src_filter}' 记录")
        continue

    errors = []
    previews = 0
    for i, mid in enumerate(data["ids"]):
        m = data["metadatas"][i] or {}
        doc = data["documents"][i] if i < len(data["documents"]) else ""
        checks = []

        if m.get("source", "") != src_filter:
            checks.append(f"❌ source不匹配: 实际='{m.get('source')}', 期望='{src_filter}'")

        if src_filter == "translated_official_docs":
            if not m.get("module"):
                checks.append("❌ 缺少module字段")
            if m.get("language") != "zh":
                checks.append(f"⚠ language='{m.get('language')}', 期望='zh'")
        elif src_filter == "supplement":
            if not m.get("module"):
                checks.append("❌ 缺少module字段")
            if m.get("source") == "loop_supplement":
                checks.append("❌ 严禁使用 'loop_supplement'，必须为 'supplement'")

        if checks:
            errors.append((mid, checks))
        elif previews < PREVIEW_PER_SOURCE:
            previews += 1
            preview = doc[:80].replace("\n", " ") if doc else ""
            print(f"  ✅ id={mid[:55]} module={m.get('module', '?')[:50]} lang={m.get('language', '?')}")
            if preview:
                print(f"     preview: {preview}...")

    if errors:
        all_pass = False
        print(f"\n  ⚠ 发现 {len(errors)} 条 metadata 问题（共校验 {count} 条）:")
        for mid, errs in errors[:50]:
            print(f"    id={mid[:55]}")
            for e in errs:
                print(f"      {e}")
        if len(errors) > 50:
            print(f"    …另有 {len(errors) - 50} 条")
    else:
        print(f"  ✅ {count} 条全部通过")

print(f"\n{'=' * 60}")
if all_pass:
    print("  ✅ 所有 metadata 验证通过（全量）")
else:
    print("  ❌ 存在 metadata 问题，请修复后重新运行")
print("=" * 60)
sys.exit(0 if all_pass else 1)
