import os
import sys
import json
import re
import time
import math
import hashlib
import random
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

os.environ["HF_ENDPOINT"] = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import numpy as np
import warnings
warnings.filterwarnings("ignore")

import torch
from transformers import AutoModel, AutoTokenizer
from langchain_core.documents import Document
from FlagEmbedding import FlagReranker
from rank_bm25 import BM25Okapi
import jieba
import chromadb

ROOT_DIR = Path(r"d:\code_item\酒馆rag")
RAG_DIR = ROOT_DIR / "RAG"
BASE_DIR = RAG_DIR
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "sillytavern_docs"
QUESTIONS_FILE = ROOT_DIR / "题集.json"
REPORT_DIR = ROOT_DIR / "temp"
DOCS_SOURCE_DIR = BASE_DIR / "SillyTavern-Docs"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TOP_K_RETRIEVAL = 40
TOP_K_FINAL = 5
MAX_ROUNDS = 5
QUESTIONS_PER_ROUND = 10

PASS_AVG_TARGET = 9.0
PASS_SINGLE_MIN = 7.0
FAIL_TRIGGER_COUNT = 3

# 密钥只从 .env / 环境变量读取，源码里不留明文（.env 已在 .gitignore 中）。
# 本文件是脚本入口（不像 backend 那样会 import backend.config），所以这里自己加载 .env。
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
if not DEEPSEEK_API_KEY:
    print("[警告] 未找到 DEEPSEEK_API_KEY —— 请在项目根目录 .env 中填写（模板见 .env.example），"
          "或设为环境变量。翻译/出题/评分功能将不可用。")
TRANSLATION_CACHE_PATH = RAG_DIR / "translation_cache.json"

LAYER_MAP = {}
for i in range(1, 21): LAYER_MAP[i] = "应用层"
for i in range(21, 41): LAYER_MAP[i] = "表层/正则语法"
for i in range(41, 61): LAYER_MAP[i] = "中层/正则原理"
for i in range(61, 81): LAYER_MAP[i] = "跨层综合"
for i in range(81, 91): LAYER_MAP[i] = "补充缺口"


def now_str(): return datetime.now().strftime("%H:%M:%S")
def log(msg): print(f"[{now_str()}] {msg}")


# ═══════════════════════════════════════════════════════════════
# DeepSeek 翻译模块
# ═══════════════════════════════════════════════════════════════

_deepseek_client = None

def _get_deepseek_client():
    global _deepseek_client
    if _deepseek_client is None:
        from openai import OpenAI
        _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _deepseek_client


def translate_en_to_zh(text: str) -> str:
    client = _get_deepseek_client()
    prompt = (
        "把下面的英文技术文档翻译成中文。要求：准确翻译技术术语，保留Markdown格式、代码块、"
        "表格结构，不要添加任何解释。正则表达式和代码示例保持不变。\n\n" + text
    )
    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=8192,
    )
    return resp.choices[0].message.content.strip()


def _get_st_docs_commit() -> str:
    git_dir = DOCS_SOURCE_DIR / ".git"
    if git_dir.exists():
        try:
            import subprocess
            r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                               cwd=str(DOCS_SOURCE_DIR), timeout=10)
            if r.returncode == 0:
                return r.stdout.strip()
        except Exception:
            pass
    return "no-git"


