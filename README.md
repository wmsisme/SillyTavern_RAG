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
| 角色卡管理 | 分页列表（20/页）、标签/名称交叉筛选、双击编辑、AI 生成 | [frontend/src/pages/CardsPage.tsx](frontend/src/pages/CardsPage.tsx)、[backend/api/cards.py](backend/api/cards.py) |
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
│  ├─ bge-reranker-v2-m3/   本地精排模型（约 2.2GB，Web 检索与循环测试共用）
│  ├─ vector_cache.npz      整库向量快照（兜底恢复用，可删）
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

### 首次克隆要自备什么（仓库里没有的东西）

`.gitignore` 挡掉了全部大件与用户数据，所以新克隆下来是这样：

| 缺什么 | 怎么补 | 说明 |
| --- | --- | --- |
| `RAG/bge-large-zh/`（1.3GB） | 自行下载 `BAAI/bge-large-zh-v1.5` 放进去 | 向量模型，必需 |
| `RAG/bge-reranker-v2-m3/`（2.2GB） | 用「四、数据与索引」里的 `snapshot_download` 命令 | 精排模型；没有就自动降级为不精排 |
| `RAG/SillyTavern-Docs/` | `git clone https://github.com/SillyTavern/SillyTavern-Docs.git` 到该路径 | 上游英文文档，更新功能靠它 |
| `RAG/translation_cache.json` | 首次建索引时自动生成，**但要重新调用 API 翻译 90 篇** | ⚠ 这是唯一有 API 成本的步骤 |
| `RAG/chroma_db/` | 启动后端会自动重建（或跑 `重建索引.py`） | 向量库早已不再入库 |
| `backend/static/` | 上传角色卡图片时自动建 | 用户数据 |
| `.env` | `copy .env.example .env` 后填 Key | 见下一节 |

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
- **重排序模型**：`bge-reranker-v2-m3`（约 2.2GB），放在 `RAG/bge-reranker-v2-m3`（已 gitignore）。下载：
  ```powershell
  python -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-reranker-v2-m3', local_dir=r'RAG/bge-reranker-v2-m3', allow_patterns=['*.json','*.txt','model.safetensors','sentencepiece*'], ignore_patterns=['*.bin','onnx/*'])"
  ```
  目前 Web 侧检索也已经用它做精排（见已知问题 2），`循环测试.py` 与后端两边共享同一个本地目录。
- **翻译缓存**：`RAG/translation_cache.json`，键为英文原文 MD5，`__commit__` 记录**上次完整索引成功**的 SillyTavern-Docs commit。
  - `__commit__` **只在零翻译失败时才推进**：有失败就保留旧值，这样 `check_update` 仍会报「有更新」、失败篇目下次会重试，同时译文照常落盘。**不要**改成写 `incomplete` 之类的哨兵值 —— `check_update` 会把基准直接喂给 `git diff --name-only <baseline>`，非法 ref 只会让 stdout 为空、静默判定「无更新」。
- **向量缓存**：`RAG/vector_cache.npz` + `RAG/vector_cache_meta.json`——整库的 ids / documents / embeddings。**现在只是兜底**：索引能正常打开时根本不走它（见已知问题 8）。它由完整重建生成，`/api/update/run` 后会清除。想强制走完整重建：删掉这两个文件即可。

### 什么时候需要重建索引

正常情况下**不需要**：索引可以直接跨进程打开（根因修复见已知问题 8）。真出问题时 `_get_collection()` 按三级降级自愈：

1. **清掉坏索引元数据让 ChromaDB 从 WAL 重建**（约 1.4 秒，最优先）；
2. 从向量缓存灌回（约 12 秒，不加载 BGE、不耗 API 额度）；
3. 全量重新向量化（约 104 秒，翻译走缓存）。

手动重建：

```powershell
python 重建索引.py     # 注意：会先删除整个集合
```

---

## 五、已知问题与注意事项

