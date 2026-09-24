import os
import sys

# 必须在所有 HF 相关 import 之前设置
HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
HF_DISABLE_SSL = os.environ.get("HF_HUB_DISABLE_SSL_VERIFY", "0")
os.environ["HF_ENDPOINT"] = HF_ENDPOINT
if HF_DISABLE_SSL == "1":
    os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    import ssl as _ssl
    _ssl._create_default_https_context = _ssl._create_unverified_context
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    import requests as _requests
    _old_request = _requests.Session.request
    def _patched_request(self, method, url, *args, **kwargs):
        kwargs.setdefault("verify", False)
        return _old_request(self, method, url, *args, **kwargs)
    _requests.Session.request = _patched_request

import shutil
import re
import subprocess
import logging
import json
import hashlib
import time
import argparse
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, Tuple

from langchain_text_splitters import MarkdownHeaderTextSplitter
import torch
from transformers import AutoModel, AutoTokenizer
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.indexes._sql_record_manager import SQLRecordManager

# ==================== 配置区 ====================
BASE_DIR = Path(r"d:\code_item\酒馆rag\RAG")
DOCS_REPO_DIR = BASE_DIR / "SillyTavern-Docs"
DOCS_SOURCE_DIR = DOCS_REPO_DIR
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"
BACKUP_DIR = BASE_DIR / "backup"
LOG_DIR = BASE_DIR / "logs"
USER_REPO_DIR = Path(r"d:\code_item\酒馆rag")

UPSTREAM_URL = "https://github.com/SillyTavern/SillyTavern-Docs.git"
UPSTREAM_BRANCH = "main"

EMBEDDING_MODEL_NAME = "BAAI/bge-large-zh-v1.5"
EMBEDDING_DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

HEADERS_TO_SPLIT_ON = [
    ("#", "H1"),
    ("##", "H2"),
    ("###", "H3"),
]

CHROMA_COLLECTION_NAME = "sillytavern_docs"
RECORD_MANAGER_DB = f"sqlite:///{BASE_DIR / 'record_manager_cache.sql'}"

REGEX_README_PATH = BASE_DIR / "README.md"
REGEX_CHUNKS_DIR = BASE_DIR / "正则表达式" / "rag_chunks"

GIT_RETRY_TIMES = 3
GIT_RETRY_DELAY = 10
MIN_DISK_SPACE_MB = 2048

LOG_RETENTION_DAYS = 30
LFS_SIZE_THRESHOLD_MB = 30
BACKUP_SIZE_THRESHOLD_MB = 100

# ==================== 日志配置 ====================
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("rag_pipeline")


# ==================== 工具函数 ====================

