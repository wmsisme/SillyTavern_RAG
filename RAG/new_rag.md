# 任务：构建并维护 SillyTavern 文档的 RAG 知识库

## 1. 项目背景与目标

- 官方文档仓库：<https://github.com/SillyTavern/SillyTavern-Docs>
- 我的 Git 仓库：<https://github.com/wmsisme/SillyTavern_RAG.git>
- 最终目标：从官方拉取英文文档 → 本地整理 → 分块 → 向量化 → 存入 ChromaDB → 上传到我的仓库。实现每次官方文档更新后，本地 RAG 知识库也能自动增量更新。

## 2. 技术栈与环境要求

- **跨语言嵌入模型**：BCEmbedding（`bce-embedding-base_v1`），处理中英跨语言检索\[reference:3]
- **重排序模型**：BCEmbedding 的 RerankerModel（`bce-reranker-base_v1`），对初步检索结果进行精排，提升精度\[reference:4]
- **向量数据库**：ChromaDB（PersistentClient 模式）
- **增量更新工具**：KARA（Knowledge-Aware Re-embedding Algorithm）\[reference:5]
- **版本追踪**：Git（通过 diff 检测文件变更）
- **Python 版本**：≥ 3.9
- **内存需求**：建议可用 RAM ≥ 8GB
- **磁盘需求**：本地至少 10GB 可用空间（含日志轮转）

## 3. 工作流程与核心参数

### 3.1 同步阶段：从官方仓库拉取最新文档

- 如果本地没有文档仓库，执行完整克隆；如果已有仓库，执行 `git fetch upstream && git merge upstream/main`
- 使用 `git diff --name-only HEAD@{1} HEAD` 获取变更文件列表
- 变更文件按 `.md` / `.json` / `.yaml` 过滤，忽略 `node_modules`、`.git` 等非文档目录

### 3.2 整理阶段：处理拉取到的文档

- 保留所有 Markdown 格式，包括代码块、表格、列表等结构
- 去除导航栏等非正文内容，保留 `h1`-`h4` 标题层级
- **前置校验**：在记录和分块前，校验变更文件是否非空，编码是否符合 UTF-8
- **手动整理保留**：如有需要手动梳理的内容，在本地调整后直接进入下一阶段

### 3.3 分块与增量更新阶段（核心）

- **分块器**：`RecursiveCharacterChunker(chunk_size=500)`。其中 `chunk_size` 取值建议在 400-600 的区间内，同时 `imperfect_chunk_tolerance` 建议设为 9 以平衡复用与新块创建\[reference:6]
- **增量策略及参数调整**：
  - **新增文档**：对整个新文档进行分块、向量化并存入 ChromaDB
  - **修改文档**：调用 `KARAUpdater.update_knowledge_base()` 对变更文档进行智能增量更新\[reference:7]
  - **已删除文档**：若变更列表中某文档在原仓库不存在，则从 ChromaDB 中删除其向量及元数据；KARA 会自动复用未变化的块，仅对变化部分重新计算嵌入，降低 Embedding API 调用成本
  - **未修改文档**：跳过，不做任何处理
- **防抖机制**：同一文档若在 30 分钟内触发多次，仅处理最后一次版本

### 3.4 向量化与存储阶段

- 使用 BCEmbedding 的 `EmbeddingModel(model_name_or_path="maidalun1020/bce-embedding-base_v1")` 将分块后的文本转为向量\[reference:8]
- 向量存入 ChromaDB 的 `PersistentClient`，集合名固定为 `silly_docs`，持久化数据存放在 `./chroma_db` 目录下
- 每条记录需存储原始文本、向量及元数据（含来源文档路径、标题层级、分块索引等）
- 存储时需带上 `doc_id` 和 `chunk_id`，便于后续追踪和更新

### 3.5 重排序阶段（可选，但建议启用）