1. **`索引更新.py` 会执行 `git add .` 并 push 到 `origin`**（[索引更新.py](索引更新.py) `git_commit_and_push`）。运行前请确认没有敏感文件处于未忽略状态；`.gitignore` 已拦截 `.env`、`backend/data.db`、`RAG/backup/`、`RAG/chroma_db/`（新增文件）。
2. ~~`backend/services/rag_service.py` 的检索是精简版~~ → **已修**（2026-09-27）：Web 侧检索现在与 `循环测试.py` 的 `rag_retrieve_v6` 同口径 —— 向量 Top-40 ∪ BM25 Top-40（jieba 分词，按 md5 去重）→ `bge-reranker-v2-m3` 精排 → Top-5。
   - `score` 口径统一为 **sigmoid(精排原始分)** —— 它是决定最终排序的那个量，所以面板上的「相关度」与实际顺序一致，不会再出现名次假分（40/39/38…）；reranker 不可用时退回向量余弦相似度（`1 - distance`）。
   - 实测：问「世界书的递归扫描是怎么工作的？」从"文档里没有相关信息"变成 **364 字正确答案**；其中 `Usage/worldinfo.md` 的递归扫描段是**只被 BM25 召回**（向量相似度 0.0000、原本完全漏掉）再经精排提到第 3 位的。
   - 代价：首次问答要懒加载两个模型（约 13s），之后同一问题约 **2s**；显存约 2.4GB。
   - ⚠ **不要改用 `FlagEmbedding.FlagReranker`**：本机「先 `import chromadb`、再 `import FlagEmbedding`」会以 **0xC0000005 访问违例原生崩溃**（进程直接消失，Python 层抓不到，uvicorn 表现为请求 500 但服务已死）。现用 `transformers` 直接加载同一个模型，评分数学一致 —— 详见 `rag_service._get_reranker()` 注释与维护记录。
3. ~~前端"参考来源"面板不会显示~~ → **已修**（2026-09-27）：`rag_service.ask_stream_events()` 产出真实 sources（含 content / module / 相似度），前端同时补上了 `response.ok` 检查与 `error` 事件识别。
4. ~~元数据分离器对 PNG 会 500~~ → **已修**（2026-09-24）：改为在 api 层转 base64，前端新增图片预览与下载。
5. ~~标签筛选在分页之后进行~~ → **已修**（2026-09-27）：筛选下推到 SQL 后再 count/分页，`total` 与翻页语义正确。注意 tags 是 JSON 列、中文标签在库里是 `\uXXXX` 转义形态，匹配串要先 `json.dumps` 转义。
6. ~~前端尚未接入 `/api/update/*`~~ → **已接入**（2026-09-24）：顶栏「文档更新」按钮 + 启动自动检查弹窗。
7. ~~`元数据校验.py` 对每类 source 只抽样 10 条~~ → **已修**（2026-09-27）：改为**全量分页校验**，并先打印全库 source 分布、标出「计划外」的取值（原来 `source` 是文档相对路径之类的记录永远看不见）。实测 1945 条全通过：1116 官方文档中译 + 675 mastering-regex + 135 supplement + 19 learn-regex。
8. ~~每次启动后端都会重建索引（约 12 秒）~~ → **已修**（2026-09-27，根因查明）。
   真凶不是"索引不落盘"，而是 segment 目录里的 **`index_metadata.pickle`**：上一次进程写下的它会让**下一次新进程**读取集合时报
   `InternalError: Error sending backfill request to compactor: ... Error loading hnsw index`。
   去掉它之后 ChromaDB 会从 `chroma.sqlite3` 的 WAL 重建索引，1810 条实测 **1.4 秒**即可被新进程查询。
   对照实验（同一份库拷到临时目录，排除路径因素）：保留全部子目录 → 必失败；只留 `chroma.sqlite3` → 正常；**仅删这一个 pickle → 正常**。
   现已在 `_get_collection()` 里做成自愈（`_repair_hnsw_pickles()` / `_try_heal_hnsw_index()`）。
   **附带好处**：索引能持久化了 → `循环测试.py` 写进去的 `qa_presupplement` / `supplement` 块不再被启动重建抹掉。
