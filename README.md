# SillyTavern RAG 知识库平台

面向 SillyTavern（酒馆）的中文知识库与创作辅助平台：把官方英文文档翻译成中文、向量化后做成可问答的 RAG 服务，并提供角色卡、世界书、工具箱等配套界面。

- 需求来源：[需求分析.txt](需求分析.txt)
- RAG 设计：[设计思路.txt](设计思路.txt)
- 开发计划：[.trae/documents/执行方案.md](.trae/documents/执行方案.md)

---

## 一、功能一览

| 模块 | 说明 | 主要代码 |
| --- | --- | --- |
| 知识问答（首页） | 向量检索 + DeepSeek 生成，流式输出 | [frontend/src/pages/HomePage.tsx](frontend/src/pages/HomePage.tsx)、[backend/api/rag.py](backend/api/rag.py) |
| 角色卡管理 | 分页列表（20/页）、标签/名称/R18 交叉筛选、双击编辑、AI 生成 | [frontend/src/pages/CardsPage.tsx](frontend/src/pages/CardsPage.tsx)、[backend/api/cards.py](backend/api/cards.py) |
| 世界书管理 | 分页列表（5/页）、条目增删改、AI 生成世界观条目 | [frontend/src/pages/WorldBooksPage.tsx](frontend/src/pages/WorldBooksPage.tsx)、[backend/api/worldbooks.py](backend/api/worldbooks.py) |
| 工具箱 | 元数据分离器 / 世界书转换器 / 简繁转换器 / 文本格式化 / JSONL 小说转换 | [frontend/src/pages/ToolDetailPage.tsx](frontend/src/pages/ToolDetailPage.tsx)、[backend/services/toolbox_service.py](backend/services/toolbox_service.py) |
| 文档更新 | 检测上游 SillyTavern-Docs 更新并重建索引 | [backend/api/update.py](backend/api/update.py)、[backend/services/update_service.py](backend/services/update_service.py) |

---

## 二、目录结构

```
酒馆rag/
├─ backend/                 FastAPI 服务（端口 8000）
│  ├─ main.py               应用入口：init_db + 加载 Chroma + 挂载路由/静态文件
│  ├─ config.py             路径、模型名、密钥（从 .env 读）
│  ├─ api/                  health / rag / cards / worldbooks / update / tools
│  ├─ models/ schemas/      SQLAlchemy 表 + Pydantic 出入参
│  └─ services/             rag / update / card / worldbook / toolbox 业务逻辑
├─ frontend/                React 18 + TypeScript + antd 5 + Vite（端口 5173）
│  └─ src/pages/            首页、角色卡、世界书、工具箱页面
├─ RAG/                     数据层
│  ├─ chroma_db/            ChromaDB 持久化目录（集合 sillytavern_docs）
│  ├─ SillyTavern-Docs/     上游英文文档（独立 git 仓库，可 pull 更新）
│  ├─ bge-large-zh/         本地向量模型 bge-large-zh-v1.5（1024 维）
│  ├─ 正则表达式/rag_chunks/ 《精通正则表达式》切片
│  ├─ README.md             learn-regex 正则语法教程
│  ├─ translation_cache.json 文档翻译缓存（含 __commit__）
│  └─ logs/                更新日志
├─ 循环测试.py              离线评测闭环：出题 → 检索 → 四维评分 → 归因 → 补充 → 复测
├─ 索引更新.py              索引管道：pull 上游 → 翻译 → 切片 → 入库 → git 提交
├─ 重建索引.py              清库全量重灌（破坏性）
├─ 元数据校验.py            ChromaDB metadata 体检
├─ test_query2.py           向量库冒烟测试
└─ 题集.json                评测题库
```

**离线脚本与 Web 服务是两套独立实现**：脚本不 import `backend.*`，backend 也不调用脚本，二者只共享 `RAG/` 下的磁盘数据。改动检索逻辑时两边都要看。

---

## 三、快速开始

### 环境要求

- Python 3.10（本项目在 3.10.6 上验证）
- Node.js 18+（前端构建）
- 首次使用需已存在 `RAG/bge-large-zh/`（向量模型，约 1.3GB）

### 安装依赖

```powershell
pip install -r backend/requirements.txt   # 后端（含 chromadb/transformers/torch 等）
cd frontend; npm install; cd ..           # 前端
```

> 根目录的 `requirements.txt` 是早期版本，缺 fastapi/uvicorn/Pillow/opencc 等，**以后端目录内的那份为准**。

### 配置密钥

复制模板并填入自己的 Key：

```powershell
copy .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY=sk-xxxx
```

`.env` 已被 `.gitignore` 忽略，不会提交。未配置时服务仍可启动，但翻译/问答/生成功能不可用。

### 启动

```powershell
.\start.ps1        # 或 start.bat：自动起后端 8000 + 前端 5173 并打开浏览器
```