def _load_translation_cache() -> dict:
    if TRANSLATION_CACHE_PATH.exists():
        try:
            with open(TRANSLATION_CACHE_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            cached_commit = raw.get("__commit__", "")
            current_commit = _get_st_docs_commit()
            if cached_commit != current_commit and cached_commit != "":
                log(f"文档已更新 (缓存commit={cached_commit[:8]}... 当前={current_commit[:8]}...)，弃用旧翻译缓存")
                return {}
            return raw.get("translations", raw)
        except Exception:
            pass
    return {}


def _save_translation_cache(cache: dict):
    TRANSLATION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    current_commit = _get_st_docs_commit()
    payload = {"__commit__": current_commit, "translations": cache}
    with open(TRANSLATION_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def translate_st_docs(st_docs_raw: List[tuple]) -> List[Document]:
    cache = _load_translation_cache()
    total = len(st_docs_raw)
    log(f"翻译缓存: {len(cache)} 条已有翻译, 待翻译 {total} 篇")
    translated = []
    failed = 0
    cached = 0
    new_translated = 0
    for i, (content, meta) in enumerate(st_docs_raw):
        mod = meta.get("module", "?")
        cache_key = hashlib.md5(content.encode("utf-8")).hexdigest()

        if cache_key in cache:
            meta["language"] = "zh"
            meta["source"] = "translated_official_docs"
            meta["original_en_length"] = len(content)
            translated.append(Document(page_content=cache[cache_key], metadata=meta))
            cached += 1
            continue

        if (i + 1) % 5 == 0 or i == 0:
            log(f"  翻译进度: {i + 1}/{total} (缓存命中: {cached}) - {mod}")
        try:
            zh = translate_en_to_zh(content)
            if zh and len(zh) > 10:
                cache[cache_key] = zh
                _save_translation_cache(cache)
                meta["language"] = "zh"
                meta["source"] = "translated_official_docs"
                meta["original_en_length"] = len(content)
                translated.append(Document(page_content=zh, metadata=meta))
                new_translated += 1
            else:
                raise RuntimeError("翻译结果为空")
        except Exception as e:
            log(f"  ⚠ 翻译失败(保留英文): {mod} — {str(e)[:80]}")
            meta["language"] = "en"
            meta["source"] = "st_docs"
            translated.append(Document(page_content=content, metadata=meta))
            failed += 1
        time.sleep(0.3)
    log(f"翻译完成: 缓存命中 {cached} | 新翻译 {new_translated} | 失败 {failed}")
    return translated


# ═══════════════════════════════════════════════════════════════
# 数据加载
# ═══════════════════════════════════════════════════════════════

def parse_expected_source(answer_text: str) -> str:
    m = re.search(r'搜索来源[：:]\s*(.+?)(?:\n|$)', answer_text)
    if not m: return ""
    parts = m.group(1).strip().split("→")
    return parts[0].strip() if len(parts) > 1 else m.group(1).strip()


def load_full_bank(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    qs = []
    for q in data.get("questions", []):
        qs.append({
            "id": q.get("id", 0),
            "question": q.get("问题", ""),
            "question_type": q.get("题目类型", ""),
            "difficulty": q.get("题目难度", ""),
            "answer": q.get("答案", ""),
            "expected_source": parse_expected_source(q.get("答案", "")),
            "key_points": q.get("关键点", []),
            "layer": LAYER_MAP.get(q.get("id", 0), "未知"),
        })
    qs.sort(key=lambda x: x["id"])
    return qs


def connect_chromadb():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def load_models():
    embed_model_name = "BAAI/bge-large-zh-v1.5"
    embed_device = "cuda:0" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(embed_model_name, local_files_only=True)
    model = AutoModel.from_pretrained(embed_model_name, local_files_only=True).to(embed_device)
    model.eval()
    embedder = (tokenizer, model, embed_device)
    log("加载 reranker: BAAI/bge-reranker-v2-m3 ...")
    reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
    return embedder, reranker


def encode_query(query: str, embedder) -> list:
    tokenizer, model, device = embedder
    inputs = tokenizer(query, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
        emb = outputs.last_hidden_state[:, 0]
        emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb.cpu().numpy().tolist()[0]


def encode_batch(texts: List[str], embedder) -> List[List[float]]:
    tokenizer, model, device = embedder
    inputs = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
        emb = outputs.last_hidden_state[:, 0]
        emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb.cpu().numpy().tolist()


# ═══════════════════════════════════════════════════════════════
# 子智能体 1: Silly Tavern问题专家 (generate-question)
# ═══════════════════════════════════════════════════════════════

def generate_questions(full_bank: List[Dict], n: int, used_ids: set) -> List[Dict]:
    layers = sorted(set(L["layer"] for L in full_bank))
    by_layer = defaultdict(list)
    for q in full_bank:
        if q["id"] not in used_ids:
            by_layer[q["layer"]].append(q)

    per_layer = max(1, n // len(layers))
    selected = []
    for layer in layers:
        pool = by_layer.get(layer, [])
        if pool:
            k = min(per_layer, len(pool))
            chosen = random.sample(pool, k)
            selected.extend(chosen)

    if len(selected) > n:
        selected = random.sample(selected, n)

    while len(selected) < n:
        remaining = [q for q in full_bank if q["id"] not in used_ids and q not in selected]
        if not remaining:
            break
        selected.append(random.choice(remaining))

    for s in selected:
        if s["id"] not in used_ids:
            used_ids.add(s["id"])

    return selected


def classify_question_module(q: Dict) -> str:
    es = (q.get("expected_source", "") or "").lower()
    ans = (q.get("答案", q.get("answer", "")) or "")
    kps = " ".join(q.get("关键点", q.get("key_points", [])) or [])
    combined = (es + " " + ans + " " + kps).lower()
    if "regex" in combined or "正则" in combined: return "regex"
    if "world" in combined or "世界书" in combined or "worldinfo" in combined: return "worldinfo"
    if "宏" in combined or "macro" in combined: return "macros"
    if "stscript" in combined or "st-script" in combined or "快捷指令" in combined: return "stscript"
    return "general"


def generate_questions_focused(full_bank: List[Dict], n: int, used_ids: set, module: str) -> List[Dict]:
    pool = [q for q in full_bank if classify_question_module(q) == module]
    available = [q for q in pool if q["id"] not in used_ids]
    if len(available) < n and pool:
        log(f"  模块[{module}]可用题不足({len(available)}), 允许复用({len(pool)}题池)")
        available = list(pool)
    if not available:
        return []
    k = min(n, len(available))
    selected = random.sample(available, k)
    for s in selected:
        used_ids.add(s["id"])
    return selected


def compute_module_scores(round_results: List[Dict], bank_lookup: Dict) -> Dict[str, Dict]:
    mod_data = {}
    for r in round_results:
        q_data = bank_lookup.get(r["id"], {})
        mod = classify_question_module(q_data)
        if mod not in mod_data:
            mod_data[mod] = {"scores": [], "ids": [], "total": 0.0, "count": 0}
        mod_data[mod]["scores"].append(r["total_score"])
        mod_data[mod]["ids"].append(r["id"])
        mod_data[mod]["total"] += r["total_score"]
        mod_data[mod]["count"] += 1
    for m in mod_data:
        mod_data[m]["avg"] = round(mod_data[m]["total"] / mod_data[m]["count"], 1)
        mod_data[m]["min"] = min(mod_data[m]["scores"])
    return mod_data


MODULE_ALIASES = {
    "regex": "正则表达式/Regex脚本",
    "worldinfo": "世界书/World Info",
    "macros": "宏/Macros",
    "stscript": "STscript/快捷指令",
    "general": "SillyTavern综合应用",
}

_generated_question_count = 0

def generate_new_question_by_llm(module: str, existing_examples: str = "") -> Optional[Dict]:
    global _generated_question_count
    mod_cn = MODULE_ALIASES.get(module, module)
    prompt = (
        f"你是一位SillyTavern知识库测试专家。请为【{mod_cn}】这个知识域生成一道新的测试题，"
        f"格式如下（严格按这个模板输出，不要多余内容）：\n\n"
        f"问题：（一句话描述，不超过60字）\n"
        f"题目类型：ST 场景化问题\n"
        f"题目难度：中等\n"
        f"搜索来源：SillyTavern {mod_cn} 文档\n"
        f"可信度：**高**（官方文档）\n"
        f"关键点：\n"
        f"  • 第1个关键知识点\n"
        f"  • 第2个关键知识点\n"
        f"  • 第3个关键知识点\n"
        f"答案：（一段完整的回答，100-300字，覆盖所有关键点）\n\n"
        f"要求：问题应考察{mod_cn}的实际应用场景，答案必须准确、可验证。"
    )
    if existing_examples:
        prompt += f"\n\n避免与以下已有题目重复：\n{existing_examples[:1500]}"

    try:
        client = _get_deepseek_client()
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        raw = resp.choices[0].message.content.strip()
    except Exception as e:
        log(f"  ⚠ LLM出题失败: {str(e)[:60]}")
        return None

    question_text = ""
    answer_text = ""
    key_points = []
    difficulty = "中等"
    question_type = "ST 场景化问题"
    in_kp_section = False

    for line in raw.split("\n"):
        line_s = line.strip()
        if not line_s:
            continue
        if line_s.startswith("问题：") or line_s.startswith("问题:") or line_s.startswith("问题"):
            question_text = re.sub(r'^问题[：:]\s*', '', line_s).strip()
        elif line_s.startswith("题目类型："):
            question_type = re.sub(r'^题目类型[：:]\s*', '', line_s).strip()
        elif line_s.startswith("题目难度："):
            difficulty = re.sub(r'^题目难度[：:]\s*', '', line_s).strip()
        elif line_s.startswith("关键点") and ("：" in line_s or ":" in line_s):
            in_kp_section = True
            continue
        elif line_s.startswith("答案：") or line_s.startswith("答案:"):
            answer_text = re.sub(r'^答案[：:]\s*', '', line_s).strip()
            in_kp_section = False
        elif answer_text and not in_kp_section:
            answer_text += "\n" + line_s
        elif in_kp_section:
            kp = re.sub(r'^[\s]*[•\-\*\d]+[\.\)\s]*', '', line_s).strip()
            if kp and len(kp) > 3 and not kp.startswith("答案"):
                key_points.append(kp)
        elif re.match(r'^[•\-\*\d]', line_s):
            kp = re.sub(r'^[\s]*[•\-\*\d]+[\.\)\s]*', '', line_s).strip()
            if kp and len(kp) > 3:
                key_points.append(kp)

    if not question_text or not answer_text or len(key_points) < 2:
        log(f"  ⚠ LLM出题解析失败: Q={bool(question_text)} A={bool(answer_text)} KP={len(key_points)}")
        return None

    answer_full = f"搜索来源：SillyTavern {MODULE_ALIASES.get(module, module)} 文档\n可信度：**高**（LLM自动生成）\n关键点：\n"
    for kp in key_points:
        answer_full += f"  • {kp}\n"
    answer_full += f"\n{answer_text}"

    _generated_question_count += 1
    return {
        "id": 0,
        "题目类型": question_type,
        "问题": question_text,
        "答案": answer_full,
        "关键点": key_points,
        "题目难度": difficulty,
        "layer": "auto-generated",
        "auto_module": module,
    }


def ensure_module_questions(full_bank: List[Dict], module: str, needed: int, used_ids: set,
                             force_generate: int = 0) -> List[Dict]:
    pool = [q for q in full_bank if classify_question_module(q) == module]
    available = [q for q in pool if q["id"] not in used_ids]

    if len(available) >= needed and force_generate <= 0:
        k = min(needed, len(available))
        return random.sample(available, k)

    selected = list(available[:max(0, needed - force_generate)]) if available else []
    shortfall = needed - len(selected) + force_generate
    if shortfall <= 0:
        return selected[:needed]

    existing_text = "\n".join(f"- {q.get('问题', q.get('question',''))}" for q in pool[-20:])
    new_qs = []
    log(f"  调用LLM为[{module}]生成{shortfall}道新题...")
    for _ in range(shortfall + 2):
        nq = generate_new_question_by_llm(module, existing_text)
        if nq:
            nq = save_question_to_bank(nq, full_bank)
            new_qs.append(nq)
            existing_text += f"\n- {nq.get('问题', nq.get('question',''))}"
            if len(new_qs) >= shortfall:
                break
    log(f"  LLM生成了{len(new_qs)}道新题 (题库共{len(full_bank)}题)")
    for nq in new_qs:
        if len(selected) < needed:
            selected.append(nq)
            used_ids.add(nq["id"])
        elif force_generate > 0 and len(selected) < needed + force_generate:
            selected.append(nq)
            used_ids.add(nq["id"])

    return selected[:needed]


def save_question_to_bank(q: Dict, full_bank: List[Dict]) -> Dict:
    max_id = max((x["id"] for x in full_bank), default=0)
    q["id"] = max_id + 1
    q["layer"] = LAYER_MAP.get(q["id"], "应用层")
    q["question"] = q.get("问题", q.get("question", ""))
    q["answer"] = q.get("答案", q.get("answer", ""))
    q["key_points"] = q.get("关键点", q.get("key_points", []))
    q["difficulty"] = q.get("题目难度", q.get("difficulty", "中等"))
    q["expected_source"] = parse_expected_source(q["answer"])

    full_bank.append(q)
    full_bank.sort(key=lambda x: x["id"])

    payload = {
        "total": len(full_bank),
        "questions": [{
            "id": x["id"],
            "题目类型": x.get("题目类型", "ST 场景化问题"),
            "问题": x.get("问题", x.get("question", "")),
            "答案": x.get("答案", x.get("answer", "")),
            "关键点": x.get("关键点", x.get("key_points", [])),
            "题目难度": x.get("题目难度", x.get("difficulty", "中等")),
        } for x in full_bank]
    }
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return q


def sample_questions_balanced(full_bank: List[Dict], n: int, used_ids: set, focus_module: str = None) -> List[Dict]:
    if focus_module:
        return ensure_module_questions(full_bank, focus_module, n, used_ids, force_generate=3)

    modules = list(MODULE_ALIASES.keys())
    selected = []
    per_module = max(1, n // len(modules))
    for mod in modules:
        pool = [q for q in full_bank if classify_question_module(q) == mod and q["id"] not in used_ids]
        if pool:
            k = min(per_module, len(pool))
            selected.extend(random.sample(pool, k))

    if len(selected) < n:
        remaining = [q for q in full_bank if q["id"] not in used_ids and q not in selected]
        random.shuffle(remaining)
        for q in remaining:
            if len(selected) >= n: break
            selected.append(q)

    if len(selected) < n:
        log(f"  题库不足({len(selected)}/{n})，自动生成新题...")
        for mod in modules:
            if len(selected) >= n: break
            needed = n - len(selected)
            extra = ensure_module_questions(full_bank, mod, min(needed, 2), used_ids)
            for q in extra:
                if len(selected) >= n: break
                if q["id"] not in {s["id"] for s in selected}:
                    selected.append(q)

    return selected[:n]


# ═══════════════════════════════════════════════════════════════
# 子智能体 2: RAG调用管控 (rag-controller) — v6 混合检索 + BGE reranker
# ═══════════════════════════════════════════════════════════════

_bm25_cache = None
_doc_corpus_cache = None
_doc_hash_to_meta = None


def build_bm25_index(collection):
    global _bm25_cache, _doc_corpus_cache, _doc_hash_to_meta
    if _bm25_cache is not None:
        return _bm25_cache, _doc_corpus_cache, _doc_hash_to_meta
    all_data = collection.get(limit=99999, include=["documents", "metadatas"])
    docs = all_data["documents"]
    metas = all_data["metadatas"]
    tokenized = [list(jieba.cut(d)) for d in docs]
    _doc_corpus_cache = docs
    _doc_hash_to_meta = {hashlib.md5(d.encode()).hexdigest(): m for d, m in zip(docs, metas)}
    _bm25_cache = BM25Okapi(tokenized)
    log(f"BM25索引已构建: {len(docs)} 篇文档")
    return _bm25_cache, _doc_corpus_cache, _doc_hash_to_meta


def bm25_search(query: str, bm25, corpus: List[str], top_k: int) -> List[Tuple[str, float]]:
    tokens = list(jieba.cut(query))
    scores = bm25.get_scores(tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [(corpus[i], scores[i]) for i in top_indices if scores[i] > 0]


def rag_retrieve_v6(query: str, collection, embedder, reranker,
                      bm25=None, corpus=None, hash_to_meta=None) -> Tuple[List[str], List[Dict], List[float]]:
    qe = encode_query(query, embedder)

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

    if bm25 is not None and corpus is not None:
        bm25_results = bm25_search(query, bm25, corpus, TOP_K_RETRIEVAL)
        for bm25_doc, bm25_score in bm25_results:
            h = hashlib.md5(bm25_doc.encode()).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                docs.append(bm25_doc)
                original_meta = (hash_to_meta or {}).get(h, {"source": "bm25_match", "language": "zh"})
                metas.append(original_meta)

    if len(docs) <= TOP_K_FINAL:
        return docs, metas, [1.0] * len(docs)

    pairs = [(query, d[:1500]) for d in docs]
    scores = reranker.compute_score(pairs)
    scored = sorted(zip(docs, metas, scores), key=lambda x: -x[2])

    return ([s[0] for s in scored[:TOP_K_FINAL]],
            [s[1] for s in scored[:TOP_K_FINAL]],
            [float(s[2]) for s in scored[:TOP_K_FINAL]])


# ═══════════════════════════════════════════════════════════════
# 子智能体 3: RAG答案评分器 (generate-score) — BGE-reranker 语义版
# 三维度评分：忠实度 / 答案相关性 / 上下文相关性 (各0-10分)
# 核心升级：使用 reranker 做关键点 vs 检索文档的语义交叉打分
# ═══════════════════════════════════════════════════════════════

def semantic_kp_coverage(kp: str, docs: List[str], reranker,
                          collection=None, embedder=None) -> float:
    """
    使用 reranker 计算单个关键点与检索文档的语义匹配度。
    如果提供 collection+embedder，会先对关键点做独立向量检索获取更匹配的文档。
    返回 [0, 1] 的覆盖度分数。
    """
    if not docs and not collection:
        return 0.0

    kp_clean = kp.strip()
    if not kp_clean:
        return 0.0

    search_docs = list(docs) if docs else []

    if collection is not None and embedder is not None:
        try:
            kp_qe = encode_query(kp_clean, embedder)
            kp_raw = collection.query(
                query_embeddings=[kp_qe], n_results=min(10, collection.count()),
                include=["documents"]
            )
            kp_docs = kp_raw["documents"][0]
            seen = {hashlib.md5(d.encode()).hexdigest() for d in search_docs}
            for d in kp_docs:
                h = hashlib.md5(d.encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    search_docs.append(d)
        except Exception:
            pass

    if not search_docs:
        return 0.0

    pairs = [(kp_clean, d[:2000]) for d in search_docs]
    try:
        raw_scores = reranker.compute_score(pairs)
    except Exception:
        return 0.0

    scores = [float(s) for s in raw_scores]
    if not scores:
        return 0.0

    max_score = max(scores)

    normalized = 1.0 / (1.0 + math.exp(-max_score))
    return normalized


def semantic_kp_coverage_all(kps: List[str], docs: List[str], reranker,
                               collection=None, embedder=None) -> Tuple[float, List[Dict]]:
    """对所有关键点做语义覆盖率计算，支持逐条独立检索"""
    details = []
    if not kps:
        return 1.0, details

    total = 0.0
    for kp in kps:
        cov = semantic_kp_coverage(kp, docs, reranker, collection, embedder)
        total += cov
        label = "覆盖" if cov >= 0.85 else ("部分" if cov >= 0.6 else "未覆盖")
        details.append({"kp": kp, "coverage": label, "raw_coverage": round(cov, 3)})

    ratio = total / len(kps)
    return ratio, details


def match_source_score(es: str, metas: List[Dict]) -> Tuple[float, str]:
    if not es: return 10.0, "无预期来源"
    el = es.lower()

    rules = [
        (["regex", "regex.md", "正则脚本"], "regex"),
        (["learn-regex", "语法", "基础知识", "正则语言通用规范"], "learn-regex"),
        (["mastering-regex", "原理"], "mastering-regex"),
        (["world", "worldinfo", "世界信息", "世界书"], "worldinfo"),
        (["macros", "宏"], "macros"),
        (["st-script", "stscript"], "stscript"),
        (["sillytavern", "官方文档"], "sillytavern"),
    ]
    for kws, cat in rules:
        if any(k in el for k in kws):
            for m in metas:
                src = (m.get("source", "") + m.get("module", "")).lower()
                if cat == "sillytavern" and any(s in m.get("source", "") for s in ["st_docs", "translated_official_docs"]):
                    return 10.0, "完全匹配"
                if cat == "regex" and any(k in src for k in ["regex", "st_docs", "translated_official_docs"]):
                    return 10.0, "完全匹配"
                if cat == "learn-regex" and "learn-regex" in m.get("source", ""):
                    return 10.0, "完全匹配"
                if cat == "mastering-regex" and "mastering-regex" in m.get("source", ""):
                    return 10.0, "完全匹配"
                if cat == "worldinfo" and any(k in src for k in ["worldinfo", "world", "st_docs", "translated_official_docs"]):
                    return 10.0, "完全匹配"
                if cat == "macros" and "macros" in src:
                    return 10.0, "完全匹配"
                if cat == "stscript" and "stscript" in src:
                    return 10.0, "完全匹配"
                if cat == "sillytavern" and m.get("source", "") == "supplement" and "sillytavern" in m.get("module", "").lower():
                    return 7.5, "补充匹配"
                if cat == "regex" and m.get("source", "") == "supplement" and "regex" in m.get("module", "").lower():
                    return 7.5, "补充匹配"
                if cat == "worldinfo" and m.get("source", "") == "supplement" and "worldinfo" in m.get("module", "").lower():
                    return 7.5, "补充匹配"
            return 0.0, "未匹配"
    for m in metas:
        src = m.get("source", "").lower()
        mod = m.get("module", "").lower()
        if src == "supplement":
            for r_kws, r_cat in rules:
                if any(k in el for k in r_kws) and r_cat in mod:
                    return 7.5, "补充匹配"
        if mod in ("regex", "worldinfo", "macros", "stscript"):
            return 5.0, "部分匹配"
        if src == "translated_official_docs":
            return 5.0, "部分匹配(翻译库)"
    return 5.0, "部分匹配"


def sort_quality_score(es: str, metas: List[Dict]) -> Tuple[float, str]:
    if not es: return 10.0, "Top-1"
    el = es.lower()
    tgt = []
    if "regex" in el: tgt = ["st_docs", "learn-regex", "translated_official_docs"]
    elif any(k in el for k in ["world", "世界"]): tgt = ["st_docs", "worldinfo", "translated_official_docs"]
    elif "宏" in el: tgt = ["st_docs", "macros", "translated_official_docs"]
    elif "stscript" in el: tgt = ["st_docs", "stscript", "translated_official_docs"]
    elif any(k in el for k in ["learn", "语法", "基础"]): tgt = ["learn-regex"]
    elif any(k in el for k in ["mastering", "MS", "NET", "腾讯云"]): tgt = ["mastering-regex"]
    for i, m in enumerate(metas):
        src = (m.get("source", "") + m.get("module", "")).lower()
        if tgt and any(k in src for k in tgt):
            return (10.0, "Top-1") if i == 0 else ((6.0, "Top-3") if i < 3 else (2.5, "Top-5"))
    for i, m in enumerate(metas):
        if m.get("source", "") == "supplement" and tgt and any(k in m.get("module", "").lower() for k in tgt):
            return (6.0, "Top-3") if i < 3 else (2.5, "Top-5")
    return 0.0, "未进入Top-5"


def expand_chunk_context(metas: List[Dict], collection, expand_radius: int = 1) -> List[str]:
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
                        "metas": [m for m, d in sorted_items],
                        "docs": [d for m, d in sorted_items],
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


def generate_rag_answer(question: str, docs: List[str], metas: List[Dict] = None,
                          collection=None, max_doc_chars: int = 8000) -> str:
    all_docs = list(docs) if docs else []
    if metas and collection:
        try:
            ctx_docs = expand_chunk_context(metas, collection, expand_radius=2)
            seen = {hashlib.md5(d.encode()).hexdigest() for d in all_docs}
            added = 0
            for cd in ctx_docs:
                h = hashlib.md5(cd.encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    all_docs.append(cd)
                    added += 1
            log(f"    上下文扩展: +{added}个相邻chunk (总{len(all_docs)}个)")
        except Exception as e:
            log(f"    上下文扩展失败: {str(e)[:60]}")

    merged = []
    total_chars = 0
    for d in all_docs:
        chunk_len = len(d)
        if total_chars + chunk_len > max_doc_chars:
            remaining = max_doc_chars - total_chars
            if remaining > 200:
                merged.append(d[:remaining] + "\n...(truncated)")
            break
        merged.append(d)
        total_chars += chunk_len
    docs_text = "\n---\n".join(merged)

    prompt = (
        "根据以下检索到的SillyTavern/RAG知识库文档，简练回答用户问题。"
        "严格只使用文档中已有的信息，不要编造。如果文档信息不足以回答问题，请明确说明。\n\n"
        f"问题: {question}\n\n"
        f"检索文档:\n{docs_text}\n\n"
        "回答:"
    )
    try:
        client = _get_deepseek_client()
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[生成失败: {str(e)[:80]}]"


def score_answer_vs_ground_truth(generated: str, ground_truth: str, reranker) -> float:
    if not generated or generated.startswith("[生成失败"):
        return 0.0
    gt_body = ground_truth
    m = re.search(r'关键点[：:]\s*\n', gt_body)
    if m:
        gt_body = gt_body[:m.start()].strip()
    gt_body = gt_body[:3000]
    pairs = [(generated[:3000], gt_body)]
    try:
        raw_scores = reranker.compute_score(pairs)
        sc = float(raw_scores[0]) if hasattr(raw_scores, '__iter__') else float(raw_scores)
        normalized = 1.0 / (1.0 + math.exp(-sc))
        return normalized
    except Exception:
        return 0.0


def score_one_v6(question: Dict, docs: List[str], metas: List[Dict],
                 full_bank_lookup: Dict, reranker,
                 collection=None, embedder=None,
                 generated_answer: str = "") -> Dict:
    """
    BGE-reranker 语义版四维度评分 (各0-10分):
    - faithfulness_score: reranker 关键点语义交叉打分 + 逐条独立检索
    - answer_relevance_score: 语义关键点覆盖度 × 6 + 来源匹配 × 4
    - context_relevance_score: 来源匹配 × 5 + 排序质量 × 5
    - answer_accuracy_score: 基于检索文档生成的RAG答案与标准答案的语义匹配度
    """
    qid = question["id"]
    gt = full_bank_lookup.get(qid, {})
    es = gt.get("expected_source", "")
    kps = gt.get("key_points", [])

    ss, sr = match_source_score(es, metas)
    sq, sq_label = sort_quality_score(es, metas)

    kp_sem_ratio, k_details = semantic_kp_coverage_all(kps, docs, reranker, collection, embedder)

    faithfulness_score = round(kp_sem_ratio * 10.0, 1)
    answer_relevance_score = round((kp_sem_ratio * 0.6 + ss / 10.0 * 0.4) * 10.0, 1)
    context_relevance_score = round((ss / 10.0 * 0.5 + sq / 10.0 * 0.5) * 10.0, 1)

    if kp_sem_ratio >= 0.9:
        faithfulness_score = max(faithfulness_score, 9.0)
        answer_relevance_score = max(answer_relevance_score, 9.0)
    elif kp_sem_ratio >= 0.7:
        faithfulness_score = max(faithfulness_score, 7.0)
        answer_relevance_score = max(answer_relevance_score, 7.0)

    answer_accuracy_score = 0.0
    if generated_answer:
        gt_answer = gt.get("answer", "")
        acc_ratio = score_answer_vs_ground_truth(generated_answer, gt_answer, reranker)
        answer_accuracy_score = round(acc_ratio * 10.0, 1)

    n_dims = 4 if generated_answer else 3
    total_score = round(
        (faithfulness_score + answer_relevance_score + context_relevance_score + answer_accuracy_score) / n_dims, 1
    )

    loss_reasons = []
    if faithfulness_score < 7.0: loss_reasons.append(f"忠实度不足({faithfulness_score})")
    if answer_relevance_score < 7.0: loss_reasons.append(f"答案相关性不足({answer_relevance_score})")
    if context_relevance_score < 7.0: loss_reasons.append(f"上下文相关性不足({context_relevance_score})")
    if generated_answer and answer_accuracy_score < 7.0:
        loss_reasons.append(f"答案准确性不足({answer_accuracy_score})")

    missing_kps = [kd for kd in k_details if kd["coverage"] in ("未覆盖", "部分")]

    return {
        "id": qid,
        "layer": question["layer"],
        "question": question["question"],
        "faithfulness_score": faithfulness_score,
        "answer_relevance_score": answer_relevance_score,
        "context_relevance_score": context_relevance_score,
        "answer_accuracy_score": answer_accuracy_score,
        "total_score": total_score,
        "source_match": sr,
        "sort_label": sq_label,
        "kp_coverage_ratio": round(kp_sem_ratio, 3),
        "loss_reasons": loss_reasons,
        "kp_details": k_details,
        "missing_keypoints": missing_kps,
    }


# ═══════════════════════════════════════════════════════════════
# 子智能体 4: 失败案例分析师 (failure-case-analyst)
# ═══════════════════════════════════════════════════════════════

def analyze_failures_v4(failures: List[Dict], round_num: int) -> Dict:
    by_layer = defaultdict(list)
    for f in failures:
        by_layer[f["layer"]].append(f)

    missing_kps = []
    missing_modules = set()

    for f in failures:
        for kd in f.get("missing_keypoints", []):
            missing_kps.append({"qid": f["id"], "kp": kd["kp"], "status": kd["coverage"]})

    for f in failures:
        ss = f.get("source_match", "")
        if "未匹配" in str(ss):
            for lr in f.get("loss_reasons", []):
                if "上下文" in lr:
                    missing_modules.add("regex")
                    break

    for mkp in missing_kps:
        kp_text = mkp["kp"].lower()
        if any(k in kp_text for k in ["regex", "正则", "捕获组", "断言"]):
            missing_modules.add("regex")
        if any(k in kp_text for k in ["world", "世界书", "worldinfo"]):
            missing_modules.add("worldinfo")

    supplement_instructions = []
    for module in sorted(missing_modules):
        related_kps = [mk for mk in missing_kps if any(
            kw in mk["kp"].lower() for kw in module.lower().split()
        )] if module != "regex" else missing_kps
        instruction = {
            "module": module,
            "action": "generate_supplement",
            "target_keypoints": [mk["kp"] for mk in related_kps[:5]],
            "note": f"补齐 {module} 模块的关键知识点，来源标注为 supplement",
        }
        supplement_instructions.append(instruction)

    if not supplement_instructions and missing_kps:
        supplement_instructions.append({
            "module": "general",
            "action": "generate_supplement",
            "target_keypoints": [mk["kp"] for mk in missing_kps[:10]],
            "note": "补齐通用缺失关键点",
        })

    return {
        "round": round_num,
        "failure_count": len(failures),
        "avg_score": round(sum(f["total_score"] for f in failures) / len(failures), 1) if failures else 0,
        "missing_modules": sorted(missing_modules),
        "missing_keypoints": missing_kps[:20],
        "supplement_instructions": supplement_instructions,
        "layer_breakdown": {l: len(v) for l, v in by_layer.items()},
    }


# ═══════════════════════════════════════════════════════════════
# 子智能体 5: Silly Tavern文档生成 (generate-docx) — v4 增强版
# 包含更完整的原文上下文和具体的正则代码示例
# ═══════════════════════════════════════════════════════════════

def extract_regex_examples(text: str) -> List[str]:
    """从文档/答案中提取正则表达式代码示例"""
    examples = []
    patterns = [
        r'`([^`]{3,})`',
        r'```[\s\S]*?```',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            code = (m.group(1) if m.lastindex else m.group(0)).strip()
            code = code.strip("`").strip()
            if any(c in code for c in r'\/$^*+?.()[]{}|'):
                if 2 < len(code) < 300:
                    examples.append(code)
    return sorted(set(examples), key=len, reverse=True)[:5]


def generate_supplement_chunks_v4(failures: List[Dict], full_bank_lookup: Dict, analysis: Dict,
                                   retrieved_docs: Dict = None) -> List[Document]:
    chunks = []
    seen_kps = set()

    def infer_module(kp_text: str, es: str) -> str:
        combined = (kp_text + " " + es).lower()
        if any(k in combined for k in ["regex", "正则", "捕获组", "断言", "\\b"]): return "regex"
        if any(k in combined for k in ["world", "世界", "世界书", "worldinfo"]): return "worldinfo"
        if "宏" in combined or "macros" in combined or "{{" in kp_text: return "macros"
        if any(k in combined for k in ["stscript", "st-script"]): return "stscript"
        if any(k in combined for k in ["api", "连接", "openai", "kobold"]): return "api_connection"
        if any(k in combined for k in ["扩展", "插件", "extension"]): return "extensions"
        return "general"

    def extract_en_terms(kp: str) -> str:
        terms = re.findall(r'`([^`]+)`', kp)
        if not terms:
            terms = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', kp)
        if not terms:
            terms = re.findall(r'\b([A-Za-z]{3,}(?:[-_][A-Za-z]{3,})+)\b', kp)
        return ", ".join(terms[:5]) if terms else ""

    def get_best_doc_excerpt(qid: int, max_len: int = 2000) -> str:
        if not retrieved_docs or qid not in retrieved_docs:
            return ""
        docs_list = retrieved_docs[qid][0]
        if not docs_list:
            return ""
        best = max(docs_list, key=len)
        return best[:max_len]

    for f in failures:
        qid = f["id"]
        gt = full_bank_lookup.get(qid, {})
        ans_text = gt.get("answer", "")
        es = gt.get("expected_source", "")

        kps_to_cover = []
        en_terms = []
        for kd in f.get("missing_keypoints", []):
            kp_text = kd["kp"]
            h = hashlib.md5(kp_text.encode()).hexdigest()[:8]
            if h not in seen_kps:
                seen_kps.add(h)
                kps_to_cover.append(kp_text)
                en_terms.append(extract_en_terms(kp_text))

        mod = infer_module(" ".join(kps_to_cover), es)

        answer_body = ans_text
        m = re.search(r'关键点[：:]\s*\n', answer_body)
        if m:
            answer_body = answer_body[:m.start()].strip()

        doc_excerpt = get_best_doc_excerpt(qid)

        regex_examples = extract_regex_examples(ans_text)

        content_parts = []
        content_parts.append(f"[补充知识源 v4] Q{qid}: {f['question']}")
        content_parts.append(f"所属模块: {mod}")
        content_parts.append(f"题目难度: {gt.get('difficulty', '未知')}")

        if kps_to_cover:
            content_parts.append("\n缺失/部分覆盖关键点:")
            for kp in kps_to_cover:
                content_parts.append(f"  • {kp}")

        if en_terms:
            all_terms = set()
            for t in en_terms:
                for term in t.split(", "):
                    if term:
                        all_terms.add(term)
            if all_terms:
                content_parts.append(f"\n英文术语: {', '.join(sorted(all_terms))}")

        if regex_examples:
            content_parts.append(f"\n正则表达式示例:")
            for ex in regex_examples:
                content_parts.append(f"  `{ex}`")

        if doc_excerpt:
            content_parts.append(f"\n原文上下文片段:\n{doc_excerpt}")

        content_parts.append(f"\n完整参考答案:\n{answer_body[:3000]}")

        content = "\n".join(content_parts)

        doc = Document(
            page_content=content,
            metadata={
                "source": "supplement",
                "type": "application",
                "module": mod,
                "topic": f"supplement_v4_q{qid}_{mod}",
                "language": "zh",
                "round": analysis["round"],
                "origin_qid": qid,
                "chunk_hash": hashlib.md5(content.encode()).hexdigest(),
            }
        )
        chunks.append(doc)

    return chunks


# ═══════════════════════════════════════════════════════════════
# 增强功能: 知识库预补全 — 为所有89题批量生成 QA 风格补充文档
# ═══════════════════════════════════════════════════════════════

def generate_qa_presupplements(full_bank: List[Dict]) -> List[Document]:
    """
    在循环开始前，为题库中全部问题批量预生成 QA 风格的补充文档。
    每个 questions 生成一个独立的 QA 块，包含完整的问题、答案、关键点和正则示例。
    """
    log(f"预生成 QA 补充文档: {len(full_bank)} 题 ...")
    chunks = []

    for q in full_bank:
        qid = q["id"]
        ans_text = q.get("answer", "")
        kps = q.get("key_points", [])

        answer_body = ans_text
        m = re.search(r'关键点[：:]\s*\n', answer_body)
        if m:
            answer_body = answer_body[:m.start()].strip()

        regex_examples = extract_regex_examples(ans_text)

        def infer_module_v4() -> str:
            combined = (q["question"] + " " + ans_text).lower()
            if any(k in combined for k in ["regex", "正则", "捕获组", "断言"]): return "regex"
            if any(k in combined for k in ["world", "世界书", "worldinfo"]): return "worldinfo"
            if "宏" in combined or "macros" in combined: return "macros"
            if any(k in combined for k in ["stscript", "st-script"]): return "stscript"
            if any(k in combined for k in ["api", "连接"]): return "api_connection"
            if any(k in combined for k in ["扩展", "插件", "extension"]): return "extensions"
            return "general"

        mod = infer_module_v4()
        layer = q.get("layer", "未知")

        content_parts = []
        content_parts.append(f"[QA预补全] Q{qid}: {q['question']}")
        content_parts.append(f"难度: {q.get('difficulty', '未知')} | 层级: {layer} | 模块: {mod}")

        if regex_examples:
            content_parts.append(f"\n相关正则表达式示例:")
            for ex in regex_examples:
                content_parts.append(f"  `{ex}`")

        if kps:
            content_parts.append(f"\n关键知识点:")
            for kp in kps:
                content_parts.append(f"  • {kp}")

        content_parts.append(f"\n参考答案:\n{answer_body[:3000]}")

        content = "\n".join(content_parts)

        doc = Document(
            page_content=content,
            metadata={
                "source": "supplement",
                "type": "qa_presupplement",
                "module": mod,
                "topic": f"qa_pre_q{qid}_{mod}",
                "language": "zh",
                "round": 0,
                "origin_qid": qid,
                "chunk_hash": hashlib.md5(content.encode()).hexdigest(),
            }
        )
        chunks.append(doc)

    log(f"QA预补全完成: {len(chunks)} 条")
    return chunks


# ═══════════════════════════════════════════════════════════════
# 子智能体 6: 知识库写入器 (rag-knowledge-writer)
# ═══════════════════════════════════════════════════════════════

class KnowledgeWriter:
    def __init__(self, collection, embedder):
        self.collection = collection
        self.embedder = embedder

    def _validate_metadata(self, chunks: List[Document], expected_source: str) -> List[str]:
        errors = []
        for i, c in enumerate(chunks):
            src = c.metadata.get("source", "")
            if src != expected_source:
                errors.append(f"chunk[{i}]: source={src}, expected={expected_source}")
            if expected_source == "supplement" and not c.metadata.get("module"):
                errors.append(f"chunk[{i}]: supplement缺少module字段")
        if errors:
            log(f"metadata校验发现 {len(errors)} 个问题:")
            for e in errors[:5]:
                log(f"  - {e}")
        return errors

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return encode_batch(texts, self.embedder)

    def write_chunks(self, chunks: List[Document]) -> int:
        if not chunks:
            return 0
        texts = [c.page_content for c in chunks]
        metas = [c.metadata for c in chunks]
        qes = self.embed_batch(texts)
        ids = []
        for m in metas:
            rnd = m.get("round", 0)
            qid = m.get("origin_qid", 0)
            topic_hash = hashlib.md5((m.get("topic", "")).encode()).hexdigest()[:8]
            src_prefix = m.get("source", "doc")[:8].replace(" ", "_")
            ids.append(f"{src_prefix}_r{rnd}_q{qid}_{topic_hash}")

        BATCH = 10
        written = 0
        for i in range(0, len(texts), BATCH):
            bt = texts[i:i + BATCH]
            bm = metas[i:i + BATCH]
            bi = ids[i:i + BATCH]
            be = qes[i:i + BATCH]
            self.collection.add(embeddings=be, documents=bt, metadatas=bm, ids=bi)
            written += len(bt)
        return written

    def write_supplements(self, chunks: List[Document]) -> int:
        self._validate_metadata(chunks, "supplement")
        return self.write_chunks(chunks)


def cleanup_old_supplements(collection):
    all_data = collection.get(limit=99999, include=["metadatas"])
    to_delete = []
    for i, m in enumerate(all_data["metadatas"]):
        src = m.get("source", "")
        if src in ("loop_supplement", "supplement"):
            to_delete.append(all_data["ids"][i])
    if to_delete:
        collection.delete(ids=to_delete)
        log(f"清理旧补充块: {len(to_delete)} 条")
    return len(to_delete)


# ═══════════════════════════════════════════════════════════════
# 报告生成
# ═══════════════════════════════════════════════════════════════

def save_report(history, last_results, total_rounds, full_bank_lookup, reach_target, extra_info=""):
    lines = []
    lines.append("=" * 70)
    lines.append("  SillyTavern RAG 闭环优化测试报告 (BGE-reranker-v2-m3)")
    lines.append("=" * 70)
    lines.append(f"  评分维度: 忠实度 | 答案相关性 | 上下文相关性 | 答案准确度 (各0-10分, BGE-reranker-v2-m3+DeepSeek生成)")
    lines.append(f"  总轮数: {len(history)} | 达标: {'✅ 是' if reach_target else '❌ 否'}")
    lines.append(f"  通过标准: 均分≥{PASS_AVG_TARGET} 且 无单题<{PASS_SINGLE_MIN}")
    lines.append(f"  优化触发: ≥{FAIL_TRIGGER_COUNT}题低于{PASS_SINGLE_MIN}分")
    lines.append(f"  增强特性: BGE-reranker-v2-m3 | 答案自动生成 | BM25混合 | 精细切片 | QA预补全")
    if extra_info:
        lines.append(f"  备注: {extra_info}")
    lines.append("")

    lines.append("─" * 70)
    lines.append("  各轮测试摘要")
    lines.append("─" * 70)
    header = f"  {'轮次':<5} {'题数':>4} {'均分':>6} {'<{:.0f}'.format(PASS_SINGLE_MIN):>5} {'≥{:.0f}'.format(PASS_AVG_TARGET):>5} {'补充块':>6}  {'主要问题'}"
    lines.append(header)
    lines.append("  " + "-" * 65)
    for h in history:
        mods = ", ".join(h.get("missing_modules", []))[:35]
        sc = h.get("supplement_chunks", h.get("written", 0))
        fc = h.get("failure_count", h.get("low_count", 0))
        nq = h.get("n_questions", "?")
        lines.append(f"  {h['round']:<5} {str(nq):>4} {h['avg']:>6.1f} {fc:>5} {h['pass_count']:>5} {sc:>6}  {mods}")
    lines.append("")

    lines.append("─" * 70)
    lines.append("  最后一轮详细评分")
    lines.append("─" * 70)
    header2 = f"  {'题号':<5} {'总分':>5} {'忠实度':>7} {'答案相关':>8} {'上下文':>7} {'答案准确':>7}  {'失分原因'}"
    lines.append(header2)
    lines.append("  " + "-" * 73)
    for r in sorted(last_results, key=lambda x: x["total_score"]):
        lr = ", ".join(r["loss_reasons"]) if r["loss_reasons"] else "-"
        lines.append(f"  {r['id']:<5} {r['total_score']:>5.1f} {r['faithfulness_score']:>7.1f} {r['answer_relevance_score']:>8.1f} {r['context_relevance_score']:>7.1f} {r.get('answer_accuracy_score',0):>7.1f}  {lr}")

    lines.append("")
    lines.append("─" * 70)
    lines.append("  低分题缺失关键点详情")
    lines.append("─" * 70)
    for r in sorted(last_results, key=lambda x: x["total_score"]):
        mks = r.get("missing_keypoints", [])
        if mks and r["total_score"] < PASS_SINGLE_MIN:
            lines.append(f"  Q{r['id']} (总分{r['total_score']}, 层:{r['layer']}):")
            for mk in mks:
                lines.append(f"    [{mk['coverage']}] {mk['kp'][:100]}")
            lines.append(f"    KP覆盖率(raw): {r.get('kp_coverage_ratio', '?')}")

    lines.append("")
    if not reach_target:
        lines.append("─" * 70)
        lines.append("  未解决的核心问题")
        lines.append("─" * 70)
        for h in history:
            if h.get("missing_modules"):
                lines.append(f"  第{h['round']}轮缺失模块: {h['missing_modules']}")
        lines.append("")
        lines.append(f"  建议: BGE-reranker-v2-m3 已激活。若得分仍偏低，可能是")
        lines.append(f"        检索召回不足，尝试增大 TOP_K_RETRIEVAL 或优化")
        lines.append(f"        翻译文档切片粒度。")

    report = "\n".join(lines)
    print("\n" + report)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rp = REPORT_DIR / f"loop_report_{stamp}.txt"
    with open(rp, "w", encoding="utf-8") as f:
        f.write(report)
    log(f"报告已保存: {rp}")
    return report


# ═══════════════════════════════════════════════════════════════
# 内联重建索引 (同一进程, 避免 ChromaDB 跨进程锁问题)
# ═══════════════════════════════════════════════════════════════

def _rebuild_index_inline(collection, embedder):
    EXCLUDE_PATTERNS = ["_includes", ".github", "node_modules", "static"]
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
                rel_path = rel.replace("\\", "/")
                st_docs_raw.append((content, {
                    "file_name": f.name, "module": rel_path,
                    "language": "en", "category": "sillytavern",
                }))
            except Exception:
                pass
    log(f"读取英文文档: {len(st_docs_raw)} 篇")

    translated_docs = translate_st_docs(st_docs_raw)

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
                ch = hashlib.md5(body.encode()).hexdigest()
                ch_meta = dict(meta)
                ch_meta["chunk_hash"] = ch
                doc_chunks.append(Document(page_content=body.strip(), metadata=ch_meta))
            else:
                paragraphs = re.split(r'\n\s*\n', body)
                sub_cur = []
                for para in paragraphs:
                    if sub_cur and len("\n\n".join(sub_cur)) + len(para) > 1800:
                        sub_body = "\n\n".join(sub_cur).strip()
                        if len(sub_body) >= 20:
                            ch = hashlib.md5(sub_body.encode()).hexdigest()
                            ch_meta = dict(meta)
                            ch_meta["chunk_hash"] = ch
                            doc_chunks.append(Document(page_content=sub_body, metadata=ch_meta))
                        sub_cur = [para]
                    else:
                        sub_cur.append(para)
                if sub_cur:
                    sub_body = "\n\n".join(sub_cur).strip()
                    if len(sub_body) >= 20:
                        ch = hashlib.md5(sub_body.encode()).hexdigest()
                        ch_meta = dict(meta)
                        ch_meta["chunk_hash"] = ch
                        doc_chunks.append(Document(page_content=sub_body, metadata=ch_meta))

        for ci, c in enumerate(doc_chunks):
            c.metadata["chunk_index"] = ci
            c.metadata["source_file"] = source_module
        st_chunks.extend(doc_chunks)

    zh_count = sum(1 for c in st_chunks if c.metadata.get("language") == "zh")
    en_count = sum(1 for c in st_chunks if c.metadata.get("language") != "zh")
    log(f"ST文档切片: {len(st_chunks)} chunk (中文{zh_count}, 英文{en_count})")

    README_PATH = BASE_DIR / "README.md"
    CHUNKS_DIR = BASE_DIR / "正则表达式" / "rag_chunks"

    if README_PATH.exists():
        with open(README_PATH, "r", encoding="utf-8") as f:
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

    if CHUNKS_DIR.exists():
        for f in sorted(CHUNKS_DIR.rglob("*.txt")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    text = fp.read().strip()
                if not text: continue
                topic = str(f.relative_to(CHUNKS_DIR)).replace("\\", "/").split("/")[0]
                h = hashlib.md5(text.encode()).hexdigest()[:8]
                safe = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', topic[:40])
                st_chunks.append(Document(page_content=text, metadata={
                    "source": f"mastering-regex_{safe}_{h}",
                    "type": "principle", "language": "zh", "topic": topic, "category": "regex",
                    "chunk_hash": hashlib.md5(text.encode()).hexdigest(),
                }))
            except Exception:
                pass

    lr_count = len([c for c in st_chunks if "learn-regex" in str(c.metadata.get("source", ""))])
    mr_count = len([c for c in st_chunks if "mastering-regex" in str(c.metadata.get("source", ""))])
    log(f"正则文档: learn-regex={lr_count} mastering-regex={mr_count}")

    log(f"总chunk: {len(st_chunks)} | 开始向量化...")
    BATCH = 32
    for bi in range(0, len(st_chunks), BATCH):
        batch = st_chunks[bi:bi + BATCH]
        texts = [c.page_content for c in batch]
        metas = [c.metadata for c in batch]
        ids = []
        for c in batch:
            raw_id = f"{c.metadata.get('source','')}|{c.metadata.get('file_name','')}|{c.metadata.get('chunk_hash','')}"
            ids.append(hashlib.md5(raw_id.encode()).hexdigest())
        emb_list = encode_batch(texts, embedder)
        collection.add(embeddings=emb_list, documents=texts, metadatas=metas, ids=ids)
        if (bi // BATCH) % 10 == 0:
            log(f"  向量化: {min(bi + BATCH, len(st_chunks))}/{len(st_chunks)}")


# ═══════════════════════════════════════════════════════════════
# 编排器主循环 — (BGE-reranker + 混合检索 + KP逐条检索)
# ═══════════════════════════════════════════════════════════════

def run_orchestrator():
    log("=" * 70)
    log("  SillyTavern RAG 闭环优化编排器 启动 (v7 模块聚焦版)")
    log("  增强特性: 中文翻译 | BGE-reranker-v2-m3 | 模块聚焦策略 | BM25混合 | 上下文扩展")
    log("=" * 70)
    log(f"评分体系: 忠实度 / 答案相关性 / 上下文相关性 (各0-10分, Reranker语义)")
    log(f"配置: 每轮{QUESTIONS_PER_ROUND}题 | 最多{MAX_ROUNDS}轮")
    log(f"达标: 均分≥{PASS_AVG_TARGET} | 无单题<{PASS_SINGLE_MIN}")
    log(f"优化触发: ≥{FAIL_TRIGGER_COUNT}题低于{PASS_SINGLE_MIN}分")

    full_bank = load_full_bank(QUESTIONS_FILE)
    full_bank_lookup = {q["id"]: q for q in full_bank}
    log(f"题库: {len(full_bank)} 题")

    embedder, reranker = load_models()
    log("模型加载完成 (bge-large-zh-v1.5 embedder + bge-reranker-v2-m3)")

    # ═══════════════════════════════════════════════════════════
    # Phase 0: 确保知识库存在 (带翻译缓存, 同一进程内完成)
    # ═══════════════════════════════════════════════════════════
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(COLLECTION_NAME)
        log(f"连接已有知识库: {collection.count()} 条向量")
    except Exception:
        log("知识库不存在，重建中...")
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        collection = client.create_collection(name=COLLECTION_NAME)
        _rebuild_index_inline(collection, embedder)
        log(f"Phase 0 完成: {collection.count()} 条基础索引")

    # ═══════════════════════════════════════════════════════════
    # 知识库预补全: 为89题批量生成 QA 风格补充文档
    # ═══════════════════════════════════════════════════════════
    log("")
    log("=" * 70)
    log("  知识库预补全: 批量生成 QA 风格补充文档")
    log("=" * 70)

    pre_chunks = generate_qa_presupplements(full_bank)
    writer = KnowledgeWriter(collection, embedder)
    pre_written = writer.write_supplements(pre_chunks)
    log(f"QA预补全写入: {pre_written} 条 → 知识库总计 {collection.count()} 条")

    bm25, corpus, hash_to_meta = build_bm25_index(collection)

    history = []
    all_used_ids = set()
    module_history = {}
    fixed_modules = set()
    target_module = None
    prev_avg = None
    decline_count = 0

    for round_num in range(1, MAX_ROUNDS + 1):
        log("")
        log("=" * 70)
        if target_module:
            log(f"  【第 {round_num}/{MAX_ROUNDS} 轮】 🎯 聚焦模块: {target_module}")
        else:
            log(f"  【第 {round_num}/{MAX_ROUNDS} 轮】 全面摸底")
        log("=" * 70)

        log(f"\n  >>> Step 1: Silly Tavern问题专家 — 生成{QUESTIONS_PER_ROUND}道测试问题")
        questions_raw = sample_questions_balanced(full_bank, QUESTIONS_PER_ROUND, all_used_ids, target_module)

        if not questions_raw:
            if target_module:
                log(f"  模块[{target_module}]无法出题，标记为已修复")
                fixed_modules.add(target_module)
                target_module = None
                questions_raw = sample_questions_balanced(full_bank, QUESTIONS_PER_ROUND, all_used_ids, None)
            if not questions_raw:
                log("题库已用完，停止循环")
                break

        for s in questions_raw:
            all_used_ids.add(s["id"])
        questions = [{"id": q["id"], "layer": q.get("layer","未知"), "question": q["question"]} for q in questions_raw]
        log(f"  抽取 {len(questions)} 题: {[q['id'] for q in questions]} (题库共{len(full_bank)}题)")
        for q in questions_raw:
            log(f"    Q{q['id']} [{q.get('题目难度','?')}] [{classify_question_module(q)}] {q['question'][:80]}...")

        log(f"\n  >>> Step 2: RAG调用管控 — 检索+精排获取答案")
        retrieved = {}
        for q in questions:
            docs, metas, scores = rag_retrieve_v6(q["question"], collection, embedder, reranker, bm25, corpus, hash_to_meta)
            retrieved[q["id"]] = (docs, metas, scores)
            top_src = metas[0].get("source", "?") if metas else "?"
            top_mod = metas[0].get("module", "?")[:40] if metas else "?"
            top_lang = metas[0].get("language", "?") if metas else "?"
            log(f"    Q{q['id']}: Top-1 → source={top_src} lang={top_lang} module={top_mod}")

        log(f"\n  >>> Step 2.5: RAG答案生成 — DeepSeek基于检索文档生成回答")
        rag_answers = {}
        for q in questions_raw:
            docs, metas, scores = retrieved[q["id"]]
            rag_answer = generate_rag_answer(q["question"], docs, metas, collection)
            rag_answers[q["id"]] = rag_answer
            log(f"    Q{q['id']}: 生成答案 {len(rag_answer)} 字符")

        log(f"\n  >>> Step 3: RAG答案评分器 — 四维度量化评分")
        round_results = []
        for q in questions_raw:
            docs, metas, scores = retrieved[q["id"]]
            gen_ans = rag_answers.get(q["id"], "")
            sr = score_one_v6(q, docs, metas, full_bank_lookup, reranker, collection, embedder, gen_ans)
            round_results.append(sr)
            log(f"    Q{q['id']}: 总分={sr['total_score']} "
                f"忠实度={sr['faithfulness_score']} "
                f"答案准确={sr['answer_accuracy_score']} "
                f"来源={sr['source_match']}")

        scores = [r["total_score"] for r in round_results]
        avg = round(sum(scores) / len(scores), 1)
        low_count = sum(1 for s in scores if s < PASS_SINGLE_MIN)
        pass_count = sum(1 for s in scores if s >= PASS_AVG_TARGET)

        mod_scores = compute_module_scores(round_results, full_bank_lookup)
        for mod_name in sorted(mod_scores.keys()):
            ms = mod_scores[mod_name]
            if mod_name not in module_history:
                module_history[mod_name] = {"scores": [], "rounds": 0}
            module_history[mod_name]["scores"].extend(ms["scores"])
            module_history[mod_name]["rounds"] += 1
            status = "✅已修复" if mod_name in fixed_modules else ""
            log(f"  模块[{mod_name}]: 本轮均分={ms['avg']} 最低={ms['min']} {status}")

        log(f"\n  >>> Step 4: 汇总判断")
        if target_module:
            log(f"  🎯 聚焦模块[{target_module}]: 均分={avg} | 低分(<{PASS_SINGLE_MIN})={low_count}题")
        else:
            log(f"  本轮: 均分={avg} | 低分(<{PASS_SINGLE_MIN})={low_count}题 | 达标(≥{PASS_AVG_TARGET})={pass_count}/{len(questions)}题")

        low_questions = [r for r in round_results if r["total_score"] < PASS_SINGLE_MIN]
        if low_questions:
            log(f"\n  ⚠ 低分题清单:")
            for r in low_questions:
                log(f"    Q{r['id']} (总分{r['total_score']}): {', '.join(r['loss_reasons'])}")
                for mk in r.get("missing_keypoints", [])[:3]:
                    log(f"      - [{mk['coverage']}] (raw={mk['raw_coverage']}) {mk['kp'][:80]}")

        failures = [r for r in round_results if r["total_score"] < PASS_SINGLE_MIN]

        if target_module and avg >= PASS_AVG_TARGET and low_count == 0:
            log("")
            log(f"  ✅ 模块[{target_module}]达标！均分{avg}≥{PASS_AVG_TARGET}，无单题<{PASS_SINGLE_MIN}")
            fixed_modules.add(target_module)
            target_module = None

        if not target_module and avg >= PASS_AVG_TARGET and low_count == 0:
            log("")
            log("=" * 70)
            log(f"  ✅ 全局达标！所有模块已修复或摸底均分≥{PASS_AVG_TARGET}")
            log("=" * 70)
            history.append({"round": round_num, "avg": avg, "low_count": low_count,
                            "pass_count": pass_count, "n_questions": len(questions),
                            "terminated": "达标",
                            "target_module": target_module, "fixed_modules": sorted(fixed_modules)})
            save_report(history, round_results, round_num, full_bank_lookup, reach_target=True,
                        extra_info=f"已修复模块: {sorted(fixed_modules)}")
            return

        if prev_avg is not None and avg < prev_avg:
            decline_count += 1
            log(f"  ⚠ 均分下降: {prev_avg} → {avg} (连续下降{decline_count}轮)")
        else:
            decline_count = 0
        prev_avg = avg

        if decline_count >= 3:
            log("")
            log("=" * 70)
            log("  ⚠ 回退中止: 连续3轮分数下降")
            log("=" * 70)
            history.append({"round": round_num, "avg": avg, "low_count": low_count,
                            "pass_count": pass_count, "n_questions": len(questions),
                            "terminated": "回退中止",
                            "target_module": target_module, "fixed_modules": sorted(fixed_modules)})
            save_report(history, round_results, round_num, full_bank_lookup, reach_target=False,
                        extra_info=f"连续3轮下降已中止。已修复: {sorted(fixed_modules)}")
            return

        if not target_module:
            candidates = []
            for m, mh in module_history.items():
                if m in fixed_modules: continue
                recent = mh["scores"][-10:] if len(mh["scores"]) >= 10 else mh["scores"]
                if recent:
                    candidates.append((m, sum(recent) / len(recent)))
            if candidates:
                target_module = min(candidates, key=lambda x: x[1])[0]
                c_avg = round(min(candidates, key=lambda x: x[1])[1], 1)
                log(f"\n  🎯 选定聚焦模块: [{target_module}] (历史均分{c_avg}最弱)")

        if low_count < FAIL_TRIGGER_COUNT and not target_module:
            log(f"  ⚠ 低分题({low_count})未达优化阈值({FAIL_TRIGGER_COUNT})，但均分{avg}<{PASS_AVG_TARGET}，继续摸底")

        if not failures and target_module:
            log(f"  ℹ 聚焦模块[{target_module}]本轮无低分题，继续加练巩固")
            history.append({"round": round_num, "avg": avg, "low_count": low_count,
                            "pass_count": pass_count, "n_questions": len(questions),
                            "target_module": target_module, "fixed_modules": sorted(fixed_modules),
                            "missing_modules": [], "supplement_chunks": 0, "written": 0})
            continue

        log(f"\n  ❌ 未达标: {len(failures)}题低于{PASS_SINGLE_MIN}分，触发优化流程")

        log(f"\n  >>> Step 5: 失败案例分析师 — 分析低分根因")
        analysis = analyze_failures_v4(failures, round_num)
        log(f"  缺失模块: {analysis['missing_modules']}")
        log(f"  缺失关键点: {len(analysis['missing_keypoints'])} 个")
        if analysis.get("supplement_instructions"):
            log(f"  补充指令: {len(analysis['supplement_instructions'])} 条")
            for instr in analysis["supplement_instructions"]:
                log(f"    → {instr['module']}: {len(instr['target_keypoints'])} 个关键点")

        log(f"\n  >>> Step 6: Silly Tavern文档生成 — 含完整原文上下文和正则示例")
        supplement_chunks = generate_supplement_chunks_v4(failures, full_bank_lookup, analysis, retrieved)
        log(f"  生成 {len(supplement_chunks)} 个补充块 (source='supplement')")

        log(f"\n  >>> Step 7: 知识库写入器 — 嵌入知识库")
        written = writer.write_supplements(supplement_chunks)
        log(f"  写入 {written} 条补充块到知识库 → 知识库总计 {collection.count()} 条")

        history.append({"round": round_num, "avg": avg, "low_count": low_count,
                        "pass_count": pass_count, "n_questions": len(questions),
                        "missing_modules": analysis["missing_modules"],
                        "supplement_chunks": len(supplement_chunks), "written": written,
                        "target_module": target_module, "fixed_modules": sorted(fixed_modules)})
        log(f"\n  >>> 第{round_num}轮优化完成，知识库已更新，进入下一轮...")

    log("")
    log("=" * 70)
    log(f"  ⚠  {MAX_ROUNDS}轮后仍未达标，输出优化历史")
    log(f"  已修复模块: {sorted(fixed_modules)}")
    log("=" * 70)
    save_report(history, round_results, MAX_ROUNDS, full_bank_lookup, reach_target=False,
                extra_info=f"已修复: {sorted(fixed_modules)}, 聚焦中: {target_module}")


if __name__ == "__main__":
    random.seed(int(time.time()))
    run_orchestrator()