9. DeepSeek Key 失效时表现为 `/api/rag/ask` 返回 401：更新项目根 `.env` 里的 `DEEPSEEK_API_KEY` 即可（检索功能不受影响）。
10. 升级 ChromaDB 大版本后官方建议执行一次 `chromadb utils vacuum` 整理数据库（可选，非必须）。
11. **LLM 必须用非推理模型**：全项目默认 `deepseek-chat`（`.env` 里可用 `DEEPSEEK_MODEL` 覆盖）。**不要**改成 `deepseek-v4-flash` / `deepseek-v4-pro` 这类推理模型——它们会把整个 `max_tokens` 预算烧在隐藏的 `reasoning_content` 上，**返回 HTTP 200 但 `content` 为空串**，异常捕获根本不会触发。2026-09-24 正是这个原因导致 16 篇文档"翻译成功"却入库英文原文。
12. ~~`RAG/chroma_db/chroma.sqlite3` 在仓库里会随每次更新增大~~ → **已处理**（2026-09-27）：`git rm --cached` 解除跟踪（**本地文件保留**），`.gitignore` 里的 `RAG/chroma_db/` 接管，`索引更新.py` 的 `git add .` 不会再把它加回来。索引改为纯本地生成 —— 自愈（1.4s）、向量缓存（12s）、全量重建（104s）三条路径都能重建出来。
13. **`/api/rag/ask*` 的两条路径现在共用一份装配逻辑**（`_prepare()`），改 prompt / 上下文扩展时不用再改两处。
14. **卡片图片（`image_path`）整条链路还没实现**：列表页有 `<Image src={image_path}>` + 默认图标兜底，但后端没有图片上传/存储/静态服务，编辑页也没有上传入口 —— 所以实际永远显示默认图标。

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

### 2026-09-24 — 工具箱 5 处修复 + 更新检测接入 + LLM 模型纠错

**工具箱（`backend/services/toolbox_service.py` / `backend/api/tools.py` / 前端 `ToolDetailPage.tsx`）**

- **简繁转换器是空壳**：`opencc` 未安装时静默返回原文却报"转换完成"。已安装 `opencc-python-reimplemented`（`backend/requirements.txt` 早已声明该依赖），并在缺依赖时改为**明确报错**而非假装成功。
- **元数据分离器对 PNG 一律 500**：`separate_metadata` 返回 `bytes`，FastAPI 无法 JSON 序列化。改为在 api 层转 base64，前端新增图片预览与下载按钮。顺带修好 `chara`/`ccv3` 的解析（两者都是 base64 编码的 JSON）。
- **世界书转换器只认 `entries` 是数组**：SillyTavern 原生导出常是 `{"0": {...}, "1": {...}}` 字典形式，旧代码直接报 `'str' object has no attribute 'get'`。新增 `_extract_entries()` 统一数组/字典/`data.entries` 三种结构。
- **`constant` 与 `depth` 语义被搅乱**：旧代码把 `constant`（常驻布尔）写进 `depth`，输出 `"depth": true`；反向又把 `depth` 当 `constant`。现在两者分开保留，往返转换可验证。
- **带 BOM 的 UTF-8 文件解析失败**：统一走 `decode_text()`（`utf-8-sig` → `gbk`）。Windows 记事本 / `Set-Content -Encoding UTF8` 写出的文件不再报 `Unexpected UTF-8 BOM`。
- 验证：18 项端到端断言全通过（5 个坑各自的用例 + 往返回归）。

**启动更新检测（需求 1 的前端那一半）**

