import os
from pathlib import Path

# ChromaDB 的遥测在 posthog 版本不匹配时会刷 "capture() takes 1 positional argument" 报错，
# 必须在 import chromadb 之前关掉（Settings 读的就是这个环境变量）。
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
RAG_DIR = ROOT_DIR / "RAG"
TMP_DIR = ROOT_DIR / "tmp"
FRONTEND_DIR = ROOT_DIR / "frontend"

DB_PATH = BACKEND_DIR / "data.db"

CHROMA_DIR = RAG_DIR / "chroma_db"
COLLECTION_NAME = "sillytavern_docs"
DOCS_REPO_DIR = RAG_DIR / "SillyTavern-Docs"
TRANSLATION_CACHE_PATH = RAG_DIR / "translation_cache.json"

# 向量缓存：把整库的 ids/documents/metadatas/embeddings 落盘一份。
# 本机 ChromaDB 的索引无法跨进程复用（每次启动都会判定索引不可用），
# 有了它就能跳过 BGE 向量化，把启动从约 60 秒压到几秒。
VECTOR_CACHE_PATH = RAG_DIR / "vector_cache.npz"
VECTOR_CACHE_META_PATH = RAG_DIR / "vector_cache_meta.json"

REGEX_CHUNKS_DIR = RAG_DIR / "正则表达式" / "rag_chunks"
REGEX_README_PATH = RAG_DIR / "README.md"

# 向量模型：优先用项目内已下载的副本（RAG/bge-large-zh）。
# 原来写死成 "BAAI/bge-large-zh-v1.5"，但 HF 缓存里并没有这个仓库，
# 而加载时用的是 local_files_only=True → 必然抛 LocalEntryNotFoundError。
_LOCAL_EMBEDDING_DIR = RAG_DIR / "bge-large-zh"
EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL_NAME",
    str(_LOCAL_EMBEDDING_DIR)
    if (_LOCAL_EMBEDDING_DIR / "config.json").exists()
    else "BAAI/bge-large-zh-v1.5",
)
RERANKER_MODEL_NAME = os.environ.get("RERANKER_MODEL_NAME", "BAAI/bge-reranker-v2-m3")

# ---- 密钥：只从环境变量 / .env 读，源码里不再写明文 ----
# .env 已在 .gitignore 中，不会被 索引更新.py 的 `git add .` 推到公开仓库。
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:  # 没装 python-dotenv 时退回纯环境变量
    pass

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    print(
        "[config] 警告：未找到 DEEPSEEK_API_KEY —— 请在项目根目录 .env 中填写"
        "（模板见 .env.example），或设为环境变量。翻译/问答/生成功能将不可用。"
    )
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

UPSTREAM_URL = "https://github.com/SillyTavern/SillyTavern-Docs.git"
UPSTREAM_BRANCH = "main"

HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")

TMP_DIR.mkdir(parents=True, exist_ok=True)
