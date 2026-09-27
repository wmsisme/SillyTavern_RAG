import os
import re
import subprocess
import time
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from threading import Lock

from backend.config import (
    DOCS_REPO_DIR, UPSTREAM_URL, UPSTREAM_BRANCH,
    TRANSLATION_CACHE_PATH, REGEX_CHUNKS_DIR, REGEX_README_PATH,
    CHROMA_DIR, COLLECTION_NAME, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    EMBEDDING_MODEL_NAME,
)
from backend.services.rag_service import reload_index

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")

_UPDATE_LOCK = Lock()
_UPDATE_STATUS = {"running": False, "progress": "", "message": ""}

# 本次更新中翻译失败的文档（相对路径）。
# 之所以要单独记：空响应/异常以前被 `except: zh_content = content` 静默吞掉，
# 结果英文原文被当成"译文"写进缓存，下次还会被当成已有译文复用 —— 失败就永久隐身了。
_translate_failures: List[str] = []

_logger = logging.getLogger("rag_update")

# ── 本次更新的用量账（时间 + token）─────────────────────────────
# DeepSeek 的 OpenAI 兼容接口每次都返回 usage，之前没记，所以"一次更新花了多少 token"
# 只能估。现在统一记账，随结果一起回报（前端完成弹窗会直接显示）。
_USAGE = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _reset_usage():
    _USAGE.update({"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})


def _record_usage(resp):
    """记一次调用的 token。**失败/空返回也要记** —— 它也真的烧了 token。"""
    u = getattr(resp, "usage", None)
    if u is None:
        return
    p = int(getattr(u, "prompt_tokens", 0) or 0)
    c = int(getattr(u, "completion_tokens", 0) or 0)
    t = int(getattr(u, "total_tokens", 0) or 0) or (p + c)
    _USAGE["calls"] += 1
    _USAGE["prompt_tokens"] += p
    _USAGE["completion_tokens"] += c
    _USAGE["total_tokens"] += t


def _usage_text() -> str:
    if not _USAGE["calls"]:
        return "未产生翻译调用（全部命中缓存）"
    return (f"翻译 {_USAGE['total_tokens']} tokens"
            f"（输入 {_USAGE['prompt_tokens']} / 输出 {_USAGE['completion_tokens']}，"
            f"{_USAGE['calls']} 次调用）")


def _call_llm_for_translation(client, content: str) -> str:
    """调一次翻译；返回空串表示失败（由调用方决定怎么处理）。

    这里要显式检查 content 是否为空：某些推理模型（如 deepseek-v4-flash）会把
    整个 max_tokens 预算烧在隐藏的 reasoning_content 上，content 返回空串，
    但 HTTP 状态码依然是 200 —— 不检查就会当成"翻译成功但结果为空"。
    """
    prompt = (
        "把下面的英文技术文档翻译成中文。要求：准确翻译技术术语，保留Markdown格式、"
        f"代码块、表格结构，不要添加任何解释。\n\n{content}"
    )
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=8192,
    )
    _record_usage(resp)
    choice = resp.choices[0]
    text = (choice.message.content or "").strip()

    if not text:
        reasoning = getattr(choice.message, "reasoning_content", "") or ""
        _logger.warning(
            "翻译返回空内容：finish_reason=%s reasoning长度=%d 模型=%s"
            "（推理模型会把预算烧在 reasoning 上，请改用非推理模型）",
            choice.finish_reason, len(reasoning), DEEPSEEK_MODEL,
        )
    elif choice.finish_reason == "length":
        _logger.warning("翻译被截断（finish_reason=length，max_tokens 不够），仍采用该结果")

    return text


def _translate_cached(client, content: str, content_hash: str, translations: dict,
                      rel_path: str) -> str:
    """带缓存的翻译。成功才写缓存；失败不写，避免英文原文污染缓存。"""
    text = _call_llm_for_translation(client, content)
    if text and len(text) > 10:
        translations[content_hash] = text
        return text

    # 失败：不写缓存，保留英文原文（检索至少还能命中英文），并登记以便回报用户
    _translate_failures.append(rel_path)
    _logger.warning("文档翻译失败，本次索引使用英文原文: %s", rel_path)
    return content


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


def _git_ok(cmd: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
    """跑 git 并**检查退出码**。

    `_retry_git`/`_run_git` 都不看 returncode（只捕获超时之类的异常），
    所以 `git fetch` 失败会被当成成功、静默用旧引用比较。这里补上。
    """
    r = _retry_git(cmd, cwd)
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip().splitlines()
        raise RuntimeError((msg[-1] if msg else f"git 退出码 {r.returncode}")[:200])
    return r


def get_local_commit() -> str:
    try:
        r = _run_git(["git", "rev-parse", "HEAD"])
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def _get_translation_hashes() -> set:
    """翻译缓存的**键集合** = 已经进过索引的文件内容指纹（md5 of 英文原文）。

    用来回答「工作区里这个未提交改动，是不是其实已经索引过了」。
    不引入新状态，只复用翻译缓存本来就有的键 —— 所有写入方（run_update /
    内联重建 / 重建索引.py / 索引更新.py）都会往里写键，天然一致。
    """
    try:
        if TRANSLATION_CACHE_PATH.exists():
            with open(TRANSLATION_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return set((data.get("translations") or {}).keys())
    except Exception:
        pass
    return set()


def _get_indexed_commit() -> str:
    """读翻译缓存里记录的 __commit__ —— 即上次真正被索引的文档版本。"""
    try:
        if TRANSLATION_CACHE_PATH.exists():
            with open(TRANSLATION_CACHE_PATH, "r", encoding="utf-8") as f:
                return (json.load(f) or {}).get("__commit__", "") or ""
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
    """判断「文档仓库当前状态」与「已被索引的状态」是否有差异。

    重要修正（2026-09-24）：原来只比较 upstream/main 与本地 HEAD，于是
    ① 只看上游提交，本地新提交（含手工改动后 commit）永远检测不到；
    ② run_update 里也只比较 merge upstream 前后的 HEAD，本地变更永远进不来。
    结果就是：要么永远判定"已是最新"，要么一旦更新就把全部 90 篇重译+重灌。
    现在统一以**翻译缓存里记录的 __commit__（= 上次实际索引的 commit）**为基准：
      - 上游比索引新        → 提示更新
      - 本地 HEAD 比索引新  → 提示更新（本地有未索引的提交）
    上游没有新提交时就不做网络 fetch，避免无谓等待。
    """
    if not (DOCS_REPO_DIR / ".git").exists():
        return {"has_update": False, "changed_files": [], "current_commit": "",
                "upstream_commit": "", "message": "文档仓库未初始化", "indexed_commit": ""}

    cwd = str(DOCS_REPO_DIR)
    local = get_local_commit()
    indexed = _get_indexed_commit()

    # 上游没取到过时先 fetch 一次
    remotes = _run_git(["git", "remote"], cwd).stdout.strip()
    if "upstream" not in remotes:
        _run_git(["git", "remote", "add", "upstream", UPSTREAM_URL], cwd)

    # 关键修正（2026-09-26）：**每次检查都要 fetch**。
    # 原来只在 refs/remotes/upstream/main 不存在时才 fetch，于是引用一旦建立，
    # 之后永远拿本地那份旧引用做比较 —— 上游发了新文档也检测不到，
    # run_update 也只是 merge 那个旧引用，实际等于「自动更新」永久失灵。
    fetch_error = ""
    try:
        _git_ok(["git", "fetch", "upstream"], cwd)
    except Exception as e:
        fetch_error = str(e)[:120]
        _logger.warning("fetch upstream 失败（改用本地已知引用 + 本地漂移判断）: %s", fetch_error)

    upstream = _run_git(["git", "rev-parse", f"upstream/{UPSTREAM_BRANCH}"], cwd).stdout.strip()
    if not upstream:
        return {"has_update": False, "changed_files": [], "current_commit": local[:16],
                "upstream_commit": "", "message": "无法获取上游更新", "indexed_commit": indexed[:16]}

    # 索引状态：没有记录时（例如刚重建过但缓存没写 commit）退回用本地 HEAD 判断上游
    baseline = indexed or local

    has_update = False
    changed_files = []
    reasons = []

    # ① 上游相对基准有变化
    if upstream and upstream != baseline:
        r = _run_git(["git", "diff", "--name-only", baseline, upstream], cwd)
        files_up = [f.strip() for f in r.stdout.strip().split("\n") if f.strip()]
        if files_up:
            has_update = True
            changed_files.extend(files_up)
            reasons.append(f"上游有 {len(files_up)} 个文件变更")

    # ② 本地 HEAD 相对基准有变化（本地提交/手工改动后 commit）
    if local and local != baseline:
        r = _run_git(["git", "diff", "--name-only", baseline, local], cwd)
        files_local = [f.strip() for f in r.stdout.strip().split("\n") if f.strip()]
        if files_local:
            has_update = True
            changed_files.extend(f for f in files_local if f not in changed_files)
            reasons.append(f"本地有 {len(files_local)} 个文件变更")

    # ③ 工作区未提交的改动：run_update 索引的是工作区文件，这些同样需要重新索引。
    #    但要排除「内容其实已经索引过」的脏文件 —— 否则点「立即更新」跑完一轮后，
    #    文件依然是未提交状态，检测会继续报"有更新"，界面上红点永远消不掉（实测踩到）。
    indexed_hashes = _get_translation_hashes()
    r = _run_git(["git", "status", "--porcelain", "--", "*.md"], cwd)
    dirty = []
    for ln in r.stdout.splitlines():
        if not ln.strip():
            continue
        # porcelain 是 "XY <path>"（2 列状态 + 1 个空格）。**不能**对整体 stdout 做
        # strip()：那会吃掉首行的前导空格，ln[3:] 就把路径截掉一个字
        # （实测 "Usage/worldinfo.md" → "sage/worldinfo.md"）。
        path = ln[3:].strip().strip('"')
        if not path:
            continue
        try:
            content = (DOCS_REPO_DIR / path).read_text(encoding="utf-8")
        except Exception:
            dirty.append(path)
            continue
        if hashlib.md5(content.encode()).hexdigest() in indexed_hashes:
            continue
        dirty.append(path)
    if dirty:
        has_update = True
        changed_files.extend(f for f in dirty if f not in changed_files)
        reasons.append(f"工作区有 {len(dirty)} 个未提交改动")

    return {
        "has_update": has_update,
        "changed_files": changed_files,
        "current_commit": local[:16],
        "upstream_commit": (upstream or "")[:16],
        "indexed_commit": baseline[:16],
        "message": ("；".join(reasons) if has_update
                    else "已是最新版本" + (f"（注意：fetch 上游失败，仅按本地已知引用判断：{fetch_error}）"
                                          if fetch_error else "")),
    }


def run_update() -> dict:
    global _UPDATE_STATUS
    if not _UPDATE_LOCK.acquire(blocking=False):
        return {"status": "busy", "message": "更新正在执行中，请稍后再试"}

    _translate_failures.clear()
    _reset_usage()
    _t_start = time.monotonic()
    try:
        _UPDATE_STATUS = {"running": True, "progress": "开始更新...", "message": ""}

        _UPDATE_STATUS["progress"] = "正在拉取上游文档..."
        # 同样不 chdir：全程显式传 cwd（这是线程里的常驻服务进程）
        cwd = str(DOCS_REPO_DIR)

        # 索引的是工作区文件，所以先把工作区状态与「上次索引的版本」比一遍，
        # 而不是只比 merge 前后的 HEAD（那样本地提交/未提交改动永远检测不到）。
        drift = _do_check_update()
        if not drift.get("has_update"):
            elapsed = time.monotonic() - _t_start
            _UPDATE_STATUS = {"running": False, "progress": "已完成", "message": "无需更新"}
            return {"status": "ok",
                    "message": f"已是最新版本，无需更新（耗时 {elapsed:.1f}s，{_usage_text()}）",
                    "new_vectors": 0, "deleted_vectors": 0, "translate_failures": [],
                    "elapsed_s": round(elapsed, 1), "usage": dict(_USAGE)}

        # 上游有新东西才 merge（本地无变更时 merge 是空操作）
        try:
            _retry_git(["git", "merge", f"upstream/{UPSTREAM_BRANCH}"], cwd)
        except Exception as e:
            _logger.warning("合并上游失败（继续用当前工作区索引）: %s", str(e)[:120])

        _UPDATE_STATUS["progress"] = f"检测到变更（{drift.get('message','')}），开始处理..."

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
                zh_content = _translate_cached(
                    client, content, content_hash, translations, rel_path)
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

        # __commit__ 记为**索引完成时**的 HEAD：这是「已索引版本」的权威标记，
        # check_update / run_update 都拿它当基准判断是否有漂移。
        # 但**有翻译失败时不能推进**：失败的那几篇这次是以英文原文入库的，
        # 一旦推进，check_update 就会判定"已是最新"，它们永远不会被重试。
        # 译文照常落盘（成功的那些不白干），失败篇目没进缓存 → 下次更新会重译。
        indexed_now = get_local_commit()
        prev_indexed = (cache or {}).get("__commit__", "") or ""
        if _translate_failures:
            commit_to_write = prev_indexed
            _logger.warning("有 %d 篇翻译失败，__commit__ 保持为 %s（不推进），下次更新会重译",
                            len(_translate_failures), prev_indexed[:8] or "空")
        else:
            commit_to_write = indexed_now or prev_indexed
        if TRANSLATION_CACHE_PATH.parent.exists() or TRANSLATION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True):
            with open(TRANSLATION_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump({"__commit__": commit_to_write, "translations": translations}, f, ensure_ascii=False, indent=2)

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
            collection = chroma_client.create_collection(
                name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

        # 先删掉这批文档的旧切片，再写新的 —— 否则每次更新都是"纯追加"：
        # 本次要重新向量化全部 md_files，不做删除就会把整个文档集复制一份
        # （实测一次更新让 1798 条变成 2963 条，同一文档的新旧译文并存、召回重复）。
        # 只删 translated_official_docs，正则知识库与 QA 补充块source 不同，不受影响。
        deleted_count = 0
        try:
            existing = collection.get(where={"source": "translated_official_docs"}, include=[])
            existing_ids = existing.get("ids") or []
            if existing_ids:
                for i in range(0, len(existing_ids), 256):
                    collection.delete(ids=existing_ids[i:i + 256])
                deleted_count = len(existing_ids)
                _logger.info("已清除旧的官方文档切片 %d 条（避免新旧并存）", deleted_count)
        except Exception as e:
            _logger.warning("清除旧切片失败（继续写入，可能产生重复）: %s", str(e)[:120])

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

        elapsed = time.monotonic() - _t_start
        summary = (f"更新完成，共处理 {len(md_files)} 个文档，"
                   f"清除旧切片 {deleted_count} 条、写入 {new_count} 条向量；"
                   f"耗时 {elapsed:.1f}s，{_usage_text()}")
        if _translate_failures:
            # 不能让翻译失败悄悄过去：这些文档这次是以英文原文入库的，
            # 且没进缓存，下次更新会重试（__commit__ 也没推进，所以检测得到）。
            summary += (f"；其中 {len(_translate_failures)} 篇翻译失败、本次以英文原文入库"
                        f"（__commit__ 未推进，下次更新会自动重试）")
            _logger.warning("翻译失败的文档：%s", "、".join(_translate_failures))
        _logger.info("本次更新用量：耗时 %.1fs，%s", elapsed, _usage_text())
        _UPDATE_STATUS = {"running": False, "progress": "更新完成", "message": summary}
        return {
            "status": "ok",
            "message": summary,
            "new_vectors": new_count,
            "deleted_vectors": deleted_count,
            "translate_failures": list(_translate_failures),
            "elapsed_s": round(elapsed, 1),
            "usage": dict(_USAGE),
        }

    except Exception as e:
        elapsed = time.monotonic() - _t_start
        _UPDATE_STATUS = {"running": False, "progress": "更新失败", "message": str(e)}
        return {"status": "error",
                "message": f"{e}（已耗时 {elapsed:.1f}s，{_usage_text()}）",
                "elapsed_s": round(elapsed, 1), "usage": dict(_USAGE)}
    finally:
        _UPDATE_LOCK.release()