- 前端新增 `frontend/src/components/UpdateNotice.tsx`，挂在顶栏（有更新时带小红点）：应用启动自动检查 → 有更新弹窗列出变更文件与当前/索引/上游 commit（可"暂不更新"）→「立即更新」带进度条（轮询 `/api/update/status`）→ 完成后提示刷新页面。`main.tsx` 包 antd `<App>` 以提供 `App.useApp()` 上下文。
- `/api/update/check?force=true` 支持跳过缓存；非强制时走 **10 分钟 TTL 缓存**（原来每次刷新页面都真的去 `git fetch`）。
- **漂移检测修正**：原来 `check_update` 只比较 `upstream/main` 与本地 HEAD、`run_update` 只比较 merge 前后 HEAD，导致 ① 本地新提交永远检测不到，② 一旦触发更新就把全部 90 篇重译+重灌。现在统一以**翻译缓存记录的 `__commit__`（= 上次真正被索引的版本）**为基准，同时看上游漂移、本地提交漂移、工作区未提交改动。
- **更新改为先删后写**：原来 `run_update` 是纯追加、`deleted_vectors` 恒为 0，一次更新把 1798 条撑到 2963 条（同一文档新旧译文并存、召回重复）。现在先删除 `source=translated_official_docs` 的旧切片再写入，实测：造一篇新文档触发更新 → `deleted=1116 / new=1119`，集合仅净增 3 条；还原后再次更新 → `deleted=1119 / new=1116`，**精确回到 1810 条**。
- `update_service` / `rag_service` 里两处 `os.chdir()` 改为显式给 git 传 `cwd`（常驻服务进程不该改进程级工作目录）。

**LLM 模型纠错（本次最重要的一处）**

全项目 15 处调用都写着 `model="deepseek-v4-flash"`。实测这个模型是**推理模型**：同一篇 14803 字符的文档，

| 模型 | 耗时 | finish_reason | content |
| --- | --- | --- | --- |
| `deepseek-chat` | 11.6s | stop | 6127 字中文 ✅ |
| `deepseek-v4-flash`（max_tokens=8192） | 29.2s | length | **空串** ❌ |
| `deepseek-v4-flash`（max_tokens=16384） | 43.8s | stop | 6381 字（烧 16244 tokens） |
| `deepseek-v4-pro`（max_tokens=8192） | 104.5s | length | **空串** ❌ |

它把全部预算花在隐藏的 `reasoning_content` 上（实测 27903 字思维链），**返回 HTTP 200 而非报错**，所以 `except` 完全不触发，旧代码的 `if zh and len(zh) > 10: ... else: zh_content = content` 分支悄悄把**英文原文当成译文**写进缓存 —— 16 篇新增文档因此一直是英文，而且下次还会被当成"已有译文"复用。

修复：

- 新增 `backend/config.py: DEEPSEEK_MODEL`，默认 `deepseek-chat`（可用环境变量覆盖），15 处调用全部改为引用它。
- 翻译路径**不再静默降级**：显式检出空 `content`（并打印 `finish_reason` 与 reasoning 长度）、失败**不写缓存**、逐篇登记并在更新结果里通过 `translate_failures` 回报。
- 修掉 `__commit__` 被写死的老问题：`重建索引.py` 写死 `"rebuild"`、`rag_service._rebuild_index_inline` 写死 `"inline"`，导致缓存 commit 永远对不上、下次必然全量重译。现在都写文档仓库的真实 commit。
- `重建索引.py` 的向量模型也修了同样的坑：它写死 HF 仓库名 `BAAI/bge-large-zh-v1.5`（本机 HF 缓存里没有），而加载用 `local_files_only=True` → 必然失败，**且脚本已先删掉集合**，会留下空库。改为优先用本地 `RAG/bge-large-zh`（`backend/config.py` 早修过，脚本侧漏了）。
- 结果：重建索引 1810 条、90 篇文档翻译缓存全命中零新翻译；`/api/rag/ask` 与 `/api/rag/ask/stream` 端到端恢复（228 字中文回答 + 5 条来源；流式 103 token + done）。

**Git**

- Web 应用首次入库（760 个文件）：`backend/`、`frontend/`、`README.md`、`start.*` 等此前一直是 untracked。
- 提交前清除三处写死的 DeepSeek key（`循环测试.py` / `索引更新.py` / `重建索引.py`，与 `.env` 在用的不是同一个）。已核实该 key 从未进入任何提交、也从未推到远端。三个脚本改为只读环境变量并各自加载 `.env`。
- `.gitignore` 补充拦截 `RAG/vector_cache.npz`、`RAG/vector_cache_meta.json`（可再生的索引产物，约 9MB）与 `*.tsbuildinfo`。
- 远端 `wmsisme/SillyTavern_RAG` 上曾有一个本地不知道的提交 `01c3ec5 docs: 添加项目 README`（GitHub 网页编辑器加的），其内容描述的是**已删除的 `main_rag_pipeline.py` 旧管线**，属过时文档，已用本 README 覆盖。

