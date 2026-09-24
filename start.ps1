# SillyTavern RAG 知识库 — 一键启动脚本 (PowerShell)
# 用法: 右键 → 使用 PowerShell 运行，或在终端输入 .\start.ps1

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SillyTavern RAG 知识库平台 — 一键启动" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
try {
    python --version 2>&1 | Out-Null
} catch {
    Write-Host "❌ 未找到 Python，请先安装 Python 3.10+" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查 Node
try {
    node --version 2>&1 | Out-Null
} catch {
    Write-Host "❌ 未找到 Node.js，请先安装 Node.js 18+" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 前端依赖检查
if (-not (Test-Path "$projectRoot\frontend\node_modules")) {
    Write-Host "📦 前端依赖未安装，正在安装..." -ForegroundColor Yellow
    Set-Location "$projectRoot\frontend"
    npm install
    Set-Location $projectRoot
    Write-Host "✅ 前端依赖安装完成" -ForegroundColor Green
}

# 后端端口
$backendPort = 8000
$frontendPort = 5173

# 检查端口占用
$portCheck = netstat -ano | Select-String ":$backendPort " | Select-String "LISTENING"
if ($portCheck) {
    Write-Host "⚠️  端口 $backendPort 已被占用，后端将尝试使用该端口" -ForegroundColor Yellow
}

# 启动后端
Write-Host "🔧 启动后端服务 (FastAPI) ..." -ForegroundColor Yellow
$backendProcess = Start-Process powershell `
    -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot'; python -m uvicorn backend.main:app --host 127.0.0.1 --port $backendPort" `
    -PassThru

Write-Host "  后端启动中，等待就绪..." -ForegroundColor Gray

# 等待后端就绪
$maxWait = 60
for ($i = 1; $i -le $maxWait; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:${backendPort}/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ 后端服务已就绪 (http://127.0.0.1:${backendPort})" -ForegroundColor Green
            $body = $response.Content | ConvertFrom-Json
            Write-Host "  ChromaDB 向量数: $($body.chroma_count)" -ForegroundColor Gray
            break
        }
    } catch {
        # 继续等待
    }
    Start-Sleep -Seconds 1
    if ($i -eq $maxWait) {
        Write-Host "⚠️  后端启动超时，继续启动前端..." -ForegroundColor Yellow
    }
}

# 启动前端
Write-Host "🎨 启动前端服务 (Vite + React) ..." -ForegroundColor Yellow
$frontendProcess = Start-Process powershell `
    -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot\frontend'; npm run dev" `
    -PassThru

# 等待前端就绪
Write-Host "  前端启动中，等待就绪..." -ForegroundColor Gray
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:${frontendPort}" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ 前端服务已就绪 (http://localhost:${frontendPort})" -ForegroundColor Green
            break
        }
    } catch {
        # 继续等待
    }
    Start-Sleep -Seconds 1
}

# 打开浏览器
Write-Host ""
Write-Host "🌐 正在打开浏览器..." -ForegroundColor Cyan
Start-Process "http://localhost:${frontendPort}"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  启动完成！" -ForegroundColor Green
Write-Host "  前端: http://localhost:${frontendPort}" -ForegroundColor White
Write-Host "  后端: http://127.0.0.1:${backendPort}" -ForegroundColor White
Write-Host "  API文档: http://127.0.0.1:${backendPort}/docs" -ForegroundColor White
Write-Host ""
Write-Host "  关闭此窗口不会影响后端/前端运行" -ForegroundColor Gray
Write-Host "  按回车键关闭此窗口..." -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
Read-Host
