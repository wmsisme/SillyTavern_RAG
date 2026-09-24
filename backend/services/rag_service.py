import os
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

os.environ.setdefault("HF_ENDPOINT", os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch
import numpy as np
from transformers import AutoModel, AutoTokenizer
import jieba
import chromadb
from openai import OpenAI

from backend.config import (
    CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL_NAME,
    RERANKER_MODEL_NAME, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
    DOCS_REPO_DIR, TRANSLATION_CACHE_PATH, REGEX_README_PATH,
    REGEX_CHUNKS_DIR, VECTOR_CACHE_PATH, VECTOR_CACHE_META_PATH,
)

EMBED_DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
TOP_K_RETRIEVAL = 40
TOP_K_FINAL = 5

_embedder = None
_reranker = None
_collection = None
_bm25 = None
_corpus = None
_hash_to_meta = None
_deepseek_client = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME, local_files_only=True)
        model = AutoModel.from_pretrained(EMBEDDING_MODEL_NAME, local_files_only=True).to(EMBED_DEVICE)
        model.eval()
        _embedder = (tokenizer, model, EMBED_DEVICE)
    return _embedder


def _get_reranker():
    return False


_g_client = None


def _save_vector_cache(ids, documents, metadatas, embeddings):
    """把整库内容落盘成向量缓存，供下次启动跳过 BGE 向量化。"""
    try:
        import json as _json
        import numpy as _np

        VECTOR_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _np.savez(
            str(VECTOR_CACHE_PATH),
            # 文本必须用 object dtype：numpy 默认的定长字符串按最长条目分配固定宽度，
            # 1798 个 chunk 会撑到 500MB+（实测 565MB，改后约 7MB）。
            ids=_np.array(ids, dtype=object),
            documents=_np.array(documents, dtype=object),
            embeddings=_np.asarray(embeddings, dtype=_np.float32),
        )
        with open(VECTOR_CACHE_META_PATH, "w", encoding="utf-8") as f:
            _json.dump({"count": len(ids), "metadatas": metadatas}, f, ensure_ascii=False)
        print(f"  向量缓存已写入: {VECTOR_CACHE_PATH.name} ({len(ids)} 条)")
    except Exception as e:
        print(f"  向量缓存写入失败（不影响本次运行）: {str(e)[:80]}")


def _load_vector_cache():
    """读取向量缓存；缺失、损坏或条目数不一致时返回 None。"""
    if not (VECTOR_CACHE_PATH.exists() and VECTOR_CACHE_META_PATH.exists()):
        return None
    try:
        import json as _json
        import numpy as _np

        with open(VECTOR_CACHE_META_PATH, "r", encoding="utf-8") as f:
            meta = _json.load(f)
        data = _np.load(str(VECTOR_CACHE_PATH), allow_pickle=True)
        ids = [str(x) for x in data["ids"].tolist()]
        documents = [str(x) for x in data["documents"].tolist()]
        embeddings = data["embeddings"]
        metadatas = meta.get("metadatas") or []

        if not (len(ids) == len(documents) == len(embeddings) == len(metadatas)):
            print("  向量缓存条目数不一致，改走全量重建")
            return None
        if meta.get("count") != len(ids):
            print("  向量缓存计数不符，改走全量重建")
            return None
        return {"ids": ids, "documents": documents,
                "embeddings": embeddings, "metadatas": metadatas}
    except Exception as e:
        print(f"  向量缓存读取失败，改走全量重建: {str(e)[:80]}")
        return None


def _restore_from_cache(client) -> bool:
    """把缓存灌回集合；成功 True，失败则由调用方回退到全量重建。"""
    cache = _load_vector_cache()
    if not cache:
        return False
    ids = cache["ids"]
    documents = cache["documents"]
    embeddings = cache["embeddings"].tolist()
    metadatas = cache["metadatas"]
    try:
        collection = client.get_collection(COLLECTION_NAME)
        BATCH = 256
        for i in range(0, len(ids), BATCH):
            collection.add(
                ids=ids[i:i + BATCH],
                documents=documents[i:i + BATCH],
                embeddings=embeddings[i:i + BATCH],
                metadatas=metadatas[i:i + BATCH],
            )
        print(f"  已从向量缓存恢复 {collection.count()} 条（跳过向量化）")
        return True
    except Exception as e:
        print(f"  向量缓存恢复失败，回退到全量重建: {str(e)[:80]}")
        return False