### 2026-09-27 — 索引根因修复 + 自动更新修通 + 循环测试跑通 + 前端修复

**① 索引跨进程问题：根因查明并修复（推翻上文的"索引不落盘"推断）**

- 真凶是 segment 目录里的 `index_metadata.pickle`（86KB）。它由**上一个进程**写下，**新进程**读它就会报
  `InternalError: Error executing plan: Error sending backfill request to compactor: Error constructing hnsw segment reader: Error creating hnsw segment reader: Error loading hnsw index`。
- 对照实验（整库拷到临时目录，排除"路径/被监视"因素）：
  | 实验 | 结果 |
  | --- | --- |
  | 保留全部子目录 | ❌ 失败 |
  | 拷到别的路径（内容相同） | ❌ 失败 → 与路径无关 |
  | 只留 `chroma.sqlite3`、丢掉全部子目录 | ✅ `count=1810`、query 成功 |
  | **仅删那一个 pickle** | ✅ 成功 |
  | 不删（对照） | ❌ 失败 |
- 结论：**索引并不是没落盘**，而是那个 pickle 让 HNSW segment reader 构造失败；去掉后 ChromaDB 从 SQLite WAL 重建，1810 条 **1.4 秒**即可用。
- 落点：`backend/services/rag_service.py` 新增 `_repair_hnsw_pickles()` 与 `_try_heal_hnsw_index()`，作为 `_get_collection()` 的**第一优先**自愈；向量缓存（12s）与全量重向量化（104s）降为二、三级兜底。启动日志从"ChromaDB 索引不可用，优先尝试向量缓存..."变成干净的"ChromaDB 索引就绪: N 条记录"。
- **副作用红利**：索引能持久化后，`循环测试.py` 写入的 `qa_presupplement` / `supplement` 块不再在下次启动被抹掉（这正是设计文档里第 3、4 层知识，此前一直是缺的）。

**② 后端「自动更新」：修掉三个 bug 后才真正可用**

- **fetch 从不刷新**：`_do_check_update` 原来只在 `refs/remotes/upstream/main` **不存在**时才 `git fetch`，引用一旦建立就永远拿旧引用比较 —— 上游发了新文档也检测不到，`run_update` 也只是 merge 那个旧引用。**等于"自动更新"永久失灵**。现在每次检查都 fetch，并新增 `_git_ok()` 检查退出码（原来 `git fetch` 失败被当成功、静默用旧引用）。
- **`changed_files` 路径截断**：对整个 `git status --porcelain` 输出做 `.strip()` 会吃掉首行前导空格，`ln[3:]` 于是把路径截掉一个字（实测 `Usage/worldinfo.md` → `sage/worldinfo.md`）。改为逐行解析。
- **更新后不收敛**：脏文件即使内容已经索引过也仍被报成漂移，于是点完「立即更新」红点消不掉。现在用翻译缓存的键集合（= 已索引过的内容指纹）过滤掉"已索引的脏文件"。
- 实测（真实造了一次文档内容变更）：`check` 报 `has_update=true` → `run_update` 79.9s、处理 90 篇、删除旧切片 1116 / 写入 1116、`translate_failures=[]`；翻译缓存 107 → **108 条**（只重译了改动的那 1 篇，不是全量）；复检 `has_update=false`，收敛。
- `run_update` 建集合补上 `metadata={"hnsw:space": "cosine"}`，与 `_get_collection()` 保持一致。

**③ 循环测试跑通 + token 计量**

