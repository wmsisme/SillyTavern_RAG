@echo off
chcp 936 >nul
title 停止酒馆RAG 服务
pushd "%~dp0..\.." 2>nul
echo.
echo   正在停止「酒馆 RAG 知识库平台」...
echo.
REM 先删自愈开关 —— 不删的话探活脚本几分钟内会把它重新拉起来
if exist temp\service.enabled (
    del temp\service.enabled
    echo   已关闭自动恢复。
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "127.0.0.1:8000" ^| findstr LISTENING') do (
    echo   结束进程 PID %%p
    taskkill /F /PID %%p >nul 2>&1
)
echo.
echo   已停止（公网地址 https://cdm.tailcb137c.ts.net:8443 也会随之打不开）。
echo   要重新开启：双击「启动酒馆RAG服务」。
echo.
pause
