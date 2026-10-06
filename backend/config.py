import os
from pathlib import Path

# ChromaDB 的遥测在 posthog 版本不匹配时会刷 "capture() takes 1 positional argument" 报错，
# 必须在 import chromadb 之前关掉（Settings 读的就是这个环境变量）。
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
TMP_DIR = ROOT_DIR / "tmp"
FRONTEND_DIR = ROOT_DIR / "frontend"
# 数据目录支持环境变量覆盖：容器化部署时把「索引 / 数据库 / 用户图片」挂到卷上，
# 代码与数据分开，升级镜像不会动到用户数据。
RAG_DIR = Path(os.environ.get("RAG_DIR", ROOT_DIR / "RAG"))

# ⚠️ 必须在**任何** os.environ.get 之前加载 .env。
# 原来这段在文件末尾，导致在它之前读的变量（EMBEDDING_MODEL_NAME / EMBED_PROVIDER 等）
# 根本看不到 .env 里的值 —— 只有设成真正的环境变量才生效，属于静默失效的那种坑。
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:  # 没装 python-dotenv 时退回纯环境变量
    pass

DB_PATH = Path(os.environ.get("DB_PATH", BACKEND_DIR / "data.db"))

CHROMA_DIR = RAG_DIR / "chroma_db"
DOCS_REPO_DIR = RAG_DIR / "SillyTavern-Docs"
TRANSLATION_CACHE_PATH = RAG_DIR / "translation_cache.json"

# ---- 向量化 / 精排走哪条路 ----------------------------------------------------
# local       = 本机 RAG/bge-large-zh（老路径，默认，行为与以前完全一致）
# siliconflow = 硅基流动 API 的 BAAI/bge-m3 + bge-reranker-v2-m3（免费档，但要求实名）
#
# ⚠️ 两套模型的向量**不在同一个空间**（实测同一文本余弦仅 0.56–0.63），
# 所以集合名与向量缓存都必须分家 —— 否则新旧向量混进同一个集合，
# 检索会"不报错但静默变差"。分家之后老索引原封不动，随时能把 provider 切回去。
EMBED_PROVIDER = os.environ.get("EMBED_PROVIDER", "local").strip().lower()

SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
SILICONFLOW_EMBED_MODEL = os.environ.get("SILICONFLOW_EMBED_MODEL", "BAAI/bge-m3")
SILICONFLOW_RERANK_MODEL = os.environ.get("SILICONFLOW_RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

if EMBED_PROVIDER == "local":
    COLLECTION_NAME = "sillytavern_docs"
    VECTOR_CACHE_PATH = RAG_DIR / "vector_cache.npz"
    VECTOR_CACHE_META_PATH = RAG_DIR / "vector_cache_meta.json"
else:
    COLLECTION_NAME = f"sillytavern_docs_{EMBED_PROVIDER}"
    VECTOR_CACHE_PATH = RAG_DIR / f"vector_cache_{EMBED_PROVIDER}.npz"
    VECTOR_CACHE_META_PATH = RAG_DIR / f"vector_cache_meta_{EMBED_PROVIDER}.json"

# 换模型时要重建的**源**集合：永远从本机那份全量索引里取文本，别从半成品里取
SOURCE_COLLECTION_NAME = os.environ.get("SOURCE_COLLECTION_NAME", "sillytavern_docs")

REGEX_CHUNKS_DIR = RAG_DIR / "正则表达式" / "rag_chunks"
REGEX_README_PATH = RAG_DIR / "README.md"

# 用户上传的角色卡图片：属于用户数据，不进版本库（.gitignore 已拦）。
# 库里只存 /static/card_images/xxx.png 这样的相对 URL；对外一律走鉴权端点
# /api/cards/{id}/image（挂静态目录是不鉴权的，那等于谁拿到 URL 谁能看）。
STATIC_DIR = Path(os.environ.get("STATIC_DIR", BACKEND_DIR / "static"))
CARD_IMAGE_DIR = STATIC_DIR / "card_images"

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
# 重排序模型：同样本地优先（RAG/bge-reranker-v2-m3，约 2.2GB）。
# 原来只留 HF 仓库名，而 rag_service 根本没加载它 —— 这次接上精排后要有真实路径。
_LOCAL_RERANKER_DIR = RAG_DIR / "bge-reranker-v2-m3"
RERANKER_MODEL_NAME = os.environ.get(
    "RERANKER_MODEL_NAME",
    str(_LOCAL_RERANKER_DIR)
    if (_LOCAL_RERANKER_DIR / "config.json").exists()
    else "BAAI/bge-reranker-v2-m3",
)

# ---- 密钥：只从环境变量 / .env 读，源码里不再写明文 ----
# （.env 的加载已挪到文件顶部，见那里的注释：太晚加载会让前面的变量读不到它）
# .env 已在 .gitignore 中，不会被 索引更新.py 的 `git add .` 推到公开仓库。
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    print(
        "[config] 警告：未找到 DEEPSEEK_API_KEY —— 请在项目根目录 .env 中填写"
        "（模板见 .env.example），或设为环境变量。翻译/问答/生成功能将不可用。"
    )
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# 默认模型：必须用非推理模型。
# 教训（2026-09-24）：原来全项目写的是 deepseek-v4-flash，那是**推理模型**，
# 会把整个 max_tokens 预算烧在隐藏的 reasoning_content 上（实测一篇文档产出
# 27903 字思维链），content 直接返回空串、finish_reason=length。
# 更坑的是它返回 HTTP 200 而不是报错，于是翻译代码的 except 根本不触发，
# 悄悄把英文原文当成"译文"写进了缓存 —— 16 篇新增文档因此一直是英文。
# 实测对照（同一篇 14803 字符的文档）：
#   deepseek-chat      11.6s / 6262 tokens / finish=stop  / 6127 字译文  ← 采用
#   deepseek-v4-flash  29.2s / 11541 tokens / finish=length / 空
#   deepseek-v4-flash(max_tokens=16384) 43.8s / 16244 tokens / 6381 字（贵且慢）
#   deepseek-v4-pro   104.5s / 11594 tokens / finish=length / 空
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

UPSTREAM_URL = "https://github.com/SillyTavern/SillyTavern-Docs.git"
UPSTREAM_BRANCH = "main"

HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")

TMP_DIR.mkdir(parents=True, exist_ok=True)
CARD_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
