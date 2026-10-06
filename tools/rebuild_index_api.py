#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用硅基流动的向量模型重算整库，写进**新集合**（老集合原封不动，可随时切回）。

为什么必须重建：本机 `RAG/bge-large-zh` 与 API 的 `BAAI/bge-m3`（或 bge-large-zh-v1.5）
实测**不是同一个向量空间**（同文本余弦仅 0.56–0.63）。换了模型不重算，
检索会"不报错但静默变差"——这种故障最难发现，所以宁可多花几分钟重算一遍。

用法：
    python tools/rebuild_index_api.py --dry-run   # 只算 20 条，验证通路/维度/耗时
    python tools/rebuild_index_api.py             # 全量重建（支持断点续传）
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np            # noqa: E402
import chromadb               # noqa: E402

from backend.config import (  # noqa: E402
    CHROMA_DIR, COLLECTION_NAME, SOURCE_COLLECTION_NAME, EMBED_PROVIDER,
    SILICONFLOW_API_KEY, SILICONFLOW_EMBED_MODEL,
    VECTOR_CACHE_PATH, VECTOR_CACHE_META_PATH, RAG_DIR,
)
from backend.services.rag_service import _encode_batch_api  # noqa: E402

CHECKPOINT = RAG_DIR / f"rebuild_{EMBED_PROVIDER}_partial.npz"
BATCH = 16


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只算前 20 条")
    ap.add_argument("--source", default=SOURCE_COLLECTION_NAME)
    ap.add_argument("--target", default=COLLECTION_NAME)
    args = ap.parse_args()

    if EMBED_PROVIDER == "local":
        print("❌ 当前 EMBED_PROVIDER=local，没什么可重建的（本机模型就是 local 那条路）")
        return 2
    if not SILICONFLOW_API_KEY:
        print("❌ .env 里没有 SILICONFLOW_API_KEY")
        return 2

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        src = client.get_collection(args.source)
    except Exception as e:
        print(f"❌ 读不到源集合 {args.source}: {e}")
        return 2

    data = src.get(include=["documents", "metadatas"])
    ids = list(data["ids"])
    docs = list(data["documents"] or [])
    metas = list(data["metadatas"] or [])
    print(f"源集合 {args.source}：{len(ids)} 条")
    print(f"目标集合 {args.target}（用 {SILICONFLOW_EMBED_MODEL}，provider={EMBED_PROVIDER}）")
    if not ids:
        print("❌ 源集合是空的")
        return 2
    if len(ids) != len(docs) or len(ids) != len(metas):
        print(f"❌ 源集合数据不齐：ids={len(ids)} docs={len(docs)} metas={len(metas)}")
        return 2

    if args.dry_run:
        t0 = time.time()
        vecs = _encode_batch_api(docs[:20])
        dt = time.time() - t0
        print(f"✅ 干跑 20 条：{dt:.1f}s（{dt/20:.2f}s/条），维度 {len(vecs[0])}")
        print(f"   按此推算全量 {len(ids)} 条约需 {dt/20*len(ids)/60:.1f} 分钟")
        return 0

    # ---- 断点续传：把已算好的向量落盘，中断了接着跑，不白烧 ----
    done = 0
    emb_list: list = []
    if CHECKPOINT.exists():
        try:
            with np.load(str(CHECKPOINT), allow_pickle=True) as ck:
                if int(ck["count"]) <= len(ids) and str(ck["model"]) == SILICONFLOW_EMBED_MODEL:
                    done = int(ck["count"])
                    emb_list = list(ck["embeddings"])
                    print(f"发现断点：已算 {done}/{len(ids)} 条，从第 {done+1} 条继续")
        except Exception as e:
            print(f"断点文件不可用（忽略，从头算）: {e}")

    t0 = time.time()
    for i in range(done, len(ids), BATCH):
        part = docs[i:i + BATCH]
        try:
            emb_list.extend(_encode_batch_api(part))
        except Exception as e:
            print(f"\n❌ 第 {i} 条起失败：{e}")
            np.savez(str(CHECKPOINT), count=len(emb_list),
                     embeddings=np.asarray(emb_list, dtype=np.float32),
                     model=SILICONFLOW_EMBED_MODEL)
            print(f"已保存断点（{len(emb_list)} 条），修好后重跑本脚本即可接着算")
            return 1
        n = i + len(part)
        if (i // BATCH) % 10 == 0 or n == len(ids):
            elapsed = time.time() - t0
            speed = (n - done) / elapsed if elapsed else 0
            eta = (len(ids) - n) / speed / 60 if speed else 0
            print(f"  {n}/{len(ids)}  已用 {elapsed/60:.1f} 分钟，预计还要 {eta:.1f} 分钟", flush=True)
        if (i // BATCH) % 10 == 9:
            np.savez(str(CHECKPOINT), count=len(emb_list),
                     embeddings=np.asarray(emb_list, dtype=np.float32),
                     model=SILICONFLOW_EMBED_MODEL)

    emb = np.asarray(emb_list, dtype=np.float32)
    if emb.shape[0] != len(ids):
        print(f"❌ 向量条数对不上：{emb.shape[0]} vs {len(ids)}")
        return 1
    print(f"向量算完：{emb.shape}（{time.time()-t0:.0f}s）")

    # ---- 写入目标集合 ----
    try:
        client.delete_collection(args.target)
        print(f"（已删除同名旧集合 {args.target}，准备重建）")
    except Exception:
        pass
    col = client.create_collection(name=args.target, metadata={"hnsw:space": "cosine"})
    W = 256
    for i in range(0, len(ids), W):
        col.add(ids=ids[i:i + W], documents=docs[i:i + W],
                embeddings=emb.tolist()[i:i + W], metadatas=metas[i:i + W])
    print(f"✅ 目标集合已写入：{col.count()} 条")

    # ---- 同步向量缓存（否则下次启动会以为索引坏了，用老缓存灌回错的向量）----
    np.savez(str(VECTOR_CACHE_PATH), ids=np.array(ids, dtype=object),
             documents=np.array(docs, dtype=object), embeddings=emb)
    import json
    VECTOR_CACHE_META_PATH.write_text(
        json.dumps({"count": len(ids), "metadatas": metas}, ensure_ascii=False),
        encoding="utf-8")
    print(f"✅ 向量缓存已同步：{VECTOR_CACHE_PATH.name}")

    if CHECKPOINT.exists():
        try:
            CHECKPOINT.unlink()
            print("（断点文件已清理）")
        except OSError as e:
            print(f"（断点文件暂时删不掉：{e}；它是纯产物，下次运行会覆盖，可手动删）")
    print("\n下一步：在 .env 里设 EMBED_PROVIDER=siliconflow 并重启后端。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