def cleanup_old_logs():
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    deleted = 0
    for log_file in LOG_DIR.glob("update_*.log"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                log_file.unlink()
                deleted += 1
        except Exception:
            pass
    if deleted:
        logger.info(f"已清理 {deleted} 个超过 {LOG_RETENTION_DAYS} 天的旧日志")


def retry_operation(operation_name, func, max_retries=3, delay=5, *args, **kwargs):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(
                    f"{operation_name} 第 {attempt}/{max_retries} 次失败，"
                    f"{delay} 秒后重试: {e}"
                )
                time.sleep(delay)
            else:
                logger.error(f"{operation_name} 重试 {max_retries} 次后仍失败")
                raise


def check_disk_space(min_mb: int = MIN_DISK_SPACE_MB):
    usage = shutil.disk_usage(str(BASE_DIR))
    free_mb = usage.free // (1024 * 1024)
    logger.info(f"磁盘剩余空间: {free_mb}MB (阈值: {min_mb}MB)")

    if free_mb < min_mb:
        logger.warning("磁盘空间不足，尝试清理旧日志...")
        cleanup_old_logs()
        usage = shutil.disk_usage(str(BASE_DIR))
        free_mb = usage.free // (1024 * 1024)
        logger.info(f"清理后剩余空间: {free_mb}MB")

    if free_mb < min_mb:
        raise RuntimeError(
            f"磁盘空间严重不足: {free_mb}MB < {min_mb}MB，中止处理"
        )


def get_dir_size_mb(dir_path: Path) -> float:
    if not dir_path.exists():
        return 0.0
    total = 0
    for f in dir_path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total / (1024 * 1024)


def backup_chromadb():
    if not CHROMA_PERSIST_DIR.exists():
        return
    size_mb = get_dir_size_mb(CHROMA_PERSIST_DIR)
    logger.info(f"ChromaDB 目录大小: {size_mb:.1f}MB")

    if size_mb <= LFS_SIZE_THRESHOLD_MB:
        logger.info(f"ChromaDB 大小未超过 {LFS_SIZE_THRESHOLD_MB}MB，无需特殊处理")
        return

    if size_mb > BACKUP_SIZE_THRESHOLD_MB:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"chroma_db_backup_{timestamp}.zip"
        logger.info(
            f"ChromaDB 超过 {BACKUP_SIZE_THRESHOLD_MB}MB，"
            f"创建备份包: {backup_file}"
        )
        with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in CHROMA_PERSIST_DIR.rglob("*"):
                if f.is_file():
                    arcname = f.relative_to(CHROMA_PERSIST_DIR)
                    zf.write(f, arcname)
        logger.info(f"备份包创建完成")
    else:
        logger.info(
            f"ChromaDB 大小在 {LFS_SIZE_THRESHOLD_MB}~{BACKUP_SIZE_THRESHOLD_MB}MB "
            f"之间，由 Git LFS 处理"
        )


# ==================== 翻译模块 ====================

# 密钥只从 .env / 环境变量读取，源码里不留明文（.env 已在 .gitignore 中）。
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR.parent / ".env")
except ImportError:
    pass

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
if not DEEPSEEK_API_KEY:
    logger.warning("未找到 DEEPSEEK_API_KEY —— 请在项目根目录 .env 中填写（模板见 .env.example），"
                   "或设为环境变量。翻译功能将不可用。")
TRANSLATION_CACHE_PATH = BASE_DIR / "translation_cache.json"

_client = None

def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


def _load_translation_cache() -> dict:
    if TRANSLATION_CACHE_PATH.exists():
        try:
            with open(TRANSLATION_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            pass
    return {"commit_hash": "", "translations": {}}


def _save_translation_cache(cache: dict):
    TRANSLATION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRANSLATION_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_docs_commit_hash() -> str:
    try:
        os.chdir(str(DOCS_REPO_DIR))
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except Exception:
        logger.warning("无法获取文档仓库 commit hash")
        return ""


def _translate_via_deepseek(text: str) -> str:
    client = _get_client()
    prompt = f"把下面的英文技术文档翻译成中文。要求：准确翻译技术术语，保留Markdown格式、代码块、表格结构，不要添加任何解释。\n\n{text}"
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=8192,
    )
    result = resp.choices[0].message.content.strip()
    return result


