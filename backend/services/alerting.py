"""邮件告警：出事了主动告诉站长，而不是等他来翻日志。

**只对 5xx 告警**：4xx 是来访者自己的问题（打错路径、没登录、被限流），那类噪音不该进邮箱 ——
否则真正的问题会被淹掉。

**噪音控制（这一条是告警能不能用的关键）**：同一个报警 key（如 `500:/api/rag/search`）
在 `ALERT_COOLDOWN_SECONDS`（默认 300 秒）内**只发一封**。
没有这道闸，一次"数据库打不开"就能让每个请求都发一封邮件，几分钟把邮箱炸掉 —— 那还不如不告警。

**异步发送**：用后台线程发。FastAPI 是单进程多协程，在请求路径上同步发 SMTP（可能几秒）
会**卡住整个事件循环** —— 这个项目之前踩过同类的坑（async def 里做同步重活）。

**没配置就静默跳过**：本地开发、CI、别人克隆走的公开版都不该因为"没配邮箱"而报错。
配置走 .env：SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / ALERT_TO。
⚠️ SMTP_PASS 是**邮箱授权码**，属于密钥 —— 只放 .env（已 gitignore），永不进仓库。
"""
import logging
import os
import smtplib
import threading
import time
from email.header import Header
from email.mime.text import MIMEText

log = logging.getLogger("backend.alert")

_lock = threading.Lock()
_last_sent: dict = {}          # 报警 key -> 上次发送时刻（monotonic）
_recent: list = []             # 最近实际发出的时刻，用于全局速率上限

# 全局速率上限：不管有多少种不同的错误，**10 分钟内最多 3 封**。
# 为什么光靠"同一个 key 冷却"不够：一次故障往往同时冒出好几种错误
# （数据库打不开 → 检索 500 + 后台 500 + 前端跟着报错……），
# 每种都各自冷却的话，邮箱照样会被刷。这道闸是卡"总共发了多少"。
ALERT_MAX_PER_WINDOW = int(os.environ.get("ALERT_MAX_PER_WINDOW", "3") or 3)
ALERT_WINDOW_SECONDS = int(os.environ.get("ALERT_WINDOW_SECONDS", "600") or 600)


def _cfg() -> dict:
    """每次现读环境变量：模块级读取会在 .env 加载之前发生（import 顺序不定），读到的就是空的。"""
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "465") or 465),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASS", ""),
        "to": os.environ.get("ALERT_TO", "").strip(),
        "cooldown": int(os.environ.get("ALERT_COOLDOWN_SECONDS", "300") or 300),
    }


def configured() -> bool:
    c = _cfg()
    return bool(c["host"] and c["user"] and c["password"] and (c["to"] or c["user"]))


def _should_send(key: str, cooldown: int) -> bool:
    now = time.monotonic()
    with _lock:
        # 第一道：全局窗口 —— 最近 10 分钟已经发够 3 封就直接压住
        _recent[:] = [t for t in _recent if now - t < ALERT_WINDOW_SECONDS]
        if len(_recent) >= ALERT_MAX_PER_WINDOW:
            return False
        # 第二道：同一个报警 key 的冷却（防"同一个错每秒一次"）
        if now - _last_sent.get(key, 0.0) < cooldown:
            return False
        _last_sent[key] = now
        _recent.append(now)
        return True


def _deliver(subject: str, body: str) -> None:
    """真正发信。抽出来是为了让 send_test() 能直接调它拿到异常。"""
    c = _cfg()
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = c["user"]
    msg["To"] = c["to"] or c["user"]

    if c["port"] == 465:
        server = smtplib.SMTP_SSL(c["host"], c["port"], timeout=15)
    else:
        server = smtplib.SMTP(c["host"], c["port"], timeout=15)
        server.starttls()
    try:
        server.login(c["user"], c["password"])
        server.sendmail(c["user"], [c["to"] or c["user"]], msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:       # noqa: BLE001
            pass


def _send_in_background(subject: str, body: str) -> None:
    try:
        _deliver(subject, body)
        log.info("告警邮件已发出：%s", subject)
    except Exception as e:      # noqa: BLE001
        # 发不出去**绝不能影响业务**：邮件只是通知，日志留痕就够了
        log.warning("告警邮件发送失败：%s: %s", type(e).__name__, str(e)[:200])


def alert(key: str, subject: str, body: str) -> bool:
    """安排一封告警（同一 key 在冷却期内只发一次）。返回是否真的安排了。

    线程用 daemon=True：不能因为它没发完就拖住进程退出。
    """
    if not configured():
        return False
    c = _cfg()
    if not _should_send(key, c["cooldown"]):
        return False
    threading.Thread(target=_send_in_background, args=(subject, body), daemon=True).start()
    return True


def send_test() -> tuple:
    """同步发一封测试邮件 —— 给"验证配置通不通"用。

    刻意**同步**：要把真实的异常（授权码错、端口被封、SSL 不匹配）原样回报给调用方，
    异步发就没法告诉调用者到底成没成。
    """
    if not configured():
        return False, "SMTP 没配置（.env 里需要 SMTP_HOST / SMTP_USER / SMTP_PASS）"
    c = _cfg()
    subject = "【酒馆RAG】告警邮件测试"
    body = (
        "这是一封测试邮件 —— 说明告警链路是通的。\n\n"
        f"发件：{c['user']}\n收件：{c['to'] or c['user']}\n服务器：{c['host']}:{c['port']}\n\n"
        "以后只有在**服务端错误（5xx）**时才会给你发信，而且同一类错误 5 分钟内只发一封。\n"
        "4xx（打错路径、没登录、被限流）不会打扰你。\n"
    )
    try:
        _deliver(subject, body)
        return True, "已发出，去邮箱看看（可能在垃圾箱）"
    except Exception as e:      # noqa: BLE001
        return False, f"{type(e).__name__}: {str(e)[:200]}"