def _get_collection():
    global _collection, _g_client
    if _collection is None:
        _g_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        needs_rebuild = False
        try:
            _collection = _g_client.get_collection(COLLECTION_NAME)
            if _collection.count() == 0:
                needs_rebuild = True
            else:
                dummy_emb = [0.0] * 1024
                _collection.query(query_embeddings=[dummy_emb], n_results=1)
        except Exception:
            needs_rebuild = True

        if needs_rebuild:
            print("ChromaDB 索引不可用，优先尝试向量缓存...")
            try:
                _g_client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
            _g_client.create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

            if not _restore_from_cache(_g_client):
                # 缓存缺失或灌回失败：清空后走完整重建（翻译走缓存、重新切片向量化）
                try:
                    _g_client.delete_collection(COLLECTION_NAME)
                except Exception:
                    pass
                _g_client.create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
                _rebuild_index_inline(_g_client)

            _collection = _g_client.get_collection(COLLECTION_NAME)
            print(f"ChromaDB 索引就绪: {_collection.count()} 条记录")
    return _collection


def _get_deepseek():
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _deepseek_client


def _encode_batch(texts: List[str]) -> List[List[float]]:
    tokenizer, model, device = _get_embedder()
    inputs = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
        emb = outputs.last_hidden_state[:, 0]
        emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb.cpu().numpy().tolist()


def _encode_query(query: str) -> List[float]:
    return _encode_batch([query])[0]


def _build_bm25():
    global _bm25, _corpus, _hash_to_meta
    if _bm25 is not None:
        return
    _bm25 = False
    _corpus = []
    _hash_to_meta = {}


def _bm25_search(query: str, top_k: int) -> List[Tuple[str, float]]:
    return []


def search(query: str, top_k: int = TOP_K_FINAL) -> List[dict]:
    collection = _get_collection()
    embedder = _get_embedder()
    reranker = _get_reranker()
    _build_bm25()

    qe = _encode_query(query)
    raw = collection.query(query_embeddings=[qe], n_results=TOP_K_RETRIEVAL,
                          include=["documents", "metadatas", "distances"])
    vec_docs = raw["documents"][0]
    vec_metas = raw["metadatas"][0]

    seen_hashes = set()
    docs = []
    metas = []

    for d, m in zip(vec_docs, vec_metas):
        h = hashlib.md5(d.encode()).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            docs.append(d)
            metas.append(m)

    bm25_results = _bm25_search(query, TOP_K_RETRIEVAL)
    for bm25_doc, _bm25_score in bm25_results:
        h = hashlib.md5(bm25_doc.encode()).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            docs.append(bm25_doc)
            original_meta = _hash_to_meta.get(h, {"source": "bm25_match", "language": "zh"})
            metas.append(original_meta)

    if len(docs) <= top_k:
        results = []
        for d, m in zip(docs, metas):
            results.append({"content": d[:500], "source": m.get("source", "unknown"), "score": 1.0})
        return results

    pairs = [(query, d[:1500]) for d in docs]
    if reranker and reranker is not False:
        try:
            scores = reranker.compute_score(pairs)
        except Exception:
            scores = list(range(len(docs), 0, -1))
    else:
        scores = list(range(len(docs), 0, -1))
    scored = sorted(zip(docs, metas, scores), key=lambda x: -x[2])

    results = []
    for d, m, s in scored[:top_k]:
        results.append({
            "content": d[:500],
            "source": m.get("source", "unknown"),
            "module": m.get("module", m.get("source_file", "")),
            "score": round(float(s), 3),
        })
    return results


def _expand_chunk_context(metas: List[Dict], expand_radius: int = 2) -> List[str]:
    collection = _get_collection()
    expanded = {}
    source_cache = {}

    for meta in metas:
        source_file = meta.get("source_file", meta.get("module", ""))
        chunk_index = meta.get("chunk_index", None)
        if not source_file or chunk_index is None:
            continue

        if source_file not in source_cache:
            try:
                neighbors = collection.get(
                    where={"source_file": source_file},
                    include=["documents", "metadatas"],
                    limit=99999
                )
                if neighbors and neighbors.get("ids"):
                    sorted_items = sorted(
                        zip(neighbors["metadatas"], neighbors["documents"]),
                        key=lambda x: x[0].get("chunk_index", 0)
                    )
                    source_cache[source_file] = {
                        "metas": [m for m, _ in sorted_items],
                        "docs": [d for _, d in sorted_items],
                        "total": len(sorted_items)
                    }
                else:
                    source_cache[source_file] = None
            except Exception:
                source_cache[source_file] = None
                continue

        sc = source_cache.get(source_file)
        if not sc:
            continue

        start = max(0, chunk_index - expand_radius)
        end = min(sc["total"], chunk_index + expand_radius + 1)

        for ci in range(start, end):
            doc = sc["docs"][ci]
            actual_ci = sc["metas"][ci].get("chunk_index", ci)
            rkey = f"{source_file}::{actual_ci}"
            if doc and rkey not in expanded:
                expanded[rkey] = doc

    return [expanded[k] for k in sorted(expanded.keys())]