def translate_loaded_documents(documents: List[Document], force_retranslate: bool = False) -> List[Document]:
    logger.info(f"使用 DeepSeek API 翻译 {len(documents)} 个英文文档...")

    current_commit = get_docs_commit_hash()
    cache = _load_translation_cache()

    cached_commit = cache.get("commit_hash", "")
    translations_cache = cache.get("translations", {})

    if current_commit and cached_commit == current_commit and not force_retranslate:
        logger.info(f"翻译缓存与当前 commit ({current_commit[:8]}) 匹配，优先使用缓存")
    elif current_commit:
        if cached_commit and cached_commit != current_commit:
            logger.info(f"commit 变更: {cached_commit[:8]} → {current_commit[:8]}，增量翻译")
        else:
            logger.info(f"当前 commit: {current_commit[:8]}，开始翻译")

    translated_docs = []
    failed_count = 0
    cached_count = 0
    new_translated_count = 0

    for i, doc in enumerate(documents):
        source = doc.metadata.get("source", "unknown")
        content = doc.page_content
        if not content or len(content.strip()) < 50:
            translated_docs.append(doc)
            continue

        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

        if content_hash in translations_cache and not force_retranslate:
            doc.metadata["language"] = "zh"
            doc.metadata["original_en_length"] = len(content)
            doc.page_content = translations_cache[content_hash]
            translated_docs.append(doc)
            cached_count += 1
            continue

        if (i + 1) % 5 == 0 or i == 0:
            logger.info(f"  翻译进度: {i + 1}/{len(documents)} (缓存命中: {cached_count}) - {source}")

        try:
            zh_content = _translate_via_deepseek(content)
            if zh_content and len(zh_content) > 10:
                translations_cache[content_hash] = zh_content
                cache["commit_hash"] = current_commit
                cache["translations"] = translations_cache
                _save_translation_cache(cache)
                doc.metadata["language"] = "zh"
                doc.metadata["original_en_length"] = len(content)
                doc.page_content = zh_content
                translated_docs.append(doc)
                new_translated_count += 1
            else:
                raise RuntimeError("翻译结果为空")
        except Exception as e:
            logger.warning(f"  翻译失败: {source} — {str(e)[:80]}")
            doc.metadata["language"] = "en"
            translated_docs.append(doc)
            failed_count += 1

        time.sleep(0.5)

    if current_commit:
        cache["commit_hash"] = current_commit
        cache["translations"] = translations_cache
        _save_translation_cache(cache)

    logger.info(
        f"翻译完成 (DeepSeek): "
        f"缓存命中 {cached_count} | 新翻译 {new_translated_count} | 失败 {failed_count}"
    )
    return translated_docs


# ==================== 步骤 1：拉取上游更新 ====================

def git_setup_upstream():
    os.chdir(str(DOCS_REPO_DIR))
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "upstream"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            logger.info("添加上游远程仓库 upstream...")
            subprocess.run(
                ["git", "remote", "add", "upstream", UPSTREAM_URL],
                check=True, capture_output=True, text=True,
            )
        else:
            existing_url = result.stdout.strip()
            if existing_url != UPSTREAM_URL:
                logger.info(f"upstream URL 不匹配，更新为 {UPSTREAM_URL}")
                subprocess.run(
                    ["git", "remote", "set-url", "upstream", UPSTREAM_URL],
                    check=True, capture_output=True, text=True,
                )
            else:
                logger.info(f"upstream 已配置: {existing_url}")
    except subprocess.CalledProcessError as e:
        logger.error(f"upstream 配置失败: {e.stderr}")
        raise


def _do_git_fetch():
    subprocess.run(
        ["git", "fetch", "upstream"],
        check=True, capture_output=True, text=True,
    )


