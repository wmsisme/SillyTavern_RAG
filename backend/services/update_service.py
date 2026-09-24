import os
import re
import subprocess
import time
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from threading import Lock

from backend.config import (
    DOCS_REPO_DIR, UPSTREAM_URL, UPSTREAM_BRANCH,
    TRANSLATION_CACHE_PATH, REGEX_CHUNKS_DIR, REGEX_README_PATH,
    CHROMA_DIR, COLLECTION_NAME, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
    EMBEDDING_MODEL_NAME,
)
from backend.services.rag_service import reload_index

_UPDATE_LOCK = Lock()
_UPDATE_STATUS = {"running": False, "progress": "", "message": ""}

# check_update() 每次都会真的去 `git fetch upstream`（网络往返数秒），
# 而前端每次打开/刷新页面都会调用它。缓存一段时间，避免刷新页面就卡一下。
CHECK_CACHE_TTL = 600  # 秒
_check_cache = {"at": 0.0, "result": None}

GIT_RETRY_TIMES = 3
GIT_RETRY_DELAY = 10


def get_update_status() -> dict:
    return dict(_UPDATE_STATUS)


def _run_git(cmd: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
    cwd = cwd or DOCS_REPO_DIR
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), timeout=60)


def _retry_git(cmd: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
    last_error = None
    for attempt in range(1, GIT_RETRY_TIMES + 1):
        try:
            return _run_git(cmd, cwd)
        except Exception as e:
            last_error = e
            if attempt < GIT_RETRY_TIMES:
                time.sleep(GIT_RETRY_DELAY)
            else:
                raise
    raise last_error


def get_local_commit() -> str:
    try:
        r = _run_git(["git", "rev-parse", "HEAD"])
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def check_update(force: bool = False) -> dict:
    """检查上游文档是否有更新。

    force=False 时走 10 分钟缓存（前端启动检测用这个）；
    用户在界面上点「立即检查」时传 force=True 强制真的去 fetch。
    """
    now = time.time()
    if not force and _check_cache["result"] is not None and (now - _check_cache["at"]) < CHECK_CACHE_TTL:
        return dict(_check_cache["result"])

    result = _do_check_update()
    _check_cache["at"] = time.time()
    _check_cache["result"] = dict(result)
    return result


def _do_check_update() -> dict:
    if not (DOCS_REPO_DIR / ".git").exists():
        return {"has_update": False, "changed_files": [], "current_commit": "", "upstream_commit": "", "message": "文档仓库未初始化"}

    current = get_local_commit()
    # 注意：不要用 os.chdir()。这是常驻服务进程，改全局工作目录会影响其它模块的
    # 相对路径（后台任务是线程，chdir 是进程级的）。git 命令都显式带 cwd。
    cwd = str(DOCS_REPO_DIR)

    remotes = _run_git(["git", "remote"], cwd).stdout.strip()
    if "upstream" not in remotes:
        _run_git(["git", "remote", "add", "upstream", UPSTREAM_URL], cwd)

    try:
        _retry_git(["git", "fetch", "upstream"], cwd)
    except Exception:
        return {"has_update": False, "changed_files": [], "current_commit": current[:16], "upstream_commit": "", "message": "无法获取上游更新"}

    r = _run_git(["git", "rev-parse", f"upstream/{UPSTREAM_BRANCH}"], cwd)
    upstream = r.stdout.strip()

    has_update = current != upstream
    changed_files = []
    if has_update:
        r = _run_git(["git", "diff", "--name-only", current, upstream], cwd)
        changed_files = [f.strip() for f in r.stdout.strip().split("\n") if f.strip()]

        r_local = _run_git(["git", "merge-base", current, upstream], cwd)
        if r_local.returncode == 0 and r_local.stdout.strip():
            merge_base = r_local.stdout.strip()
            r_changes = _run_git(["git", "diff", "--name-only", merge_base, upstream], cwd)
            changed_files = [f.strip() for f in r_changes.stdout.strip().split("\n") if f.strip()]

    return {
        "has_update": has_update,
        "changed_files": changed_files,
        "current_commit": current[:16],
        "upstream_commit": upstream[:16],
        "message": f"发现 {len(changed_files)} 个文件变更" if has_update else "已是最新版本",
    }


def run_update() -> dict:
    global _UPDATE_STATUS
    if not _UPDATE_LOCK.acquire(blocking=False):
        return {"status": "busy", "message": "更新正在执行中，请稍后再试"}

    try:
        _UPDATE_STATUS = {"running": True, "progress": "开始更新...", "message": ""}

        _UPDATE_STATUS["progress"] = "正在拉取上游文档..."
        # 同样不 chdir：全程显式传 cwd（这是线程里的常驻服务进程）
        cwd = str(DOCS_REPO_DIR)
        _retry_git(["git", "fetch", "upstream"], cwd)

        current = get_local_commit()
        _retry_git(["git", "merge", f"upstream/{UPSTREAM_BRANCH}"], cwd)

        new_current = get_local_commit()
        if current == new_current:
            _UPDATE_STATUS = {"running": False, "progress": "已完成", "message": "无需更新"}
            return {"status": "ok", "message": "已是最新版本", "new_vectors": 0, "deleted_vectors": 0}

        _UPDATE_STATUS["progress"] = f"检测到上游变更，开始处理..."

        EXCLUDE_PATTERNS = ["_includes", ".github", "node_modules", "static"]
        md_files = []
        for f in DOCS_REPO_DIR.rglob("*.md"):
            rel = str(f.relative_to(DOCS_REPO_DIR))
            if any(p in rel.split(os.sep) for p in EXCLUDE_PATTERNS):
                continue
            if f.name in ("LICENSE", "LicenseCredits.md", "readme.md"):
                continue
            md_files.append(f)

        _UPDATE_STATUS["progress"] = f"发现 {len(md_files)} 个文档，开始翻译和索引..."

        import torch
        import numpy as np
        from transformers import AutoModel, AutoTokenizer
        from openai import OpenAI
        from langchain_core.documents import Document
        import chromadb

        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

        cache = {}
        if TRANSLATION_CACHE_PATH.exists():
            try:
                with open(TRANSLATION_CACHE_PATH, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            except Exception:
                pass
        if not isinstance(cache, dict):
            cache = {"__commit__": "", "translations": {}}
        translations = cache.get("translations", cache) if "__commit__" not in cache else cache.get("translations", {})

        all_chunks = []
        for i, md_file in enumerate(md_files):
            if (i + 1) % 20 == 0:
                _UPDATE_STATUS["progress"] = f"翻译进度: {i + 1}/{len(md_files)}"

            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                continue

            content_hash = hashlib.md5(content.encode()).hexdigest()
            rel_path = str(md_file.relative_to(DOCS_REPO_DIR)).replace("\\", "/")

            if content_hash in translations:
                zh_content = translations[content_hash]
            else:
                try:
                    prompt = f"把下面的英文技术文档翻译成中文。要求：准确翻译技术术语，保留Markdown格式、代码块、表格结构，不要添加任何解释。\n\n{content}"
                    resp = client.chat.completions.create(
                        model="deepseek-v4-flash",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=8192,
                    )
                    zh_content = resp.choices[0].message.content.strip()
                    if zh_content and len(zh_content) > 10:
                        translations[content_hash] = zh_content
                    else:
                        zh_content = content
                except Exception:
                    zh_content = content
                time.sleep(0.3)

            lines = zh_content.split("\n")
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
                    doc_chunks.append(body.strip())
                else:
                    paragraphs = re.split(r'\n\s*\n', body)
                    sub_cur = []
                    for para in paragraphs:
                        if sub_cur and len("\n\n".join(sub_cur)) + len(para) > 1800:
                            sub_body = "\n\n".join(sub_cur).strip()
                            if len(sub_body) >= 20:
                                doc_chunks.append(sub_body)
                            sub_cur = [para]
                        else:
                            sub_cur.append(para)
                    if sub_cur:
                        sub_body = "\n\n".join(sub_cur).strip()
                        if len(sub_body) >= 20:
                            doc_chunks.append(sub_body)

            for ci, chunk_body in enumerate(doc_chunks):
                all_chunks.append({
                    "content": chunk_body,
                    "source": "translated_official_docs",
                    "module": rel_path,
                    "file_name": md_file.name,
                    "language": "zh",
                    "chunk_index": ci,
                    "source_file": rel_path,
                    "chunk_hash": hashlib.md5(chunk_body.encode()).hexdigest(),
                })

        if TRANSLATION_CACHE_PATH.parent.exists() or TRANSLATION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True):
            with open(TRANSLATION_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump({"__commit__": new_current, "translations": translations}, f, ensure_ascii=False, indent=2)

        _UPDATE_STATUS["progress"] = f"共 {len(all_chunks)} 个切片，开始向量化..."

        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME, local_files_only=True)
        embed_device = "cuda:0" if torch.cuda.is_available() else "cpu"
        model = AutoModel.from_pretrained(EMBEDDING_MODEL_NAME, local_files_only=True).to(embed_device)
        model.eval()

        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            collection = chroma_client.get_collection(COLLECTION_NAME)
        except Exception:
            try:
                chroma_client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
            collection = chroma_client.create_collection(name=COLLECTION_NAME)

        new_count = 0
        BATCH = 32
        for bi in range(0, len(all_chunks), BATCH):
            if (bi // BATCH) % 5 == 0:
                _UPDATE_STATUS["progress"] = f"向量化: {min(bi + BATCH, len(all_chunks))}/{len(all_chunks)}"

            batch = all_chunks[bi:bi + BATCH]
            texts = [c["content"] for c in batch]
            metas = [{k: v for k, v in c.items() if k != "content"} for c in batch]
            ids = [f"update_{c['chunk_hash'][:16]}" for c in batch]

            inputs = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt").to(embed_device)
            with torch.no_grad():
                outputs = model(**inputs)
                emb = outputs.last_hidden_state[:, 0]
                emb = torch.nn.functional.normalize(emb, p=2, dim=1)
            emb_list = emb.cpu().numpy().tolist()

            collection.add(embeddings=emb_list, documents=texts, metadatas=metas, ids=ids)
            new_count += len(batch)

        # 文档已更新：向量缓存作废，否则下次启动会用旧向量覆盖新索引
        try:
            from backend.config import VECTOR_CACHE_PATH, VECTOR_CACHE_META_PATH
            VECTOR_CACHE_PATH.unlink(missing_ok=True)
            VECTOR_CACHE_META_PATH.unlink(missing_ok=True)
            _UPDATE_STATUS["progress"] = "已清除向量缓存（下次启动重建）"
        except Exception:
            pass

        reload_index()
        _UPDATE_STATUS = {"running": False, "progress": "更新完成", "message": f"新增 {new_count} 条向量"}
        return {"status": "ok", "message": f"更新完成，共处理 {len(md_files)} 个文档，新增 {new_count} 条向量", "new_vectors": new_count, "deleted_vectors": 0}

    except Exception as e:
        _UPDATE_STATUS = {"running": False, "progress": "更新失败", "message": str(e)}
        return {"status": "error", "message": str(e)}
    finally:
        _UPDATE_LOCK.release()
