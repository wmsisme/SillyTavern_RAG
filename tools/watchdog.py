#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探活 + 自愈：服务挂了就把它拉起来（达铭 2026-10-07 定：只做自动重起，不通知）。

谁在跑它
--------
Windows 计划任务每 3 分钟调一次，用 `pythonw.exe`（**无控制台窗口**）——
达铭明确讨厌弹窗/黑框/抢焦点，所以这里绝不能出现窗口。

怎么判定「挂了」
--------------
请求 `http://127.0.0.1:8000/health` 失败（连不上 / 超时 / 非 200）算一次失败；
**连续 2 次**才动手重启 —— 避免瞬时卡顿、外部网络抖动造成误判。

自愈开关（重要）
--------------
只在 `temp/service.enabled` **存在**时才自愈。
  双击「启动酒馆RAG服务」 → 建立这个开关（= 我想让它跑着）
  双击「停止酒馆RAG服务」 → 删掉开关 + 杀进程（= 我要停）
没有它的话，你关掉服务窗口后会被自动拉回来 —— 那就变成"你想关都关不掉"了。

它管不到的情况（写在最前面免得误会）
--------------------------------
  · **电脑休眠 / 关机** —— 探活脚本自己也停了，谁也救不了
  · **开关不存在** —— 说明你就没想让它跑，这时它什么都不做（安静退出）
"""
import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
HEALTH_URL = "http://127.0.0.1:8000/health"
ENABLED_FLAG = TEMP / "service.enabled"
STATE_FILE = TEMP / "watchdog.state.json"
LOG_FILE = TEMP / "watchdog.log"
UVICORN_LOG = TEMP / "uvicorn.out.log"

# 连续失败几次才重启（1 = 立刻重启，容易被瞬时抖动骗到）
FAILS_BEFORE_RESTART = 2
PROBE_TIMEOUT = 6

CREATE_NO_WINDOW = 0x08000000          # 关键：起子进程时不弹黑框


def log(msg: str) -> None:
    TEMP.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_state(d: dict) -> None:
    TEMP.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def probe() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=PROBE_TIMEOUT) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False
    except Exception:
        return False


def start_server() -> None:
    """无窗口拉起 uvicorn（日志追加到 temp/uvicorn.out.log）。

    ⚠️ 用 `python.exe` + `CREATE_NO_WINDOW`，**绝不要用 `pythonw.exe`** ——
    2026-10-07 实测踩到：pythonw 没有有效的 stdout，uvicorn 启动时会**静默失败**
    （现象极隐蔽：进程确实起来了、也不报错，但端口就是没监听、日志里一行都没有）。
    CREATE_NO_WINDOW 同样不弹任何窗口，却保留了正常的输出句柄。
    """
    py = pathlib.Path(sys.executable)
    if py.name.lower() == "pythonw.exe":          # 万一 watchdog 自己被 pythonw 调起
        cand = py.with_name("python.exe")         # 换个能正常输出的解释器去起服务
        if cand.exists():
            py = cand
    TEMP.mkdir(parents=True, exist_ok=True)
    out = open(UVICORN_LOG, "a", encoding="utf-8", errors="replace")
    subprocess.Popen(
        [str(py), "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(ROOT),
        stdout=out,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
        close_fds=True,
    )


def main() -> int:
    # 开关不在 = 你没打算让它跑着（或你刚点了「停止服务」）→ 安静退出，绝不复活
    if not ENABLED_FLAG.exists():
        return 0

    state = read_state()

    if probe():
        if state.get("fails"):
            log(f"已恢复正常（代理前失败 {state['fails']} 次）")
        write_state({**state, "fails": 0, "last_ok": datetime.now().isoformat(timespec="seconds")})
        return 0

    fails = int(state.get("fails", 0)) + 1
    if fails < FAILS_BEFORE_RESTART:
        write_state({**state, "fails": fails})
        log(f"探活失败第 {fails} 次（不到 {FAILS_BEFORE_RESTART} 次，继续观察）")
        return 0

    log(f"连续 {fails} 次探活失败 → 自动重启服务")
    try:
        start_server()
    except Exception as e:
        log(f"重启失败：{e}")
        write_state({**state, "fails": fails})
        return 1

    restarts = int(state.get("restarts", 0)) + 1
    write_state({"fails": 0, "restarts": restarts,
                 "last_restart": datetime.now().isoformat(timespec="seconds")})
    log(f"已重新拉起（累计自愈 {restarts} 次）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
