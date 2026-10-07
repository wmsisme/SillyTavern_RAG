@echo off
chcp 936 >nul
title 酒馆RAG 服务
REM 自动定位项目根：本文件在 <项目>\tools\desktop\ 下
pushd "%~dp0..\.." 2>nul
if errorlevel 1 goto fail
REM 建立「自愈开关」= 我想让它跑着。tools/watchdog.py 只在这个文件存在时才自动重起服务。
if not exist temp mkdir temp
echo. > temp\service.enabled
echo.
echo   ============================================
echo            酒馆 RAG 知识库平台
echo   ============================================
echo.
netstat -ano | findstr "127.0.0.1:8000" | findstr LISTENING >nul 2>&1
if not errorlevel 1 goto running
echo   正在启动，大约 10 秒后可用：
echo.
echo     本机打开:  http://127.0.0.1:8000
echo     公网打开:  https://cdm.tailcb137c.ts.net:8443
echo.
echo   ------------------------------------------
echo   要停止服务：双击「停止酒馆RAG服务」。
echo   （直接关窗口也会停，但几分钟后探活会把它自动拉回来）
echo   ------------------------------------------
echo.
REM 注意：python 这个名字在 cmd 里可能指向 WindowsApps 的存根、不可执行，必须写全路径
set PYEXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe
if not exist "%PYEXE%" goto nopython
"%PYEXE%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
echo.
echo   服务已停止。自愈开关还在的话，几分钟后会被探活拉回来；
echo   要彻底停下请用「停止酒馆RAG服务」。
pause
exit /b 0
:running
echo   [已在运行] 服务已经开着了。
echo.
echo     本机打开:  http://127.0.0.1:8000
echo     公网打开:  https://cdm.tailcb137c.ts.net:8443
echo.
pause
exit /b 0
:nopython
echo   [错误] 找不到 Python：%PYEXE%
echo   升级过 Python 的话，把本文件里 set PYEXE= 那行改成新路径。
pause
exit /b 1
:fail
echo   [错误] 进不去项目目录（本文件要放在 <项目>\tools\desktop\ 下）
pause
exit /b 1