def _retrieve_raw(query: str) -> Tuple[List[str], List[Dict], List[float]]:
    collection = _get_collection()
    embedder = _get_embedder()
    reranker = _get_reranker()
    _build_bm25()

    qe = _encode_query(query)
    raw = collection.query(query_embeddings=[qe], n_results=TOP_K_RETRIEVAL,
                          include=["documents", "metadatas", "distances"])
    vec_docs = raw["documents"][0]
    vec_metas = raw["metadatas"][0]

    seen_hashes = set()
    docs = []
    metas = []

    for d, m in zip(vec_docs, vec_metas):
        h = hashlib.md5(d.encode()).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            docs.append(d)
            metas.append(m)

    bm25_results = _bm25_search(query, TOP_K_RETRIEVAL)
    for bm25_doc, _bm25_score in bm25_results:
        h = hashlib.md5(bm25_doc.encode()).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            docs.append(bm25_doc)
            original_meta = _hash_to_meta.get(h, {"source": "bm25_match", "language": "zh"})
            metas.append(original_meta)

    if len(docs) <= TOP_K_FINAL:
        return docs, metas, [1.0] * len(docs)

    pairs = [(query, d[:1500]) for d in docs]
    if reranker and reranker is not False:
        try:
            scores = reranker.compute_score(pairs)
        except Exception:
            scores = list(range(len(docs), 0, -1))
    else:
        scores = list(range(len(docs), 0, -1))
    scored = sorted(zip(docs, metas, scores), key=lambda x: -x[2])

    return (
        [s[0] for s in scored[:TOP_K_FINAL]],
        [s[1] for s in scored[:TOP_K_FINAL]],
        [float(s[2]) for s in scored[:TOP_K_FINAL]],
    )


def ask(query: str, max_doc_chars: int = 8000) -> dict:
    docs, metas, scores = _retrieve_raw(query)

    all_docs = list(docs)
    if metas:
        try:
            ctx_docs = _expand_chunk_context(metas, expand_radius=2)
            seen = {hashlib.md5(d.encode()).hexdigest() for d in all_docs}
            for cd in ctx_docs:
                h = hashlib.md5(cd.encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    all_docs.append(cd)
        except Exception:
            pass

    merged = []
    total_chars = 0
    for d in all_docs:
        chunk_len = len(d)
        if total_chars + chunk_len > max_doc_chars:
            remaining = max_doc_chars - total_chars
            if remaining > 200:
                merged.append(d[:remaining])
            break
        merged.append(d)
        total_chars += chunk_len

    docs_text = "\n---\n".join(merged)

    prompt = (
        "根据以下检索到的SillyTavern知识库文档，简练回答用户问题。"
        "严格只使用文档中已有的信息，不要编造。如果文档信息不足以回答问题，请明确说明。\n\n"
        f"问题: {query}\n\n"
        f"检索文档:\n{docs_text}\n\n"
        "回答:"
    )

    try:
        client = _get_deepseek()
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
        )
        answer = resp.choices[0].message.content.strip()
    except Exception as e:
        answer = f"[生成失败: {str(e)[:80]}]"

    sources = []
    for m in metas:
        sources.append({
            "source": m.get("source", "unknown"),
            "module": m.get("module", m.get("source_file", "")),
            "language": m.get("language", "unknown"),
        })

    return {"answer": answer, "sources": sources}


