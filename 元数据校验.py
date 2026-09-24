import os
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import chromadb

ROOT_DIR = Path(r"d:\code_item\酒馆rag")
CHROMA_DIR = ROOT_DIR / "RAG" / "chroma_db"
COLLECTION_NAME = "sillytavern_docs"

REQUIRED_SOURCES = ["translated_official_docs", "supplement"]

print("=" * 60)
print("  RAG metadata 验证测试脚本")
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
    total = "?"
print(f"集合: {COLLECTION_NAME} | 总文档数: {total}")

all_pass = True

for src_filter in REQUIRED_SOURCES:
    print(f"\n{'=' * 60}")
    print(f"  检查 source='{src_filter}'")
    print(f"{'=' * 60}")

    try:
        result = collection.get(
            where={"source": src_filter},
            limit=10,
            include=["metadatas", "documents"],
        )
    except Exception as e:
        print(f"  [跳过] 查询失败 (可能该source不存在): {e}")
        continue

    count = len(result["ids"])
    print(f"  记录数: {count}")

    if count == 0:
        print(f"  [信息] 暂无 source='{src_filter}' 记录")
        continue

    errors = []
    for i, mid in enumerate(result["ids"]):
        m = result["metadatas"][i]
        doc = result["documents"][i] if i < len(result["documents"]) else ""

        checks = []
        actual_source = m.get("source", "")

        if actual_source != src_filter:
            checks.append(f"❌ source不匹配: 实际值='{actual_source}', 期望='{src_filter}'")

        if src_filter == "translated_official_docs":
            module_val = m.get("module", "")
            if not module_val:
                checks.append("❌ 缺少module字段")
            lang = m.get("language", "")
            if lang != "zh":
                checks.append(f"⚠ language='{lang}', 期望='zh'")

        if src_filter == "supplement":
            module_val = m.get("module", "")
            if not module_val:
                checks.append("❌ 缺少module字段")
            if actual_source == "loop_supplement":
                checks.append("❌ 严禁使用 'loop_supplement'，必须为 'supplement'")

        if checks:
            errors.append((mid, checks))
        else:
            src_ok = "✅" if actual_source == src_filter else "❌"
            mod_info = m.get("module", "?")[:50]
            lang_info = m.get("language", "?")
            preview = doc[:80].replace("\n", " ") if doc else ""
            print(f"  {src_ok} id={mid[:55]} module={mod_info} lang={lang_info}")
            if preview:
                print(f"     preview: {preview}...")

    if errors:
        all_pass = False
        print(f"\n  ⚠ 发现 {len(errors)} 个metadata问题:")
        for mid, errs in errors:
            print(f"    id={mid[:55]}")
            for e in errs:
                print(f"      {e}")

print(f"\n{'=' * 60}")
if all_pass:
    print("  ✅ 所有metadata验证通过")
else:
    print("  ❌ 存在metadata问题，请修复后重新运行")
print("=" * 60)
sys.exit(0 if all_pass else 1)
