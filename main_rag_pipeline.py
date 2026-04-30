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
import subprocess
import logging
import hashlib
import time
import argparse
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, Tuple

from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.indexes._sql_record_manager import SQLRecordManager
from langchain_core.indexing import index

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

EMBEDDING_MODEL_NAME = "maidalun1020/bce-embedding-base_v1"
EMBEDDING_DEVICE = "cpu"

HEADERS_TO_SPLIT_ON = [
    ("#", "H1"),
    ("##", "H2"),
    ("###", "H3"),
]

CHROMA_COLLECTION_NAME = "sillytavern_docs"
RECORD_MANAGER_DB = f"sqlite:///{BASE_DIR / 'record_manager_cache.sql'}"

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


# ==================== 步骤 3：向量化 ====================

def create_embeddings():
    logger.info(f"加载 BCEmbedding 模型: {EMBEDDING_MODEL_NAME}")
    logger.info(f"设备: {EMBEDDING_DEVICE}")
    logger.info("该模型支持中英跨语言检索，英文文档入库后可用中文查询")

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={
            "trust_remote_code": True,
            "device": EMBEDDING_DEVICE,
        },
        encode_kwargs={
            "normalize_embeddings": True,
        },
    )


def create_vectorstore(embeddings: HuggingFaceEmbeddings):
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

    # 前置检查
    cleanup_old_logs()
    check_disk_space()

    added = updated = skipped = deleted = 0
    total_after = 0
    documents = []
    chunks = []

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

        # ---- Step 2: 文档预处理 ----
        logger.info("[Step 2/5] 文档预处理 (MarkdownHeaderTextSplitter)...")
        documents = load_markdown_documents(DOCS_SOURCE_DIR)
        if not documents:
            logger.warning("未找到任何有效 Markdown 文档")
            return

        chunks = split_documents(documents)
        current_sources = get_current_sources(chunks)

        # ---- Step 3: 向量化 ----
        logger.info("[Step 3/5] 初始化 BCEmbedding 嵌入模型 & ChromaDB...")
        embeddings = create_embeddings()
        vectorstore = create_vectorstore(embeddings)

        # ---- Step 4: 增量更新 ----
        logger.info("[Step 4/5] LangChain Indexing API 增量索引...")
        record_manager = create_record_manager()

        index_result = index(
            docs_source=chunks,
            record_manager=record_manager,
            vector_store=vectorstore,
            cleanup="incremental",
            source_id_key="source",
        )

        added = index_result.get("num_added", 0)
        updated = index_result.get("num_updated", 0)
        skipped = index_result.get("num_skipped", 0)
        deleted = index_result.get("num_deleted", 0)

        logger.info(
            f"索引结果: 新增 {added} | 更新 {updated} | "
            f"跳过(未变) {skipped} | 删除(过期) {deleted}"
        )

        total_after = vectorstore._collection.count()
        logger.info(f"向量数据库当前记录数: {total_after}")

        # ChromaDB 大文件备份
        backup_chromadb()

        # ---- Step 5: 版本管理 ----
        logger.info("[Step 5/5] 提交并推送至 Git 仓库...")
        git_commit_and_push(force=force)

        # ---- 总结 ----
        logger.info("=" * 60)
        logger.info("  管道执行完成！")
        logger.info(f"  上游变更 Markdown 文件: {changed_count}")
        logger.info(f"  加载文档数: {len(documents)}")
        logger.info(f"  切片后 chunk 数: {len(chunks)}")
        logger.info(f"  新增/更新/跳过/删除: {added}/{updated}/{skipped}/{deleted}")
        logger.info(f"  向量库总记录数: {total_after}")
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