def ask_stream(query: str, max_doc_chars: int = 8000):
    docs, metas, scores = _retrieve_raw(query)

    all_docs = list(docs)
    if metas:
        try:
            ctx_docs = _expand_chunk_context(metas, expand_radius=2)
            seen = {hashlib.md5(d.encode()).hexdigest() for d in all_docs}
            for cd in ctx_docs:
                h = hashlib.md5(cd.encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    all_docs.append(cd)
        except Exception:
            pass

    merged = []
    total_chars = 0
    for d in all_docs:
        chunk_len = len(d)
        if total_chars + chunk_len > max_doc_chars:
            remaining = max_doc_chars - total_chars
            if remaining > 200:
                merged.append(d[:remaining])
            break
        merged.append(d)
        total_chars += chunk_len

    docs_text = "\n---\n".join(merged)

    prompt = (
        "根据以下检索到的SillyTavern知识库文档，简练回答用户问题。"
        "严格只使用文档中已有的信息，不要编造。如果文档信息不足以回答问题，请明确说明。\n\n"
        f"问题: {query}\n\n"
        f"检索文档:\n{docs_text}\n\n"
        "回答:"
    )

    try:
        client = _get_deepseek()
        stream = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"[生成失败: {str(e)[:80]}]"


def reload_index():
    global _collection, _bm25, _corpus, _hash_to_meta
    _collection = None
    _bm25 = None
    _corpus = None
    _hash_to_meta = None
    _get_collection()
    _build_bm25()


def _rebuild_index_inline(chromadb_client):
    import json as _json
    import time as _time
    from langchain_core.documents import Document as _Document

    EXCLUDE_PATTERNS = ["_includes", ".github", "node_modules", "static"]

    st_docs_raw = []
    if DOCS_REPO_DIR.exists():
        for f in DOCS_REPO_DIR.rglob("*.md"):
            rel = str(f.relative_to(DOCS_REPO_DIR))
            if any(p in rel.split(os.sep) for p in EXCLUDE_PATTERNS):
                continue
            if f.name in ("LICENSE", "LicenseCredits.md", "readme.md"):
                continue
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    content = fp.read()
                if not content.strip():
                    continue
                st_docs_raw.append((content, {
                    "file_name": f.name, "module": rel.replace("\\", "/"),
                    "language": "en", "category": "sillytavern",
                }))
            except Exception:
                pass
    print(f"  英文文档: {len(st_docs_raw)} 篇")

    cache = {}
    if TRANSLATION_CACHE_PATH.exists():
        try:
            with open(TRANSLATION_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = _json.load(f)
        except Exception:
            pass
    if not isinstance(cache, dict):
        cache = {"__commit__": "", "translations": {}}
    translations = cache.get("translations", cache if "__commit__" not in cache else cache.get("translations", {}))

    ds_client = _get_deepseek()
    translated_docs = []
    cached_count = 0
    new_count = 0

    for i, (content, meta) in enumerate(st_docs_raw):
        cache_key = hashlib.md5(content.encode()).hexdigest()
        if cache_key in translations:
            meta["language"] = "zh"
            meta["source"] = "translated_official_docs"
            translated_docs.append(_Document(page_content=translations[cache_key], metadata=meta))
            cached_count += 1
            continue
        if (i + 1) % 10 == 0:
            print(f"  翻译: {i + 1}/{len(st_docs_raw)} (缓存:{cached_count} 新:{new_count})")
        try:
            prompt = f"把下面的英文技术文档翻译成中文。要求：准确翻译技术术语，保留Markdown格式、代码块、表格结构。\n\n{content}"
            resp = ds_client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=8192,
            )
            zh = resp.choices[0].message.content.strip()
            if zh and len(zh) > 10:
                translations[cache_key] = zh
                meta["language"] = "zh"
                meta["source"] = "translated_official_docs"
                translated_docs.append(_Document(page_content=zh, metadata=meta))
                new_count += 1
            else:
                meta["language"] = "en"
                translated_docs.append(_Document(page_content=content, metadata=meta))
        except Exception as e:
            print(f"  翻译失败: {meta['module']} - {str(e)[:60]}")
            meta["language"] = "en"
            translated_docs.append(_Document(page_content=content, metadata=meta))
        _time.sleep(0.3)

    TRANSLATION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRANSLATION_CACHE_PATH, "w", encoding="utf-8") as f:
        _json.dump({"__commit__": "inline", "translations": translations}, f, ensure_ascii=False, indent=2)

    print(f"  翻译完成: 缓存 {cached_count} | 新翻译 {new_count}")

    st_chunks = []
    for doc in translated_docs:
        content = doc.page_content
        meta = doc.metadata
        source_module = meta.get("module", "")
        lines = content.split("\n")
        raw_chunks = []
        cur_lines = []
        for line in lines:
            if re.match(r'^#{1,3}\s', line) and cur_lines and len("".join(cur_lines).strip()) >= 50:
                raw_chunks.append("\n".join(cur_lines))
                cur_lines = [line]
            else:
                cur_lines.append(line)
        if cur_lines and len("".join(cur_lines).strip()) >= 20:
            raw_chunks.append("\n".join(cur_lines))

        for body in raw_chunks:
            if len(body) <= 2000:
                ch_meta = dict(meta)
                ch_meta["chunk_hash"] = hashlib.md5(body.encode()).hexdigest()
                ch_meta["chunk_index"] = len(st_chunks)
                ch_meta["source_file"] = source_module
                st_chunks.append(_Document(page_content=body.strip(), metadata=ch_meta))
            else:
                paragraphs = re.split(r'\n\s*\n', body)
                sub_cur = []
                for para in paragraphs:
                    if sub_cur and len("\n\n".join(sub_cur)) + len(para) > 1800:
                        sub_body = "\n\n".join(sub_cur).strip()
                        if len(sub_body) >= 20:
                            ch_meta = dict(meta)
                            ch_meta["chunk_hash"] = hashlib.md5(sub_body.encode()).hexdigest()
                            ch_meta["chunk_index"] = len(st_chunks)
                            ch_meta["source_file"] = source_module
                            st_chunks.append(_Document(page_content=sub_body, metadata=ch_meta))
                        sub_cur = [para]
                    else:
                        sub_cur.append(para)
                if sub_cur:
                    sub_body = "\n\n".join(sub_cur).strip()
                    if len(sub_body) >= 20:
                        ch_meta = dict(meta)
                        ch_meta["chunk_hash"] = hashlib.md5(sub_body.encode()).hexdigest()
                        ch_meta["chunk_index"] = len(st_chunks)
                        ch_meta["source_file"] = source_module
                        st_chunks.append(_Document(page_content=sub_body, metadata=ch_meta))

    if REGEX_README_PATH.exists():
        with open(REGEX_README_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
        blocks = re.split(r"\n(?=## )", raw)
        for block in blocks:
            block = block.strip()
            if not block or len(block) < 50:
                continue
            header = block.split("\n")[0].lstrip("#").strip()
            h = hashlib.md5(block.encode()).hexdigest()[:8]
            safe = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', header[:40])
            st_chunks.append(_Document(page_content=block, metadata={
                "source": f"learn-regex_{safe}_{h}",
                "type": "syntax", "language": "zh", "topic": header, "category": "regex",
                "chunk_hash": hashlib.md5(block.encode()).hexdigest(),
            }))

    if REGEX_CHUNKS_DIR.exists():
        for f in sorted(REGEX_CHUNKS_DIR.rglob("*.txt")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    text = fp.read().strip()
                if not text:
                    continue
                topic = str(f.relative_to(REGEX_CHUNKS_DIR)).replace("\\", "/").split("/")[0]
                h = hashlib.md5(text.encode()).hexdigest()[:8]
                safe = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', topic[:40])
                st_chunks.append(_Document(page_content=text, metadata={
                    "source": f"mastering-regex_{safe}_{h}",
                    "type": "principle", "language": "zh", "topic": topic, "category": "regex",
                    "chunk_hash": hashlib.md5(text.encode()).hexdigest(),
                }))
            except Exception:
                pass

    print(f"  总 chunk: {len(st_chunks)} | 向量化中...")

    collection = chromadb_client.get_collection(COLLECTION_NAME)
    BATCH = 32
    cache_ids, cache_docs, cache_metas, cache_embs = [], [], [], []
    for bi in range(0, len(st_chunks), BATCH):
        batch = st_chunks[bi:bi + BATCH]
        texts = [c.page_content for c in batch]
        metas = [c.metadata for c in batch]
        ids = []
        for c in batch:
            raw_id = f"{c.metadata.get('source','')}|{c.metadata.get('chunk_hash','')}"
            ids.append(hashlib.md5(raw_id.encode()).hexdigest())
        emb_list = _encode_batch(texts)
        collection.add(embeddings=emb_list, documents=texts, metadatas=metas, ids=ids)
        cache_ids.extend(ids)
        cache_docs.extend(texts)
        cache_metas.extend(metas)
        cache_embs.extend(emb_list)
        if (bi // BATCH) % 10 == 0:
            print(f"  向量化: {min(bi + BATCH, len(st_chunks))}/{len(st_chunks)}")

    print(f"  内联重建完成: {collection.count()} 条")
    _save_vector_cache(cache_ids, cache_docs, cache_metas, cache_embs)
