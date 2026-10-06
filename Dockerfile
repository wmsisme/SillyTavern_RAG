# 单镜像部署：一个容器里同时提供 API 与已构建的前端（后端会伺服 frontend/dist）。
#
# ⚠️ 这里**故意不写** `# syntax=docker/dockerfile:1`：那行会额外去拉一个 frontend 镜像，
# 而本文件只用了经典语法（多阶段 COPY / HEALTHCHECK / ENV），不需要它。
# 实测在本机环境下，拉它必然卡在 auth.docker.io 的 IPv6 上（超时），去掉后构建正常。
#
# ⚠️ 镜像里**不含** torch / transformers —— 公网版检索走硅基流动 API。
# 数据（向量索引、SQLite、用户图片）一律走卷挂载，升级镜像不会动到用户数据。

# ---------- 阶段一：构建前端 ----------
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
# 有 lock 就按 lock 装（可复现），没有就退回 install
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- 阶段二：后端运行时 ----------
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/data/data.db \
    STATIC_DIR=/data/static \
    RAG_DIR=/app/RAG

WORKDIR /app

# curl 只用于 HEALTHCHECK
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-server.txt ./backend/requirements-server.txt
RUN pip install --no-cache-dir -r backend/requirements-server.txt

COPY backend/ ./backend/
COPY --from=web /web/dist ./frontend/dist

EXPOSE 8000

# --proxy-headers：让 uvicorn 从 X-Forwarded-For 取真实客户端 IP ——
# 这样反代后面的「按 IP 限流」才按真实 IP 分桶。它默认只信任来自 127.0.0.1 的代理，
# 所以外面伪造 XFF 没用（比在应用层无脑信任 XFF 安全）。
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