- 给 `循环测试.py` 加了 token 计量：所有 DeepSeek 调用统一走 `llm_create(stage, ...)`，按 `stage`（翻译 / 出题 / 答案生成）记账，每轮与总计写进日志和报告。
- 下载 `bge-reranker-v2-m3` 到 `RAG/bge-reranker-v2-m3`（2.19GB，已 gitignore），`load_models()` 同时支持本地目录优先 + `RERANKER_MODEL_NAME` 覆盖。
- 实测 5 轮（约 4.5 分钟）：均分 7.8 / 7.6 / 7.3 / 8.0 / 7.4，未达 9.0 目标；知识库 1810 → 1945（123 条 QA 预补全 + 12 条补充块），题库 123 → 147 题。
- **token 账单（实测 usage，不是估算）**：第 1 轮 15,882 / 第 2 轮 19,262 / 第 3 轮 21,052 / 第 4 轮 25,074 / 第 5 轮 29,087；**合计 110,357**（输入 96,561 / 输出 13,796，74 次调用），**平均每轮 22,071**。翻译走缓存、QA 预补全与四维评分（reranker）都不吃 token —— 真正消耗只有「答案生成」和「出题」。
- 注意：QA 预补全会把题库的标准答案写进知识库，所以「忠实度」常年 9.9–10.0，循环测试有**部分自我打分**的成分。

**④ 前端修复 + 前后端连接核查**

- 逐接口走 Vite 代理真实调用了一遍（更新检测 / 流式问答 / 角色卡 CRUD + 搜索筛选 / 世界书 CRUD / 5 个工具 / 删除），全部可用。
- `ToolDetailPage`：**切换工具不重置 `direction`/`operation`** → 会把上一个工具的参数值发给新工具（后端回"不支持的转换方向"）。加 `useEffect` 按 `toolId` 重置；并补 `resp.ok` 检查与 `detail` 错误识别（原来 HTTP 报错会被显示成"处理完成"）。
- `HomePage`：补 `response.ok` 检查 + 识别后端的 `error` 事件（原来生成失败时界面只剩空白）。
- `main.tsx` 加 `ConfigProvider locale={zhCN}`（antd 内置文案中文化）；`App.tsx` 加 404 兜底路由（原来未知地址渲染成只有顶栏的空壳）。
- 5 个页面把静态 `message.xxx` 换成 `App.useApp()`（静态方法不消费 ConfigProvider 上下文）。
- **标签筛选下推到 SQL**（`card_service` / `worldbook_service`）：原来对"已取出的一页"做内存过滤，`total` 退化成"本页命中数"，翻到第 2 页会空白。注意 tags 是 JSON 列且中文标签落库为 `\uXXXX` 转义，匹配串要先 `json.dumps(t, ensure_ascii=True)` 再 `LIKE`。实测：命中项全在第 2 页时 `total` 与 `items` 均正确，多标签（逗号分隔）OR 语义、与 `search` 的交叉筛选均正确。

### 2026-09-27（续）— Web 检索层彻底升级：向量 + BM25 + 精排

**背景**：`rag_service` 的"混合检索"一直是空壳 —— `_get_reranker()` 直接 `return False`、
`_build_bm25()` 把 `_bm25` 置 False 后什么都不建、`_bm25_search()` 恒返回 `[]`，
实际只有纯向量 Top-5，`score` 还是名次（40/39/38…）。

**改动**：

- `_build_bm25()`：真正在全库上建 `BM25Okapi`（jieba 分词），并维护 `hash → metadata` 映射（1945 篇约 3 秒，懒加载）。
- `_bm25_search()`：真正的关键词召回。
- `_get_reranker()`：加载 `bge-reranker-v2-m3` 精排（懒加载、失败优雅降级）。
- `_retrieve_raw(query, top_k_final=TOP_K_FINAL)`：向量 ∪ BM25 → 精排 → Top-N，统一返回
  `(docs, metas, 对外相关度, 向量相似度)`；`search()` 与 `ask*` 全部改走它，删掉了重复实现与名次假分。
- `score` 口径：有 reranker 时 = `sigmoid(精排原始分)`；降级时 = 向量余弦相似度。

**踩坑（重要）**：第一版用 `FlagEmbedding.FlagReranker`，结果**后端进程直接消失**（请求 500 后服务已死），
Python 层没有任何 traceback。子进程隔离对照后定位到原生崩溃：