def _do_git_merge():
    try:
        subprocess.run(
            ["git", "merge", f"upstream/{UPSTREAM_BRANCH}"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr if isinstance(e.stderr, str) else e.stderr.decode()
        if "Already up to date" in stderr or "already up to date" in stderr:
            logger.info("已是最新，无需更新")
            return False
        raise
    return True


def git_pull_upstream() -> Tuple[List[str], bool]:
    os.chdir(str(DOCS_REPO_DIR))
    logger.info("正在 fetch upstream...")
    retry_operation("Git fetch", _do_git_fetch, GIT_RETRY_TIMES, GIT_RETRY_DELAY)

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    current_branch = result.stdout.strip()
    logger.info(f"当前分支: {current_branch}")

    result_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    head_before = result_before.stdout.strip()

    logger.info(f"正在 merge upstream/{UPSTREAM_BRANCH}...")
    merged = retry_operation(
        "Git merge", _do_git_merge, GIT_RETRY_TIMES, GIT_RETRY_DELAY
    )

    if not merged:
        return [], False

    result = subprocess.run(
        ["git", "diff", "--name-only", head_before, "HEAD"],
        capture_output=True, text=True,
    )
    changed_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    changed_md_files = [f for f in changed_files if f.endswith(".md")]

    logger.info(f"变更文件总数: {len(changed_files)}, Markdown 文件数: {len(changed_md_files)}")
    for f in changed_md_files:
        logger.info(f"  [变更] {f}")

    return changed_md_files, True


# ==================== 步骤 2：文档预处理 ====================

def check_data_consistency(docs_dir: Path, max_deviation_pct: float = 5.0):
    os.chdir(str(docs_dir))
    local_md = len(list(docs_dir.rglob("*.md")))

    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", f"upstream/{UPSTREAM_BRANCH}", "--name-only"],
            capture_output=True, text=True, check=True,
        )
        upstream_md = len(
            [f for f in result.stdout.strip().split("\n") if f.endswith(".md")]
        )
    except subprocess.CalledProcessError:
        logger.warning("无法获取上游仓库文件列表，跳过一致性检查")
        return

    if upstream_md == 0:
        logger.warning("上游仓库 Markdown 文件数为 0，跳过一致性检查")
        return

    deviation = abs(local_md - upstream_md) / upstream_md * 100
    logger.info(
        f"文档数量: 本地 {local_md} vs 上游 {upstream_md} (偏差 {deviation:.1f}%)"
    )

    if deviation > max_deviation_pct:
        raise RuntimeError(
            f"文档数量偏差 {deviation:.1f}% 超过阈值 {max_deviation_pct}%，中止处理"
        )


def load_markdown_documents(docs_dir: Path, exclude_patterns: List[str] = None) -> List[Document]:
    if exclude_patterns is None:
        exclude_patterns = ["_includes", ".github", "node_modules", "static"]

    md_files = []
    for f in docs_dir.rglob("*.md"):
        rel = str(f.relative_to(docs_dir))
        if any(pat in rel.split(os.sep) for pat in exclude_patterns):
            continue
        if f.name in ("LICENSE", "LicenseCredits.md", "readme.md"):
            continue
        md_files.append(f)

    logger.info(f"找到 {len(md_files)} 个有效 Markdown 文件")
    skipped = len(list(docs_dir.rglob("*.md"))) - len(md_files)
    if skipped:
        logger.info(f"已排除 {skipped} 个非文档文件")

    documents = []
    for f in sorted(md_files):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
            if not content.strip():
                logger.debug(f"跳过空文件: {f.name}")
                continue

            rel_path = str(f.relative_to(docs_dir)).replace("\\", "/")
            documents.append(Document(
                page_content=content,
                metadata={
                    "source": rel_path,
                    "file_name": f.name,
                    "file_size": len(content),
                },
            ))
        except UnicodeDecodeError:
            logger.warning(f"编码错误，尝试其他编码: {f.name}")
            try:
                with open(f, "r", encoding="latin-1") as fp:
                    content = fp.read()
                rel_path = str(f.relative_to(docs_dir)).replace("\\", "/")
                documents.append(Document(
                    page_content=content,
                    metadata={"source": rel_path, "file_name": f.name},
                ))
                logger.info(f"  (使用 latin-1 编码读取)")
            except Exception as e2:
                logger.warning(f"读取彻底失败: {f.name} - {e2}")

    logger.info(f"成功加载 {len(documents)} 个文档")
    return documents


def load_specific_markdown_documents(docs_dir: Path, file_paths: List[str]) -> List[Document]:
    documents = []
    for file_path in file_paths:
        full_path = docs_dir / file_path
        if not full_path.exists():
            logger.debug(f"跳过不存在的文件: {file_path}")
            continue
        try:
            with open(full_path, "r", encoding="utf-8") as fp:
                content = fp.read()
            if not content.strip():
                logger.debug(f"跳过空文件: {file_path}")
                continue
            rel_path = str(full_path.relative_to(docs_dir)).replace("\\", "/")
            documents.append(Document(
                page_content=content,
                metadata={
                    "source": rel_path,
                    "file_name": full_path.name,
                    "file_size": len(content),
                },
            ))
        except UnicodeDecodeError:
            logger.warning(f"编码错误，尝试其他编码: {file_path}")
            try:
                with open(full_path, "r", encoding="latin-1") as fp:
                    content = fp.read()
                rel_path = str(full_path.relative_to(docs_dir)).replace("\\", "/")
                documents.append(Document(
                    page_content=content,
                    metadata={"source": rel_path, "file_name": full_path.name},
                ))
            except Exception as e2:
                logger.warning(f"读取彻底失败: {file_path} - {e2}")
        except Exception as e:
            logger.warning(f"加载文件失败: {file_path} - {e}")

    logger.info(f"按需加载 {len(documents)} 个文档（共 {len(file_paths)} 个指定文件）")
    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )

    all_chunks: List[Document] = []
    failed_count = 0

    for i, doc in enumerate(documents):
        source = doc.metadata.get("source", "unknown")
        try:
            chunks = splitter.split_text(doc.page_content)
            for j, chunk in enumerate(chunks):
                chunk.metadata.update(doc.metadata)
                chunk.metadata["doc_id"] = source
                chunk.metadata["chunk_id"] = f"{source}#chunk{j}"
                chunk.metadata["chunk_hash"] = hashlib.md5(
                    chunk.page_content.encode("utf-8")
                ).hexdigest()
            all_chunks.extend(chunks)
        except Exception as e:
            logger.debug(f"切片失败，保留完整文档 {source}: {e}")
            doc.metadata["doc_id"] = source
            doc.metadata["chunk_id"] = f"{source}#chunk0"
            doc.metadata["chunk_hash"] = hashlib.md5(
                doc.page_content.encode("utf-8")
            ).hexdigest()
            all_chunks.append(doc)
            failed_count += 1

    if failed_count:
        logger.warning(f"{failed_count} 个文档未能切片，已作为完整 chunk 保留")

    logger.info(f"切片完成: {len(documents)} 个文档 → {len(all_chunks)} 个 chunk")
    return all_chunks


