import os
import sys
import re
import json
import time
import hashlib
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch
import numpy as np
from transformers import AutoModel, AutoTokenizer
from openai import OpenAI
import chromadb
from langchain_core.documents import Document

ROOT_DIR = Path(r"d:\code_item\酒馆rag")
RAG_DIR = ROOT_DIR / "RAG"
CHROMA_DIR = RAG_DIR / "chroma_db"
COLLECTION_NAME = "sillytavern_docs"
DOCS_SOURCE_DIR = RAG_DIR / "SillyTavern-Docs"
TRANSLATION_CACHE_PATH = RAG_DIR / "translation_cache.json"
REGEX_CHUNKS_DIR = RAG_DIR / "正则表达式" / "rag_chunks"
REGEX_README_PATH = RAG_DIR / "README.md"

EMBEDDING_MODEL_NAME = "BAAI/bge-large-zh-v1.5"

# 密钥只从 .env / 环境变量读取，源码里不留明文（.env 已在 .gitignore 中）。
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
if not DEEPSEEK_API_KEY:
    print("[警告] 未找到 DEEPSEEK_API_KEY —— 请在项目根目录 .env 中填写（模板见 .env.example），"
          "或设为环境变量。翻译功能将不可用。")

EMBED_DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
EXCLUDE_PATTERNS = ["_includes", ".github", "node_modules", "static"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def encode_batch(texts, tokenizer, model, device):
    inputs = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
        emb = outputs.last_hidden_state[:, 0]
        emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb.cpu().numpy().tolist()


def rebuild_index():
    log("=" * 60)
    log("  ChromaDB 索引重建脚本")
    log("=" * 60)

    log("加载翻译缓存...")
    cache = {}
    if TRANSLATION_CACHE_PATH.exists():
        try:
            with open(TRANSLATION_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            pass
    if not isinstance(cache, dict):
        cache = {"__commit__": "", "translations": {}}
    translations = cache.get("translations", cache if "__commit__" not in cache else cache.get("translations", {}))

    log(f"翻译缓存: {len(translations)} 条")

    log("加载文档...")
    st_docs_raw = []
    if DOCS_SOURCE_DIR.exists():
        for f in DOCS_SOURCE_DIR.rglob("*.md"):
            rel = str(f.relative_to(DOCS_SOURCE_DIR))
            if any(p in rel.split(os.sep) for p in EXCLUDE_PATTERNS):
                continue
            if f.name in ("LICENSE", "LicenseCredits.md", "readme.md"):
                continue
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    content = fp.read()
                if not content.strip():
                    continue
                st_docs_raw.append((content, {"file_name": f.name, "module": rel.replace("\\", "/"),
                                              "language": "en", "category": "sillytavern"}))
            except Exception:
                pass
    log(f"英文文档: {len(st_docs_raw)} 篇")

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    translated_docs = []
    cached_count = 0
    new_count = 0

    for i, (content, meta) in enumerate(st_docs_raw):
        mod = meta["module"]
        cache_key = hashlib.md5(content.encode()).hexdigest()

        if cache_key in translations:
            meta["language"] = "zh"
            meta["source"] = "translated_official_docs"
            translated_docs.append(Document(page_content=translations[cache_key], metadata=meta))
            cached_count += 1
            continue

        if (i + 1) % 10 == 0:
            log(f"  翻译进度: {i + 1}/{len(st_docs_raw)} (缓存: {cached_count}, 新翻译: {new_count})")

        try:
            prompt = f"把下面的英文技术文档翻译成中文。要求：准确翻译技术术语，保留Markdown格式、代码块、表格结构。\n\n{content}"
            resp = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=8192,
            )
            zh = resp.choices[0].message.content.strip()
            if zh and len(zh) > 10:
                translations[cache_key] = zh
                meta["language"] = "zh"
                meta["source"] = "translated_official_docs"
                translated_docs.append(Document(page_content=zh, metadata=meta))
                new_count += 1
            else:
                meta["language"] = "en"
                translated_docs.append(Document(page_content=content, metadata=meta))
        except Exception as e:
            log(f"  翻译失败: {mod} - {str(e)[:60]}")
            meta["language"] = "en"
            translated_docs.append(Document(page_content=content, metadata=meta))
        time.sleep(0.3)

    with open(TRANSLATION_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"__commit__": "rebuild", "translations": translations}, f, ensure_ascii=False, indent=2)

    log(f"翻译完成: 缓存 {cached_count} | 新翻译 {new_count}")

    log("文档切片...")
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

        doc_chunks = []
        for body in raw_chunks:
            if len(body) <= 2000:
                ch_meta = dict(meta)
                ch_meta["chunk_hash"] = hashlib.md5(body.encode()).hexdigest()
                doc_chunks.append(Document(page_content=body.strip(), metadata=ch_meta))
            else:
                paragraphs = re.split(r'\n\s*\n', body)
                sub_cur = []
                for para in paragraphs:
                    if sub_cur and len("\n\n".join(sub_cur)) + len(para) > 1800:
                        sub_body = "\n\n".join(sub_cur).strip()
                        if len(sub_body) >= 20:
                            ch_meta = dict(meta)
                            ch_meta["chunk_hash"] = hashlib.md5(sub_body.encode()).hexdigest()
                            doc_chunks.append(Document(page_content=sub_body, metadata=ch_meta))
                        sub_cur = [para]
                    else:
                        sub_cur.append(para)
                if sub_cur:
                    sub_body = "\n\n".join(sub_cur).strip()
                    if len(sub_body) >= 20:
                        ch_meta = dict(meta)
                        ch_meta["chunk_hash"] = hashlib.md5(sub_body.encode()).hexdigest()
                        doc_chunks.append(Document(page_content=sub_body, metadata=ch_meta))

        for ci, c in enumerate(doc_chunks):
            c.metadata["chunk_index"] = ci
            c.metadata["source_file"] = source_module
        st_chunks.extend(doc_chunks)

    log(f"切片完成: {len(st_chunks)} 个 chunk")

    if REGEX_README_PATH.exists():
        with open(REGEX_README_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
        blocks = re.split(r"\n(?=## )", raw)
        for block in blocks:
            block = block.strip()
            if not block: continue
            header = block.split("\n")[0].lstrip("#").strip()
            if not header or len(block) < 50: continue
            h = hashlib.md5(block.encode()).hexdigest()[:8]
            safe = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', header[:40])
            st_chunks.append(Document(page_content=block, metadata={
                "source": f"learn-regex_{safe}_{h}",
                "type": "syntax", "language": "zh", "topic": header, "category": "regex",
                "chunk_hash": hashlib.md5(block.encode()).hexdigest(),
            }))

    if REGEX_CHUNKS_DIR.exists():
        for f in sorted(REGEX_CHUNKS_DIR.rglob("*.txt")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    text = fp.read().strip()
                if not text: continue
                topic = str(f.relative_to(REGEX_CHUNKS_DIR)).replace("\\", "/").split("/")[0]
                h = hashlib.md5(text.encode()).hexdigest()[:8]
                safe = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', topic[:40])
                st_chunks.append(Document(page_content=text, metadata={
                    "source": f"mastering-regex_{safe}_{h}",
                    "type": "principle", "language": "zh", "topic": topic, "category": "regex",
                    "chunk_hash": hashlib.md5(text.encode()).hexdigest(),
                }))
            except Exception:
                pass

    log(f"总 chunk: {len(st_chunks)} (含正则知识)")

    log("加载嵌入模型...")
    tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME, local_files_only=True)
    model = AutoModel.from_pretrained(EMBEDDING_MODEL_NAME, local_files_only=True).to(EMBED_DEVICE)
    model.eval()

    log("初始化 ChromaDB...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
        log("已删除旧集合")
    except Exception:
        pass
    collection = client.create_collection(name=COLLECTION_NAME)

    log(f"开始向量化 {len(st_chunks)} 个 chunk...")
    BATCH = 32
    for bi in range(0, len(st_chunks), BATCH):
        batch = st_chunks[bi:bi + BATCH]
        texts = [c.page_content for c in batch]
        metas = [c.metadata for c in batch]
        ids = []
        for c in batch:
            raw_id = f"{c.metadata.get('source','')}|{c.metadata.get('file_name','')}|{c.metadata.get('chunk_hash','')}"
            ids.append(hashlib.md5(raw_id.encode()).hexdigest())
        emb_list = encode_batch(texts, tokenizer, model, EMBED_DEVICE)
        collection.add(embeddings=emb_list, documents=texts, metadatas=metas, ids=ids)
        if (bi // BATCH) % 10 == 0:
            log(f"  向量化: {min(bi + BATCH, len(st_chunks))}/{len(st_chunks)}")

    log(f"重建完成! 集合 '{COLLECTION_NAME}' 共 {collection.count()} 条记录")


if __name__ == "__main__":
    rebuild_index()