手动启动：

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000   # 后端，API 文档 /docs
cd frontend; npm run dev                                          # 前端 http://localhost:5173
```

前端通过 Vite 代理把 `/api`、`/health` 转发到 8000（见 [frontend/vite.config.ts](frontend/vite.config.ts)）。

---

## 四、数据与索引

- **向量库**：ChromaDB（持久化在 `RAG/chroma_db/`），集合 `sillytavern_docs`。
- **向量模型**：`bge-large-zh-v1.5`，本地路径由 `EMBEDDING_MODEL_NAME` 决定，默认取 `RAG/bge-large-zh`，可用 `.env` 覆盖。
- **翻译缓存**：`RAG/translation_cache.json`，键为英文原文 MD5，`__commit__` 记录对应的 SillyTavern-Docs commit。commit 不匹配时脚本会重译全部文档（消耗 API 额度）。
- **向量缓存**：`RAG/vector_cache.npz` + `RAG/vector_cache_meta.json`——整库的 ids / documents / metadatas / embeddings（约 9.4MB）。因为本机 ChromaDB 索引无法跨进程复用，启动时若判定索引不可用，会**优先用它把 1798 条灌回去（约 12 秒）**，而不是重新向量化（约 104 秒）。
  - 它由完整重建自动生成；`/api/update/run` 更新文档后会**自动清除**，下次启动重新构建。
  - 想强制走完整重建：删掉这两个文件即可。

### 什么时候需要重建索引

索引不可用时（见「已知问题」第 8 条——本机环境下该判定几乎每次启动都会命中），`_get_collection()` 会**自动清库重建**，启动日志会打印"ChromaDB 索引不可用，正在内联重建..."。重建过程只做向量化，翻译走缓存，通常不产生额外 API 费用。

手动重建：

```powershell
python 重建索引.py     # 注意：会先删除整个集合
```

---

## 五、已知问题与注意事项

1. **`索引更新.py` 会执行 `git add .` 并 push 到 `origin`**（[索引更新.py](索引更新.py) `git_commit_and_push`）。运行前请确认没有敏感文件处于未忽略状态；`.gitignore` 已拦截 `.env`、`backend/data.db`、`RAG/backup/`、`RAG/chroma_db/`（新增文件）。
2. **`backend/services/rag_service.py` 的检索是精简版**：`_get_reranker()` 直接返回 `False`、`_bm25_search()` 返回空列表，实际只有纯向量 Top-5。带 BM25 + bge-reranker 的完整实现在 `循环测试.py` 的 `rag_retrieve_v6`。
3. **前端"参考来源"面板不会显示**：`/api/rag/ask/stream` 固定发送空的 `sources`（[backend/api/rag.py](backend/api/rag.py)）。
4. **元数据分离器对 PNG 会 500**：`toolbox_service.separate_metadata` 返回 `bytes`，FastAPI 无法 JSON 序列化。
5. **标签筛选在分页之后进行**（[backend/services/card_service.py](backend/services/card_service.py)、[worldbook_service.py](backend/services/worldbook_service.py)），`total` 与分页语义不准确。
6. **前端尚未接入 `/api/update/*`**：需求里的"启动检测文档更新并提示"目前只有后端 API。
7. `元数据校验.py` 对每类 source 只抽样 10 条，且看不到 `source` 为文档相对路径的记录。
8. **每次启动后端都会重建索引（约 12 秒）**：本机环境下 ChromaDB 的向量索引**无法被另一个进程加载**，跨进程访问报 `Error loading hnsw index`（0.5.23 下是 `Cannot open header file`，两个版本均复现），于是 `_get_collection()` 每次启动都判定索引不可用。现在优先走向量缓存恢复（约 12 秒，不加载 BGE 模型、不消耗 API 额度），而非重新向量化（约 104 秒）。排查过程中已排除的因素见维护记录。
9. DeepSeek Key 失效时表现为 `/api/rag/ask` 返回 401：更新项目根 `.env` 里的 `DEEPSEEK_API_KEY` 即可（检索功能不受影响）。
10. 升级 ChromaDB 大版本后官方建议执行一次 `chromadb utils vacuum` 整理数据库（可选，非必须）。

---

## 六、维护记录

### 2026-09-20

- 修复后端无法启动：`chromadb` 0.4.24 与 numpy 2.x 不兼容（`np.float_` 已移除），升级到 **0.5.23**（仅影响 `chromadb` 与 `chroma-hnswlib` 两个包）。
- 修复向量模型加载失败：`EMBEDDING_MODEL_NAME` 原来写死成 HF 仓库名 `BAAI/bge-large-zh-v1.5`，但本机 HF 缓存中不存在该仓库，改为**优先使用本地 `RAG/bge-large-zh`**。
- 密钥外置：`DEEPSEEK_API_KEY` 不再硬编码在源码中，改从 `.env` / 环境变量读取；新增 [.env.example](.env.example)。
- 补充 `.gitignore`：拦截 `.env`、`backend/data.db`、`RAG/backup/`、`RAG/chroma_db/`（新增文件）、`.trae/`。
- 关闭 ChromaDB 遥测（`ANONYMIZED_TELEMETRY=False`），并把 `posthog` 从 7.15.3 降到 **3.25.0** —— chromadb 0.5.x 调用的是 `posthog.capture(distinct_id, event, properties)` 三参数老签名，新版 posthog 改成单参数后每次操作都会刷 `Failed to send telemetry event ... capture() takes 1 positional argument`，降级后报错消失。
- 重建 `sillytavern_docs` 向量索引（原 HNSW 索引文件缺失，仅剩 sqlite 记录），仍为 1798 条。
- 重建后 `RAG/chroma_db/` 中只有 `chroma.sqlite3` 与各 segment 的 `index_metadata.pickle`，没有索引二进制文件。

### 2026-09-20（续）— ChromaDB 升级到 1.5.9

- `chromadb` 0.5.23 → **1.5.9**（Rust 存储层）。装前留档：`RAG/backup/chroma_db_pre-1x_20260920_105934/` 与 `pip-freeze_pre-1x_20260920_105934.txt`。
- 1.5.9 **读不了 0.5.23 写的旧库**（`Error loading hnsw index`），已重建索引：仍 1798 条、翻译缓存 90 篇全命中、**未消耗 API 额度**。
- 收益：`pip check` 中 `langchain-chroma 1.1.0 requires chromadb>=1.3.5` 的冲突消失（`索引更新.py` 的依赖障碍解除）；遥测报错在 1.5.9 + posthog 3.25.0 下也不再出现。
- **持久化问题与 chromadb 版本无关**：1.5.9 在 `RAG/chroma_db/` 与临时目录下**都**无法跨进程加载索引。0.5.23 时期最有价值的一组对照：同一段 `create_collection → add → 退出` 代码，在 `RAG/backup/` 下落盘正常（写出 `data_level0.bin`/`header.bin`/`length.bin`/`link_lists.bin`），在 `RAG/chroma_db/` 下却只写出 `index_metadata.pickle`；已排除数据量（1500/1798 条）、参数（`hnsw:space=cosine` + 1024 维）、进程退出方式、干净目录重建等因素。**推断**为索引文件写入在本机被某种机制拦截（待查：文件监视/锁定）。
- 升级前的完整备份保留在 `RAG/backup/chroma_db_pre-upgrade_<时间戳>/`（含 299 个包的 `pip freeze` 快照）。

### 2026-09-20（续 2）— 向量缓存 + 根因排查

- **新增向量缓存**（[backend/services/rag_service.py](backend/services/rag_service.py)）：全量重建后把整库落成 `RAG/vector_cache.npz`（9.4MB）+ `vector_cache_meta.json`；启动时若判定索引不可用，优先从缓存灌回。实测**启动耗时 104s → 11.9s**，不加载 BGE 模型、零 API 消耗。首次实现误用 numpy 定长字符串存文本，缓存膨胀到 **565MB**，改用 `dtype=object` 后降到 9.4MB。
- `update_service.run_update()` 成功后清除该缓存，避免文档更新被旧向量覆盖。
- `.env` 中的 DeepSeek Key 已更新（旧 Key 返回 401），`/api/rag/ask` 端到端验证通过（正常生成回答 + 5 条来源）。
- **根因排查（未最终定位，但已收敛到代码路径）**：失败只在 `_get_collection()` 这条路径上稳定复现。以下因素均已用对照实验**排除**：
  1. chromadb 版本——0.5.23 与 1.5.9 都复现；
  2. 数据规模——100 / 1500 / 1798 条假数据均正常；
  3. 数据内容——把真实 ids/documents/metadatas/embeddings 拿去用独立脚本写入，跨进程完全正常；
  4. 数据库路径——`RAG/backup/`、`RAG/_probe_direct`、`RAG/chroma_db_new` 乃至全新的 `RAG/chroma_db` 均正常；
  5. `hnsw:space=cosine` 参数；
  6. 进程退出方式（进程内检查与退出后检查结论一致）；
  7. 被"损坏索引"污染的 system（沿用污染的 system 重建同样正常）；
  8. torch/BGE 与 CUDA 的使用；
  9. 全零向量的健康检查 query；
  10. 持有已删除 collection 对象的引用；
  11. `.bin` 索引文件是否存在（1.x 下删掉 `.bin` 仍能跨进程查询）。
  剩余可疑点集中在 `_get_collection()` 内部的调用顺序/上下文，需要调试 chromadb 内部状态才能继续。