def load_regex_documents() -> List[Document]:
    docs: List[Document] = []

    # 表层：learn-regex (README.md)
    if REGEX_README_PATH.exists():
        with open(REGEX_README_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
        blocks = re.split(r"\n(?=## )", raw)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            lines = block.split("\n")
            header = lines[0].lstrip("#").strip()
            if not header or len(block) < 50:
                continue
            h = hashlib.md5(block.encode("utf-8")).hexdigest()[:8]
            safe_topic = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', header[:40])
            source_id = f"learn-regex_{safe_topic}_{h}"
            docs.append(Document(
                page_content=block,
                metadata={
                    "source": source_id,
                    "type": "syntax",
                    "language": "zh",
                    "topic": header,
                    "category": "regex",
                    "chunk_hash": hashlib.md5(block.encode("utf-8")).hexdigest(),
                },
            ))

    # 中层：mastering-regex (rag_chunks)
    if REGEX_CHUNKS_DIR.exists():
        for f in sorted(REGEX_CHUNKS_DIR.rglob("*.txt")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    text = fp.read().strip()
                if not text:
                    continue
                rel = f.relative_to(REGEX_CHUNKS_DIR)
                parts = str(rel).replace("\\", "/").split("/")
                topic = parts[0] if parts else "未知"
                h = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
                safe_topic = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', topic[:40])
                source_id = f"mastering-regex_{safe_topic}_{h}"
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": source_id,
                        "type": "principle",
                        "language": "zh",
                        "topic": topic,
                        "category": "regex",
                        "chunk_hash": hashlib.md5(text.encode("utf-8")).hexdigest(),
                    },
                ))
            except Exception:
                pass

    logger.info(f"加载正则知识源: {len(docs)} 条 (learn-regex + mastering-regex)")
    return docs