- 初步检索返回 Top-N 结果后，调用 BCEmbedding 的 RerankerModel 进行精排，提升语义匹配精度\[reference:9]
- 精排后的结果再送入大模型生成最终答案

### 3.6 上传阶段：将更新后的 RAG 数据上传到我的仓库

- 上传内容：`chroma_db/` 目录（向量数据）+ 更新日志 `CHANGELOG.md` + 备份包 `backup/`
- **Commit 信息**：`"docs: update RAG index – YYYY-MM-DD HH:MM"`
- **.gitignore 需包含**：`.env`、`__pycache__/`、`*.pyc`、`venv/` 以及密钥扫描排除项
- 若 `chroma_db/` 目录大小超过 30MB，启用 Git LFS 进行存储；若超过 100MB，在上传时生成备份包并放入 `backup/` 目录

## 4. 日志与监控

- **日志系统**：所有操作（拉取、分块、向量化、上传等）需生成日志，日志文件存放在 `./logs/` 目录下
- **日志文件命名**：`update_YYYYMMDD_HHMMSS.log`
- **日志记录内容**：操作时间、处理文件数、成功/失败/跳过状态、新增和复用的块数、KARA 效率比、API 调用次数等\[reference:10]
- **日志保留策略**：保留最近 30 天，自动删除过期文件
- **告警通知**（建议）：单次操作连续失败 3 次时，通过 Webhook 发送告警

## 5. 异常处理与容错策略

- **网络超时**：Git 拉取超时重试最多 3 次（间隔 10 秒）；Embedding API 调用超时重试最多 3 次（间隔 5 秒）
- **数据一致性检查**：每次拉取结束后，对比本地文档数量与上游仓库文档数量，若偏差超过 5% 则中止并告警
- **磁盘空间检查**：若本地可用空间低于 2GB，中止处理并删除过期日志
- **回滚机制**：若上传阶段失败，自动回滚到上一个稳定版本的 ChromaDB 数据

## 6. 安全与隐私

- 禁止将 `api_key`、`token`、密码等敏感信息硬编码在脚本中，使用 `.env` 文件管理
- 确保 `.env`、`__pycache__/`、`venv/` 等在 `.gitignore` 中，避免误上传
- 避免上传包含个人隐私的文档内容

## 7. 目录结构建议

project\_root/
├── silly\_docs/ # 克隆的官方文档仓库
├── chroma\_db/ # ChromaDB 持久化向量数据
├── backup/ # Git LFS 以外的备份包（≥100MB 时使用）
├── logs/ # 日志文件
├── scripts/
│ ├── sync\_and\_update.py # 同步与增量更新主脚本
│ ├── sync\_docs.py # Git 拉取模块（独立）
│ └── config.yaml # 可调参数的集中配置文件
├── .env # 敏感信息（API 密钥等），不上传 Git
├── .gitignore # 排除规则
├── .gitattributes # Git LFS 配置
├── requirements.txt # Python 依赖
└── CHANGELOG.md # 更新日志（可选但建议保留）

## 8. 触发与调度机制

- **推荐**：GitHub Actions 每日定时触发（`schedule` 触发器），频率可配置，默认每日 UTC 2:00
- **备选**：本地 Crontab（Linux/Mac）或任务计划程序（Windows）
- **手动触发**：支持通过命令 `python scripts/sync_and_update.py --force` 手动执行完整流程

## 9. 验收标准

- [ ] 命令 `python scripts/sync_and_update.py` 可一键执行从拉取到上传的全部流程
- [ ] 修改任意一个 Markdown 文件后，仅更新对应文档的向量（增量更新验证）
- [ ] 中文提问（如“SillyTavern 如何安装？”）能检索到相关英文文档
- [ ] 日志文件正常生成，30 天自动清理
- [ ] 异常网络下重试机制生效，不会直接崩溃
- [ ] `.env` 文件未被上传至远程仓库
- [ ] 最终代码通过 `ruff` 或 `flake8` 静态检查

