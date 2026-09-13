# SillyTavern RAG

把 [SillyTavern 官方文档](https://github.com/SillyTavern/SillyTavern-Docs) 做成一个**可自动增量更新**的本地 RAG 知识库：定时拉取上游文档变更 → 分块 → 向量化 → 存入 ChromaDB → 提交回本仓库。

目标有两个：让检索到的内容始终跟着官方文档同步；以及用中英跨语言嵌入模型，做到**用中文提问也能命中英文原文**。

## 工作流程

`main_rag_pipeline.py` 一条命令跑完 5 步：

1. **拉取上游** —— 给本地文档仓库配置 `upstream`，执行 `git fetch` + `git merge upstream/main`，再用 `git diff --name-only` 取出本次变更的 `.md`
2. **一致性校验 + 预处理** —— 对比本地与上游的 Markdown 数量，偏差超过 5% 直接中止；用 `MarkdownHeaderTextSplitter` 按 H1/H2/H3 切片，每个 chunk 带上 `doc_id` / `chunk_id` / `chunk_hash`(md5)
3. **向量化** —— BCEmbedding `maidalun1020/bce-embedding-base_v1`（CPU 推理），写入 ChromaDB 持久化集合 `sillytavern_docs`
4. **增量索引** —— LangChain Indexing API（`cleanup="incremental"`）+ `SQLRecordManager`：未变动的 chunk 跳过、被删除的文档清掉向量，并清理孤立记录
5. **版本管理** —— ChromaDB 目录超过 100 MB 时打包 zip 备份，随后 `git add` / `commit` / `push`，提交信息统一为 `docs: update RAG index - YYYY-MM-DD HH:MM`

```bash
python main_rag_pipeline.py            # 增量更新
python main_rag_pipeline.py --force    # 忽略增量跳过逻辑，强制走完整流程
```

## 目录结构

```
main_rag_pipeline.py     # 索引管道（唯一入口，649 行）
requirements.txt         # langchain / langchain-chroma / chromadb / sentence-transformers ...
需求分析.txt             # 最初的 4 条需求
RAG/
├── docs/                # SillyTavern 官方文档本地副本（91 个 .md，正文为英文、目录名已中文化）
├── chroma_db/           # ChromaDB 持久化数据（chroma.sqlite3 约 11 MB，随仓库提交）
├── rag.md               # 方案设计：基于 KARA 的增量更新
└── new_rag.md           # 方案设计：完整工作流与核心参数
.gitattributes           # Git LFS 规则（模型权重 / chroma bin、parquet / 图片）
```

## 技术栈

| 环节 | 选型 |
| --- | --- |
| 分块 | LangChain `MarkdownHeaderTextSplitter`（按标题层级切） |
| 嵌入 | BCEmbedding `bce-embedding-base_v1`（中英跨语言检索） |
| 向量库 | ChromaDB（PersistentClient） |
| 增量索引 | LangChain Indexing API + `SQLRecordManager`（SQLite 记录管理） |
| 版本追踪 | Git（对比上下游提交差异，只处理变更文件） |

## 环境要求与运行

- Python ≥ 3.9；建议可用内存 ≥ 8 GB、磁盘 ≥ 10 GB（含日志轮转）
- 首次运行前需要：
  1. 把官方文档仓库克隆到脚本里的 `DOCS_REPO_DIR`
  2. 确认本仓库已配置 `origin`（脚本结束后会自动 push）
  3. **修改脚本顶部配置区的三个路径**为你本机的实际路径：`BASE_DIR`、`DOCS_REPO_DIR`、`USER_REPO_DIR`

> ⚠️ 脚本中的路径目前是开发机上的绝对路径（`d:\code_item\酒馆rag\...`），克隆到别的机器后**必须先改这三处**才能运行。

```bash
pip install -r requirements.txt
python main_rag_pipeline.py
```

## 运维细节

- **日志**：`logs/update_YYYYMMDD_HHMMSS.log`，保留最近 30 天，过期自动清理
- **磁盘保护**：可用空间低于 2 GB 时先清日志，仍不足则中止本次处理
- **重试**：Git 操作失败重试 3 次、间隔 10 秒
- **备份**：ChromaDB 目录超过 100 MB 时生成 `backup/chroma_db_backup_<时间戳>.zip`
- **调度**：脚本本身不自带定时器，建议用 GitHub Actions（`schedule`）或系统计划任务触发

## 关于 `RAG/docs/`

该目录是 [SillyTavern 官方文档仓库](https://github.com/SillyTavern/SillyTavern-Docs) 的本地副本，仅作为检索语料使用，版权归 SillyTavern 项目及其贡献者所有。

## 设计文档与实现的差异

`RAG/rag.md` 与 `RAG/new_rag.md` 推荐的是 KARA（`kara-toolkit`）做**块级**增量复用；当前 `main_rag_pipeline.py` 落地的是 LangChain Indexing API + `SQLRecordManager` 的**文档级**增量方案，`requirements.txt` 中也没有引入 `kara-toolkit`。两份设计文档作为方案演进过程保留。

## 需求来源

见 `需求分析.txt`，最初的四条需求是：官方文档能实时更新并同步进 RAG；能根据用户描述分析需求并创建角色卡、世界书（可选）；具备对官方文档的熟练掌握（世界书与角色卡格式、正则表达式用法、特定文风的生成、世界书条目深度设置、预设设置、CSS 样式、是否需要格式化状态栏）；角色卡按表单式设计（年龄 / 性别 / 种族等信息 + 尽可能全的标签选择）。