| 变体 | 结果 |
| --- | --- |
| 只 `import FlagEmbedding` | ✅ 退出码 0 |
| **先 `import chromadb` 再 `import FlagEmbedding`** | ❌ 退出码 **3221225477（0xC0000005 访问违例）** |
| 先 `import FlagEmbedding` 再 `import chromadb` | ✅ 正常（但依赖导入顺序，太脆） |
| `transformers` 直接加载同一模型（chromadb 已先导入） | ✅ 正常 |

最终采用 `transformers` 方案（`AutoModelForSequenceClassification` + `float16`），
评分数学与 FlagReranker 一致（`max_length=512`，与其 `passage_max_length` 默认值对齐）。

**效果实测**：

| 项 | 修前（纯向量） | 修后（向量+BM25+精排） |
| --- | --- | --- |
| 「世界书的递归扫描」 | 答"文档里没有相关信息"，来源是目录页+文档开头，相似度 0.69~0.71 | **364 字正确答案**，来源相关度 0.979 / 0.901 / 0.890… |
| `Usage/worldinfo.md` 递归扫描段 | 完全没被召回 | **仅被 BM25 召回**（向量相似度 0.0000）→ 精排提到第 3 位 |
| `/api/rag/search` 的 score | 名次 40/39/38 | 真实相关度 0.9836 / 0.9725 / 0.9683 |
| 单次问答耗时 | 约 1~2s | 首次 13.4s（含两个模型懒加载），之后约 **2.1s** |

**降级验证**：把 `RERANKER_MODEL_NAME` 指向不存在的模型 → 打印明确告警并退回
「向量+BM25 不精排」，检索照常返回、进程不崩（实测退出码 0）。

### 2026-09-27（续 2）— 收尾：仓库瘦身 + 前端健壮性

**仓库瘦身**

- `RAG/docs/`（91 个文件 / 790KB，上游英文文档的重复副本，全项目零引用）**已删除** —— 真正读的是 `RAG/SillyTavern-Docs`。删除前全仓 grep 复核过引用为 0。
- `RAG/chroma_db/chroma.sqlite3`（45MB）解除跟踪（见已知问题 12）。

**前端健壮性**

- `services/api.ts` 重写：加 **AbortController 超时**（默认 60s，AI/更新类接口用 `LONG_TIMEOUT`）；
  错误信息统一解析（`{detail}` / `{error}` / `{message}` / HTML 都能取出可读文案）；
  204 与空响应体不再让 `response.json()` 抛 `SyntaxError`。
- `UpdateNotice`：更新中的弹窗原来是死锁的（`closable=false` 且无取消），现在
  ① 显示已等待秒数，② 加「不再等待（后端继续执行）」按钮（只是不再等，后端更新照跑完），
  ③ `/update/run` 用放宽超时（默认 60s 会把 80s 的正常更新误判成失败），
  ④ 超时后先查 `/update/status`，仍在跑就提示"后端仍在继续"，而不是笼统报失败。
- `ToolDetailPage`：上传加**大小（32MB）与类型双重校验** —— `accept` 只在文件选择框里生效，
  拖拽/改后缀能绕过；顺手显示文件大小。
- `元数据校验.py`：全量校验（见已知问题 7）。

**角色卡编辑页：状态栏字段联动**

- 现在按开关联动：`状态栏` 关闭 → 只显示一条提示，不出现状态栏内容与自定义 CSS；
  `状态栏` 开启 → 出现「状态栏内容」与自定义 CSS 编辑框。
  `Form.Item` 默认 `preserve`，隐藏不会丢已填内容。
- 踩坑：一开始用 `Form.useWatch` 读开关值 —— 这两个开关在**未激活的页签**里（没挂载），
  `useWatch` 对未注册字段返回 `undefined`；而本机 antd 5.20 的 `useWatch` 还不支持
  `preserve` 参数（`tsc: Expected 1-2 arguments, but got 3`）。最终改为
  「本地 state + `onValuesChange` + 载入时回填」，并把表单初值抽成 `CARD_INITIAL_VALUES`
  让两处共用，避免以后改默认值只改一处。
- 验证方式：无头渲染 + 逐场景断言（关/关、开/关、开/开三种组合下字段的出现与否），
  验证用的临时改动（默认页签、初值）事后已全部还原。