# ==================== 步骤 3：向量化 ====================

class _BGEAdapter:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME, local_files_only=True)
        self.model = AutoModel.from_pretrained(EMBEDDING_MODEL_NAME, local_files_only=True, weights_only=False).to(EMBEDDING_DEVICE)
        self.model.eval()
        self.device = EMBEDDING_DEVICE

    def _encode(self, texts: List[str]) -> List[List[float]]:
        inputs = self.tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0]
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings.cpu().numpy().tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._encode([text])[0]


def create_embeddings():
    logger.info(f"加载 BGE 中文嵌入模型: {EMBEDDING_MODEL_NAME}")
    logger.info(f"设备: {EMBEDDING_DEVICE}")
    logger.info("bge-large-zh-v1.5 专为中文优化，1024维向量")
    return _BGEAdapter()


def create_vectorstore(embeddings: _BGEAdapter):
    logger.info(f"初始化 ChromaDB PersistentClient: {CHROMA_PERSIST_DIR}")
    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR),
    )
    collection_count = vectorstore._collection.count()
    logger.info(f"ChromaDB 集合 '{CHROMA_COLLECTION_NAME}' 当前包含 {collection_count} 条记录")
    return vectorstore


def get_existing_sources(vectorstore: Chroma) -> Set[str]:
    try:
        result = vectorstore._collection.get(include=["metadatas"])
        if not result["metadatas"]:
            return set()
        return {m.get("source", "") for m in result["metadatas"] if m.get("source")}
    except Exception as e:
        logger.warning(f"获取已有 source 列表失败: {e}")
        return set()


def delete_document_vectors(vectorstore: Chroma, source: str) -> int:
    try:
        existing = vectorstore._collection.get(
            where={"source": source}, include=[]
        )
        if existing["ids"]:
            vectorstore._collection.delete(ids=existing["ids"])
            logger.info(f"  已删除旧向量: {source} ({len(existing['ids'])} chunks)")
            return len(existing["ids"])
    except Exception as e:
        logger.warning(f"  删除旧向量失败 {source}: {e}")
    return 0


# ==================== 步骤 4：增量更新 ====================

def create_record_manager():
    logger.info(f"初始化 SQLRecordManager: {RECORD_MANAGER_DB}")
    namespace = f"chromadb/{CHROMA_COLLECTION_NAME}"
    record_manager = SQLRecordManager(namespace=namespace, db_url=RECORD_MANAGER_DB)
    record_manager.create_schema()
    return record_manager


def get_current_sources(documents: List[Document]) -> Set[str]:
    return {doc.metadata.get("source", "") for doc in documents if doc.metadata.get("source")}


def cleanup_orphaned_records(vectorstore: Chroma, record_manager: SQLRecordManager, current_sources: Set[str]):
    all_keys = record_manager.list_keys()
    orphaned_keys = [k for k in all_keys if k not in current_sources]

    if not orphaned_keys:
        return

    logger.info(f"发现 {len(orphaned_keys)} 条孤立记录，正在清理...")
    try:
        vectorstore.delete(ids=orphaned_keys)
    except Exception as e:
        logger.warning(f"删除向量记录时出现部分错误: {e}")

    record_manager.delete_keys(orphaned_keys)
    logger.info(f"已清理 {len(orphaned_keys)} 条孤立记录")


# ==================== 步骤 5：版本管理 ====================

def ensure_user_repo_initialized():
    os.chdir(str(USER_REPO_DIR))
    git_dir = USER_REPO_DIR / ".git"
    if not git_dir.exists():
        logger.info("用户仓库尚未初始化，正在 git init...")
        subprocess.run(["git", "init"], check=True, capture_output=True, text=True)
        logger.info("git init 完成")

    remotes = subprocess.run(
        ["git", "remote"], capture_output=True, text=True,
    ).stdout.strip()
    if "origin" not in remotes:
        logger.info("请手动设置 origin 远程仓库:")
        logger.info("  git remote add origin https://github.com/wmsisme/SillyTavern_RAG.git")


