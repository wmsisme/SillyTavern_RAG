# SillyTavern RAG 知识库平台

面向 [SillyTavern](https://github.com/SillyTavern/SillyTavern)（酒馆）玩家的**中文知识库与创作辅助 Web 应用**：
多用户账号 + 知识库检索问答 + 角色卡 / 世界书管理 + 五件套工具箱。

检索走硅基流动（bge-m3 向量 + bge-reranker 精排），生成类调用**全部 BYOK** —— 用户自带大模型 Key，
服务端不提供免费额度、也不留兜底 Key。

**技术栈**：FastAPI · SQLAlchemy · SQLite · ChromaDB · React 18 · TypeScript · antd 5 · Vite · Docker

---

## 这个仓库是什么

- **一个可直接跑起来的 Web 应用**：单容器，FastAPI 同时提供 API 与已构建好的前端页面；
  服务器不需要 GPU，2 核 4G 起步（检索走 API，不用搬本地向量模型）。
- 部署全过程（传索引 → 配 `.env` → 起容器 → 反代 HTTPS → 备份 → 排障）写在 **[部署说明.md](部署说明.md)**。

**这个仓库里没有**（先说清楚，免得白找）：

| 没有 | 为什么 |
| --- | --- |
| 离线语料流水线（抓取 / 翻译 / 切片 / 灌库脚本）与本地向量模型 | 那部分在开发仓；知识库更新走「**本机出索引包 → 只把数据传上服务器**」，服务器上不跑灌库，也不放站长的大模型 Key |
| 任何 API Key | 生成类调用由用户自带（BYOK）；服务端只保留「加密存进用户账号」要用的 `SECRET_KEY` |
| 用户数据（`data/`、`static/`、`RAG/`） | 已被 [.gitignore](.gitignore) 挡住；卡图与账号库都是部署时挂载的卷 |

---

## 一、功能

| 模块 | 说明 | 主要代码 |
| --- | --- | --- |
| 知识库问答（首页，免登录） | 向量 + BM25 混合召回 → 精排 → Top-5；**检索**免登录、也不花用户的钱（服务端出检索成本），**AI 生成答案**走用户自带的 Key；支持流式输出与引用来源 | [frontend/src/pages/HomePage.tsx](frontend/src/pages/HomePage.tsx)、[backend/api/rag.py](backend/api/rag.py)、[backend/services/rag_service.py](backend/services/rag_service.py) |
| 角色卡管理 | 分页列表（20/页）、标签 / 名称交叉筛选、双击编辑、图片上传、AI 生成卡与标签推荐 | [frontend/src/pages/CardsPage.tsx](frontend/src/pages/CardsPage.tsx)、[backend/api/cards.py](backend/api/cards.py) |
| 世界书管理 | 分页列表、条目增删改、AI 生成世界观条目 / 推荐条目 | [frontend/src/pages/WorldBooksPage.tsx](frontend/src/pages/WorldBooksPage.tsx)、[backend/api/worldbooks.py](backend/api/worldbooks.py) |
| 工具箱（免登录） | 元数据分离器 / 世界书转换器 / 简繁转换器 / 文本格式化 / JSONL 小说转换 | [frontend/src/pages/ToolDetailPage.tsx](frontend/src/pages/ToolDetailPage.tsx)、[backend/services/toolbox_service.py](backend/services/toolbox_service.py) |
| 账号与多租户 | 注册登录（httponly Cookie）、改密码、首个注册者自动成为管理员、**卡片 / 世界书按用户隔离** | [backend/api/auth.py](backend/api/auth.py)、[backend/services/auth_service.py](backend/services/auth_service.py) |
| API 设置（BYOK） | 填自己的大模型 Key，两种存法：**只存这台浏览器** / **存进我的账号（加密落库）** | [frontend/src/components/LLMSettingsModal.tsx](frontend/src/components/LLMSettingsModal.tsx)、[backend/services/llm_provider.py](backend/services/llm_provider.py) |
| 按 IP 限流 | 贵重接口 50 次/分钟/IP，登录注册 10 次/分钟/IP（滑动窗口，超限返回 429 + `Retry-After`） | [backend/api/ratelimit.py](backend/api/ratelimit.py) |
| **后台管理与封禁**（仅管理员） | 概览统计 · 用户列表（含会话数 / 提问数 / 最后提问时间）· **封号 / 解封**（当场踢下线）· **IP 黑名单**（限期或永久；环回地址永不封）· 活跃 IP 排行（同一 IP 上多个账号 = 共享账号线索）· 提问记录（可只看没答上来的）· **待更新清单**（勾选要补进知识库的提问 → 导出 Markdown；刻意不做自动灌库） | [backend/api/admin.py](backend/api/admin.py)、[backend/api/ban_guard.py](backend/api/ban_guard.py)、[frontend/src/pages/AdminPage.tsx](frontend/src/pages/AdminPage.tsx) |
| 提问记录与回答评价 | 每次检索 / 问答都留痕（谁、IP、问题、召回条数、最高相关度、是否答上来）；**用户可评价「有帮助 / 没解决 / 检索到的内容不相关」并写明原因**，反馈时还会记下当时的来源摘要（前 5 条的来源与分数） | [backend/api/rag.py](backend/api/rag.py)、[backend/services/admin_service.py](backend/services/admin_service.py)、[frontend/src/components/AnswerFeedback.tsx](frontend/src/components/AnswerFeedback.tsx) |
| **功能反馈**（登录后） | 顶部栏「反馈」按钮：选分类（建议 / 体验 / 故障 / 其他）+ 写内容，提交时自动带上所在页面；后台可查看、标记已处理。入口只给登录用户看，服务端同样要求登录 | [backend/api/feedback.py](backend/api/feedback.py)、[frontend/src/components/UserFeedbackModal.tsx](frontend/src/components/UserFeedbackModal.tsx) |
| 文档更新检测 | 检查上游官方文档仓是否有更新（**需要本机文档仓**，容器部署下不可用，见「已知边界」） | [backend/api/update.py](backend/api/update.py) |

**支持的模型平台**（7 家，均在 [backend/services/llm_provider.py](backend/services/llm_provider.py) 集中注册，
前端「API 设置」直接渲染这份表）：DeepSeek · 硅基流动 · Kimi（月之暗面） · 千问（阿里云百炼） ·
豆包（火山方舟） · OpenAI · Anthropic。前 6 家走 OpenAI 兼容协议，Anthropic 单独适配。

---

## 二、架构

```
浏览器 ──► FastAPI(单进程) ──┬─► /api/*        账号 / 卡片 / 世界书 / 工具箱 / 限流
                            ├─► 检索：ChromaDB(向量) + BM25  ──► 硅基流动 bge-m3 + 精排
                            ├─► 生成：用户自带的 Key（请求头优先，其次账号里加密存的）
                            └─► 静态：frontend/dist（已构建前端，深链接由后端兜底）
```

关键设计取舍：

- **凭证不落服务端兜底**：请求头 `X-LLM-Key` 优先，其次用户账号里加密存的；两者都没有就明确 400，
  绝不偷偷用站长的 Key（见 [backend/api/deps.py](backend/api/deps.py)）。前端没配 Key 时会自动弹设置框。
- **图片走鉴权端点**（`GET /api/cards/{id}/image`）而不是静态目录：静态目录不鉴权，
  否则「只有本人能看到自己的卡」就是假的（见 [backend/main.py](backend/main.py) 的注释）。
- **检索层可切换实现**：`EMBED_PROVIDER=siliconflow`（默认，走 API，镜像不含 torch）或 `local`
  （本机模型，需装完整依赖）。**两套向量不在同一空间，换实现必须重建索引**。
- **限流按真实 IP 分桶**：容器内置 `--proxy-headers`（只信任来自 127.0.0.1 的代理头），
  应用层默认**不信任**客户端伪造的 `X-Forwarded-For`。

### 目录结构

```
.
├─ backend/                  FastAPI 服务（默认端口 8000）
│  ├─ main.py                入口：建表 → 挂路由 → 伺服前端静态与深链接
│  ├─ config.py              路径 / 模型 / 环境变量（从根目录 .env 读，改完要重启）
│  ├─ api/                   health · auth · llm · rag · cards · worldbooks · update · tools · ratelimit
│  ├─ models/ schemas/       SQLAlchemy 表（user / character_card / world_book / …）与 Pydantic 出入参
│  └─ services/              rag · llm_provider · user_llm · secret_box · card · worldbook · toolbox · auth · update
├─ frontend/                 React 18 + TS + antd 5 + Vite
│  └─ src/{pages,components,services,layouts}/
├─ tools/                    自检 / 运维脚本（见「六、自检与测试」）
├─ Dockerfile                多阶段构建：node 构建前端 → python 运行时，单容器同源
├─ docker-compose.yml        env_file + 三个挂载卷（RAG / data / static）
├─ .env.example              配置模板（复制成 .env）
└─ 部署说明.md                部署 / 反代 / 备份 / 更新 / 排障
```

---

## 三、快速开始（本机）

### 环境要求

- Python 3.10（本项目在 3.10.6 上验证）
- Node.js 18+
- Docker（要跑容器时；只做本机开发不需要）

### 安装与配置

```bash
pip install -r backend/requirements.txt   # 本机开发（含 chromadb 等）
cd frontend && npm install && cd ..       # 前端

cp .env.example .env                      # 模板见 .env.example，每项都有注释
```

`.env` 里**必填两项**：

| 变量 | 作用 |
| --- | --- |
| `SECRET_KEY` | 加密「用户存进账号里的 Key」。不填也能跑（本地会自动生成 `backend/.secret_key`）；**丢了 = 所有用户存的 Key 全部解不开**，部署时务必单独备份 |
| `SILICONFLOW_API_KEY` | 检索用（bge-m3 向量 + 精排，硅基流动免费档，需实名） |

### 启动

```powershell
.\start.ps1            # 或 start.bat：起后端 8000 + 前端 5173 并打开浏览器
```

手动启动：

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000   # 后端；接口文档 /docs
cd frontend && npm run dev                                        # 前端 http://localhost:5173
```

前端开发服务器把 `/api`、`/health`、`/static` 代理到 8000（见 [frontend/vite.config.ts](frontend/vite.config.ts)）；
后端也会直接伺服已构建的 `frontend/dist`，所以 `npm run build` 之后单开 8000 就能用完整应用。

### 首次使用

1. 打开页面 → **注册一个账号**（第一个注册的自动是管理员）
2. 右上角用户名 → **API 设置** → 选平台、填自己的 Key（或「只存这台浏览器」）
3. 首页搜一个词试检索；登录后可建角色卡 / 世界书

> 知识库检索需要一份已建好的索引（`RAG/chroma_db/`）。新克隆下来的仓库**不含**这份数据，
> 见 [部署说明.md](部署说明.md) 第 1 节「传项目与索引」。

---

## 四、接口一览

| 分组 | 端点 |
| --- | --- |
| 健康 | `GET /health`（含索引条数与当前版本号） |
| 账号 | `GET /api/auth/config` · `POST /api/auth/register` · `POST /api/auth/login` · `POST /api/auth/logout` · `GET /api/auth/me` · `POST /api/auth/password` |
| 大模型 | `GET /api/llm/providers` · `GET/PUT/DELETE /api/llm/settings` · `POST /api/llm/test` |
| 检索问答 | `POST /api/rag/search` · `POST /api/rag/ask` · `POST /api/rag/ask/stream` · `POST /api/rag/feedback`（用户评价：solved / unsolved / **irrelevant** + 文字原因） |
| 角色卡 | `GET/POST /api/cards` · `GET/PUT/DELETE /api/cards/{id}` · `GET/POST/DELETE /api/cards/{id}/image` · `POST /api/cards/generate` · `POST /api/cards/generate/preview` · `POST /api/cards/generate/status-bar` · `POST /api/cards/generate/greeting` · `POST /api/cards/suggest-tags` |
| 世界书 | `GET/POST /api/worldbooks` · `GET/PUT/DELETE /api/worldbooks/{id}` · `POST /api/worldbooks/generate/preview` · `POST /api/worldbooks/suggest-entries` |
| 工具箱 | `POST /api/tools/separator` · `/worldbook-converter` · `/chinese-converter` · `/width-converter` · `/jsonl-novel-converter` |
| 文档更新 | `GET /api/update/check` · `POST /api/update/run`（管理员） · `GET /api/update/status` |
| 后台管理（管理员） | `GET /api/admin/overview` · `GET /api/admin/users` · `POST /api/admin/users/{id}/ban\|unban\|make-admin` · `GET/POST /api/admin/ip-bans` · `DELETE /api/admin/ip-bans/{id}` · `GET /api/admin/active-ips` · `GET/DELETE /api/admin/queries` |
| 功能反馈 | `POST /api/feedback`（登录用户提交） · `GET /api/admin/feedback` · `POST /api/admin/feedback/{id}/handle` · `DELETE /api/admin/feedback/{id}`（后三个仅管理员） |

完整参数与响应模型见运行时的 `/docs`（FastAPI 自动生成）。

---

## 五、配置项

配置全部从**项目根目录的 `.env`** 读取，**改完必须重启后端**（配置在导入时加载一次）。
每项的含义与默认值都写在 [.env.example](.env.example) 里，常用几项：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | 自动生成 | 账号内 Key 的加密密钥；部署时必须显式设置并备份 |
| `SILICONFLOW_API_KEY` | 空 | 检索（向量 + 精排）用的 Key |
| `EMBED_PROVIDER` | `siliconflow` | `siliconflow` 走 API；`local` 用本机模型（要装 torch、搬 3.4GB 模型） |
| `DB_PATH` / `STATIC_DIR` / `RAG_DIR` | 项目内相对路径 | 数据落点；容器部署分别指向挂载卷 `/data/data.db`、`/data/static`、`/app/RAG` |
| `RATE_LIMIT_PER_MIN` / `RATE_LIMIT_AUTH_PER_MIN` | 50 / 10 | 每 IP 每分钟的贵重接口 / 登录注册额度 |
| `TRUST_PROXY` | 0 | 反代**不在同一台机器**上时才设 1；否则全站会共用一个额度 |
| `REGISTER_INVITE_CODE` | 空 | 留空 = 开放注册；填了必须带邀请码 |
| `UNANSWERED_THRESHOLD` | 0.45 | 最高相关度低于它就算「没答上来」，进后台的待补清单 |
| `QUERY_LOG_MAX` | 20000 | 提问记录最多留多少条，超了从最老的开始裁 |
| `COOKIE_SECURE` | 0 | 上了 HTTPS 后设 1 |

---

## 六、自检与测试

`tools/` 下的脚本都是从项目根目录跑：

```bash
python tools/test_multitenant.py     # 账号与数据隔离（服务层，用临时 SQLite，不需要后端）
python tools/test_api_auth.py        # 接口层权限：401 / 403 / 404 的边界
python tools/test_toolbox.py         # 工具箱 5 个工具（需后端在跑；断言落在具体内容而不是只看 200）
python tools/test_byok.py            # BYOK：无凭证报错 / 假 Key 被拒 / 账号内存密文（--live 才发真实调用）
python tools/test_ratelimit.py       # 限流：贵接口 429、换 IP 可用、非贵接口不受影响
python tools/test_concurrency.py     # 并发：8 个请求是否真并行、事件循环有没有被占住（需后端在跑）
python tools/test_admin.py           # 后台与封禁：封号 / 解封 / 封 IP / 权限边界 / 提问判定（用临时库，不碰真实数据）

python tools/test_deployed_site.py --base http://<服务器>:8000   # 部署冒烟（首次部署务必跑）
python tools/check_server_deps.py    # 把 backend 的 import 与容器实际装的包对照，防「本机能跑、部署缺包」
python tools/check_syntax.py backend # 后端语法自检

python tools/manage_users.py --list  # 账号运维：--reset-password / --make-admin / --deactivate / --ban / --ban-ip / --unban-ip
python tools/backup.py               # 数据备份（SQLite 在线备份 + 卡图 + .env）；--list 看现有备份、--keep N 改保留份数
python tools/rebuild_index_api.py    # 换检索模型后重建索引（--dry-run 先试 20 条；支持断点续传）
```

---

## 七、数据与备份

| 数据 | 位置（容器内） | 说明 |
| --- | --- | --- |
| 账号、卡片、世界书、**提问记录、封禁名单、用户反馈** | `/data/data.db` | SQLite，直接拷文件即可备份 |
| 用户上传的卡片图 | `/data/static/` | 走鉴权端点提供，不对外直链 |
| 向量索引 + 缓存 | `/app/RAG/` | 由本机生成后传上来，服务器上不重算 |

**要备份三样**：`SECRET_KEY`（丢了用户存的 Key 全解不开）、`data/`、`static/`。

---

## 八、安全与隐私

- **数据隔离**：卡片 / 世界书的每一次读写都带 `user_id`，拿别人的 id 访问返回 **404**（不是 403），
  不泄露「这条记录存在」。
- **Key 的两种存法**（界面里必须二选一，互斥）：
  - *只存这台浏览器* —— Key 只在本机 `localStorage`，随请求头发给后端，**服务端不经手**；
  - *存进我的账号* —— 用 `SECRET_KEY` 做 Fernet 加密后落库（见 [backend/services/secret_box.py](backend/services/secret_box.py)），
    响应只回打码形态、**永不回传原文**。
  这层加密挡的是「数据库文件被拖走」；它挡不住服务器被攻破 —— 想完全不经手服务器，就选第一种。
- **密码**：`pbkdf2_sha256` 加盐哈希（标准库实现），**无法找回**，只能由管理员重置；改密码会踢掉所有旧会话。
- **限流**：贵重接口与登录注册分别限流，超限 429 并给 `Retry-After`；额度按真实 IP 分桶。
- **不写日志的**：API Key 不落日志；异常信息里也不带 Key 原文。
- **提问与反馈会被记录**：每次检索 / 问答都会在服务端留下「提问内容 + 账号 + IP + 召回质量」，
  用户提交的评价（有帮助 / 没解决 / **内容不相关**）与**填写的文字原因**同样会保存，
  并且会连同「当时的来源摘要」一起存 —— 事后才说得清是召回给错了、还是文档自己没写清楚。
  此外，登录用户从顶部栏「反馈」按钮提交的建议 / 体验问题 / 故障也会原样保存（含账号与所在页面）。
  用途：排查违规使用（封号 / 封 IP 的依据）、改进知识库与功能。
  提问记录条数有上限（`QUERY_LOG_MAX`），站长可在后台清理。
  ⚠️ **要当对外服务的话，建议同时在页面上向用户明示这一点**（当前版本只在本文档里说明）。

---

## 九、已知边界

- **没有免费额度**：不填 Key 时 AI 问答 / 生成会明确报「请先设置 API Key」——这是设计，不是故障。
  （知识库**检索**本身由服务端承担，不需要用户带 Key。）
- **检索依赖第三方**：向量与精排都走硅基流动，免费档有 RPM 限制，平台不可用时检索不可用。
- **文档更新功能需要本机文档仓**：`/api/update/*` 靠 `git` 比对上游文档仓，
  容器里没有 `.git` 与文档仓，所以部署环境下该功能不可用 —— 公网版更新走「本机出索引包 → 传数据 → 重启」。
- **单进程**：限流窗口存在进程内存里，前端由后端同源伺服；要多副本部署得先解决限流与静态资源的外置。
- **没做公开广场**：卡片与世界书只有本人可见，也没有分享 / 导出为公开链接的入口。

---

## 十、许可

[MIT](LICENSE)
