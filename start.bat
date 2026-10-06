@echo off
chcp 65001 >nul
title SillyTavern RAG — 一键启动

echo.
echo ============================================================
echo   SillyTavern RAG 知识库平台 — 一键启动
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查 Node
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

REM 前端依赖
if not exist "frontend\node_modules" (
    echo 📦 前端依赖未安装，正在安装...
    cd frontend
    call npm install
    cd ..
    echo ✅ 前端依赖安装完成
)

echo 🔧 启动后端服务 (FastAPI) ...
start "ST-RAG-Backend" cmd /c "cd /d %~dp0 && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

echo   等待后端就绪...
:wait_backend
timeout /t 2 /nobreak >nul
powershell -Command "try { (Invoke-WebRequest 'http://127.0.0.1:8000/health' -TimeoutSec 2).StatusCode } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 goto wait_backend
echo ✅ 后端服务已就绪

echo 🎨 启动前端服务 (Vite + React) ...
start "ST-RAG-Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo   等待前端就绪...
:wait_frontend
timeout /t 2 /nobreak >nul
powershell -Command "try { (Invoke-WebRequest 'http://localhost:5173' -TimeoutSec 2).StatusCode } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 goto wait_frontend
echo ✅ 前端服务已就绪

echo.
echo 🌐 正在打开浏览器...
start http://localhost:5173

echo.
echo ============================================================
echo   启动完成！
echo   前端: http://localhost:5173
echo   后端: http://127.0.0.1:8000
echo   API文档: http://127.0.0.1:8000/docs
echo.
echo   关闭后端窗口: 在 "ST-RAG-Backend" 窗口中按 Ctrl+C
echo   关闭前端窗口: 在 "ST-RAG-Frontend" 窗口中按 Ctrl+C
echo ============================================================
echo.
pause