def git_commit_and_push(force: bool = False):
    os.chdir(str(USER_REPO_DIR))
    ensure_user_repo_initialized()

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if not result.stdout.strip() and not force:
        logger.info("没有需要提交的变更")
        return

    now = datetime.now()
    commit_message = (
        f"docs: update RAG index - {now.strftime('%Y-%m-%d %H:%M')}"
    )
    logger.info(f"提交信息: {commit_message}")

    subprocess.run(["git", "add", "."], check=True, capture_output=True, text=True)

    try:
        subprocess.run(
            ["git", "commit", "-m", commit_message, "--allow-empty"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr if isinstance(e.stderr, str) else e.stderr.decode()
        if "nothing to commit" in stderr:
            logger.info("没有可提交的变更")
            return
        raise

    remotes = subprocess.run(
        ["git", "remote"], capture_output=True, text=True,
    ).stdout.strip()
    if "origin" not in remotes:
        logger.warning("未配置 origin 远程仓库，跳过推送")
        logger.warning("请手动执行: git remote add origin <你的仓库URL> && git push -u origin main")
        return

    try:
        subprocess.run(["git", "push"], check=True, capture_output=True, text=True)
        logger.info(f"推送成功: {commit_message}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr if isinstance(e.stderr, str) else e.stderr.decode()
        if "has no upstream branch" in stderr:
            logger.warning("当前分支无上游配置，请手动执行:")
            logger.warning("  git push -u origin main")
        else:
            logger.error(f"推送失败: {stderr}")
            logger.warning("推送失败，本地 commit 已保留，请手动推送")
            raise


# ==================== 主流程 ====================

def run_pipeline(force: bool = False):
    logger.info("=" * 60)
    logger.info("  SillyTavern RAG 知识库自动化索引管道")
    logger.info(f"  启动时间: {datetime.now().isoformat(timespec='seconds')}")
    logger.info(f"  模式: {'强制全量' if force else '增量更新'}")
    logger.info("=" * 60)

    cleanup_old_logs()
    check_disk_space()

    total_new = total_deleted_old = 0
    zh_count = 0

    try:
        # ---- Step 1: 拉取上游更新 ----
        logger.info("[Step 1/5] 拉取上游文档更新...")
        git_setup_upstream()
        changed_files, upstream_updated = git_pull_upstream()
        changed_count = len(changed_files)

        if changed_count == 0 and not upstream_updated and not force:
            logger.info("无变更，管道正常结束")
            return

        if upstream_updated:
            logger.info("[检查] 数据一致性校验...")
            check_data_consistency(DOCS_SOURCE_DIR)

        # ---- Step 2: 确定需要处理的文件 ----
        logger.info("[Step 2/5] 确定需要处理的文档...")

        if force:
            logger.info("强制全量模式：重新加载所有官方文档")
            all_docs = load_markdown_documents(DOCS_SOURCE_DIR)
            to_process = [doc.metadata["source"] for doc in all_docs]
        else:
            to_process = [f for f in changed_files if f.endswith(".md")]

        deleted_files = [f for f in to_process if not (DOCS_SOURCE_DIR / f).exists()]
        modified_files = [f for f in to_process if (DOCS_SOURCE_DIR / f).exists()]

        logger.info(
            f"待处理: {len(modified_files)} 个修改/新增 + "
            f"{len(deleted_files)} 个已删除"
        )

        # ---- Step 3: 仅加载、翻译、切片变更的文件 ----
        logger.info("[Step 3/5] 加载并翻译变更文档...")
        documents = load_specific_markdown_documents(DOCS_SOURCE_DIR, modified_files)

        if documents:
            documents = translate_loaded_documents(documents)
            zh_count = sum(1 for d in documents if d.metadata.get("language") == "zh")
            logger.info(f"翻译结果: {zh_count}/{len(documents)} 篇为中文")

            logger.info("文档切片 (MarkdownHeaderTextSplitter)...")
            new_chunks = split_documents(documents)
            logger.info(f"切片完成: {len(documents)} 个文档 → {len(new_chunks)} 个 chunk")
        else:
            new_chunks = []
            logger.info("没有需要加载的变更文档")

        # ---- Step 4: 向量化与增量更新 ----
        logger.info("[Step 4/5] 初始化 BGE 嵌入模型 & ChromaDB...")
        embeddings = create_embeddings()
        vectorstore = create_vectorstore(embeddings)

        # 4a. 清理已删除文件的旧向量
        for del_file in deleted_files:
            n = delete_document_vectors(vectorstore, del_file)
            total_deleted_old += n

        # 4b. 删旧添新：对每个修改/新增文件，先删旧向量再加新向量
        if new_chunks:
            modified_sources = {c.metadata.get("source", "") for c in new_chunks}
            modified_sources.discard("")

            for src in modified_sources:
                n = delete_document_vectors(vectorstore, src)
                total_deleted_old += n

            logger.info(f"添加 {len(new_chunks)} 个新 chunk 到向量数据库...")
            chunk_ids = [
                c.metadata.get("chunk_id", f"chunk_{i}")
                for i, c in enumerate(new_chunks)
            ]
            vectorstore.add_documents(new_chunks, ids=chunk_ids)
            total_new += len(new_chunks)

        # 4c. 保留非官方知识源（正则表达式），只添加尚未入库的新条目
        logger.info("处理正则表达式知识源...")
        regex_docs = load_regex_documents()
        existing_sources = get_existing_sources(vectorstore)
        new_regex_docs = [
            d for d in regex_docs
            if d.metadata.get("source", "") not in existing_sources
        ]
        regex_skipped = len(regex_docs) - len(new_regex_docs)
        if new_regex_docs:
            logger.info(
                f"发现 {len(new_regex_docs)} 条新正则知识（跳过已有 {regex_skipped} 条），正在添加..."
            )
            regex_ids = [
                d.metadata.get("source", f"regex_{i}")
                for i, d in enumerate(new_regex_docs)
            ]
            vectorstore.add_documents(new_regex_docs, ids=regex_ids)
            total_new += len(new_regex_docs)
        else:
            logger.info(f"正则知识源无新增（已有 {len(regex_docs)} 条全部保留）")

        total_after = vectorstore._collection.count()

        # ---- Step 5: 备份与版本管理 ----
        backup_chromadb()

        logger.info("[Step 5/5] 提交并推送至 Git 仓库...")
        git_commit_and_push(force=force)

        # ---- 总结 ----
        logger.info("=" * 60)
        logger.info("  管道执行完成！")
        logger.info(f"  上游变更 Markdown 文件: {changed_count}")
        logger.info(f"  处理修改/新增文档: {len(modified_files)}")
        logger.info(f"  处理已删除文档: {len(deleted_files)}")
        logger.info(f"  翻译为中文: {zh_count} 篇")
        logger.info(f"  新增向量: {total_new} | 删除旧向量: {total_deleted_old}")
        logger.info(f"  向量库总记录数: {total_after}")
        logger.info(f"  嵌入模型: bge-large-zh-v1.5 (1024维, 纯中文优化)")
        logger.info(f"  日志文件: {LOG_FILE}")
        logger.info("=" * 60)

    except subprocess.CalledProcessError as e:
        stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode() if e.stderr else "")
        logger.error(f"Git 命令执行失败: {stderr}")
        raise
    except RuntimeError:
        logger.exception("管道因资源不足而中止")
        raise
    except Exception:
        logger.exception("管道执行失败")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SillyTavern RAG 知识库自动化索引管道"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制执行完整流程（忽略增量跳过逻辑）",
    )
    args = parser.parse_args()
    run_pipeline(force=args.force)
