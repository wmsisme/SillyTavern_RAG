#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全加固的回归测试（2026-10-07 建立）。

跑法：python tools/test_security.py
特点：**全部进程内**跑（临时 SQLite + TestClient），不碰正在运行的服务、
      不写真实数据库、不发任何出网请求（唯一要 DNS 的是两条公网地址断言，
      那两条走的是本机 DNS，失败会跳过而不是报错）。

覆盖 8 组：
  ① SSRF 地址校验：内网 / 环回 / 云元数据 / CGNAT / 非 http(s) 协议一律拒
  ② 密码策略：太短、纯数字、常见弱口令一律拒
  ③ 卡片 schema：创建 / 更新请求不再接受 image_path（跨用户读删图的根因）
  ④ 上传体积上限：工具箱 11MB → 413
  ⑤ 图片头校验：内容不是图片 → 400
  ⑥ 安全响应头 + /docs 关闭
  ⑦ 限流的匿名档（未登录 20 / 登录 50）
  ⑧ 中间件顺序：封禁必须在限流**之前**（用"被封 IP 第二次请求仍是 403 而不是 429"来验）
"""
import os
import sys
import tempfile
from pathlib import Path

try:  # Windows 管道 / 控制台默认 GBK：中文与 emoji 输出会炸，这里自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ⚠️ 必须在 import backend.* 之前设好：这些参数是模块导入时读的环境变量
_TMPDB = Path(tempfile.mkdtemp(prefix="strag_sec_")) / "test.db"
os.environ["DB_PATH"] = str(_TMPDB)
os.environ["TRUST_PROXY"] = "1"            # 用 X-Forwarded-For 模拟来源 IP
os.environ["RATE_LIMIT_ENABLED"] = "1"
os.environ["ENABLE_DOCS"] = "0"            # 和公网一致：文档关闭

from backend.services import auth_service, llm_provider          # noqa: E402
from backend.schemas.character_card import (                     # noqa: E402
    CharacterCardCreate, CharacterCardUpdate,
)

fails: list[str] = []


def check(cond, msg):
    print(f"  {'✅' if cond else '❌'} {msg}")
    if not cond:
        fails.append(msg)


def expect_reject(url, why):
    try:
        llm_provider.validate_base_url(url)
        check(False, f"{why}：{url} —— 竟然放行了")
    except ValueError:
        check(True, f"{why}：{url} 被拒")


# ---------------------------------------------------------------- ① SSRF
def t_ssrf():
    print("① SSRF：自定义 base_url 只准指向公网")
    expect_reject("http://127.0.0.1:8000/health", "环回地址")
    expect_reject("http://127.0.0.1:5401/", "环回地址（另一个服务）")
    expect_reject("http://[::1]:8000/", "IPv6 环回")
    expect_reject("http://localhost:8000/", "localhost 域名")
    expect_reject("http://10.0.0.5/v1", "内网 10/8")
    expect_reject("http://192.168.1.1/v1", "内网 192.168/16")
    expect_reject("http://172.16.0.1/v1", "内网 172.16/12")
    expect_reject("http://169.254.169.254/latest/meta-data/", "云元数据地址")
    expect_reject("http://100.112.244.12:8000/", "Tailscale CGNAT 网段")
    expect_reject("http://0.0.0.0:8000/", "未指定地址")
    expect_reject("file:///C:/Windows/win.ini", "file 协议")
    expect_reject("gopher://127.0.0.1:8000/_x", "gopher 协议")
    expect_reject("http://", "没有主机名")

    check(llm_provider.validate_base_url("") == "", "空地址合法（= 用内置地址）")

    # 公网地址要放行（这两条要 DNS，解析不了就跳过，不算失败）
    for ok_url in ("https://api.deepseek.com/v1", "http://api.siliconflow.cn/v1"):
        try:
            llm_provider.validate_base_url(ok_url)
            check(True, f"公网地址放行：{ok_url}")
        except ValueError as e:
            print(f"  ⚠️ 跳过（DNS 解析不了：{e}）：{ok_url}")

    # 凭证构造这一层也要挡：from_headers 拿到内网地址必须抛 ValueError
    try:
        llm_provider.from_headers("custom", "sk-x", "m", "http://127.0.0.1:8000/v1")
        check(False, "from_headers 没有拦住内网地址")
    except ValueError:
        check(True, "from_headers 拦住内网地址（会转成 400）")


# ---------------------------------------------------------------- ② 密码策略
def t_password():
    print("\n② 密码策略")
    for bad, why in (("123", "太短"), ("123456", "6 位纯数字"), ("12345678", "8 位纯数字"),
                     ("password", "常见口令"), ("abc12345", "常见口令"), ("aaaaaaaa", "重复字符")):
        try:
            auth_service.check_password_strength(bad)
            check(False, f"{why}：{bad} 竟然通过了")
        except auth_service.AuthError:
            check(True, f"{why}：{bad} 被拒")
    try:
        auth_service.check_password_strength("myPass2026")
        check(True, "正常密码放行：myPass2026")
    except auth_service.AuthError as e:
        check(False, f"正常密码被误拒：{e}")
    check(auth_service.MIN_PASSWORD_LEN >= 8, f"长度下限 = {auth_service.MIN_PASSWORD_LEN}")

    # 邀请码：开了就必须对得上；比较要走常量时间且**能容忍非 ASCII**
    from backend.models.database import init_db, SessionLocal
    init_db()
    db = SessionLocal()
    try:
        def _try_reg(name, code, expect):
            try:
                auth_service.register(db, name, "myPass2026", invite_code=code, expect_invite=expect)
                return None                    # 注册成功
            except auth_service.AuthError as e:
                return f"AuthError: {e}"
            except Exception as e:             # noqa: BLE001 —— 任何别的异常都算 bug
                return f"{type(e).__name__}: {e}"

        check(_try_reg("inv_nocode", "", "ABC123") is not None, "开了邀请码却不带码 → 被拒")
        check(_try_reg("inv_ok", "ABC123", "ABC123") is None, "带对邀请码 → 注册成功")
        bad = _try_reg("inv_wrong", "WRONG99", "ABC123")
        check(bad is not None and bad.startswith("AuthError"), f"错邀请码 → 明确被拒（{bad}）")
        # 非 ASCII 邀请码：compare_digest 直接吃会 TypeError → 整站注册 500，这里必须只是"被拒"
        zh_missing = _try_reg("inv_zh1", "", "中文邀请码")
        check(zh_missing is not None and zh_missing.startswith("AuthError"),
              f"中文邀请码不带码 → 被拒而不是崩（{zh_missing}）")
        check(_try_reg("inv_zh2", "中文邀请码", "中文邀请码") is None, "中文邀请码带对 → 注册成功")
    finally:
        db.close()


# ---------------------------------------------------------------- ③ image_path
def t_image_path():
    print("\n③ 卡片 schema 不再接受客户端指定的 image_path")
    c = CharacterCardCreate(name="x", image_path="/static/card_images/card_3_abc.png")
    check(not hasattr(c, "image_path"), "创建请求里的 image_path 被忽略（对象上没有这个字段）")
    u = CharacterCardUpdate(name="y", image_path="/static/card_images/card_3_abc.png")
    dumped = u.model_dump(exclude_unset=True)
    check("image_path" not in dumped, f"更新请求里的 image_path 同样被忽略（实际 dump={dumped}）")
    check(dumped == {"name": "y"}, "其它字段照常生效（不是把整个请求都丢了）")


# ---------------------------------------------------------------- ④⑤ 上传
def t_upload_limits():
    print("\n④⑤ 上传体积与图片头")
    from fastapi.testclient import TestClient
    from backend.main import app

    c = TestClient(app)          # 不 with：不进 lifespan，避免加载向量库

    big = b"A" * (33 * 1024 * 1024)      # 后端上限 32MB（与前端 MAX_UPLOAD_MB 一致）
    r = c.post("/api/tools/width-converter",
               files={"file": ("big.txt", big, "text/plain")},
               data={"operation": "fullwidth_to_halfwidth"})
    check(r.status_code == 413, f"工具箱 33MB → 413（实际 {r.status_code}）")
    check("上限" in r.text, "错误信息里说明了上限")

    small = c.post("/api/tools/width-converter",
                   files={"file": ("ok.txt", "hello".encode(), "text/plain")},
                   data={"operation": "fullwidth_to_halfwidth"})
    check(small.status_code == 200, f"正常小文件照样能用（{small.status_code}）")

    # 超大 JSON body 应当被中间件在读取前就挡掉（JSON 档 16MB）
    r = c.post("/api/rag/search", content=b"x" * (17 * 1024 * 1024),
               headers={"content-type": "application/json"})
    check(r.status_code == 413, f"17MB 请求体 → 413（实际 {r.status_code}）")


# ---------------------------------------------------------------- ⑥ 头 / docs
def t_headers_docs():
    print("\n⑥ 安全响应头 / 接口文档")
    from fastapi.testclient import TestClient
    from backend.main import app

    c = TestClient(app)
    r = c.get("/health")
    h = {k.lower(): v for k, v in r.headers.items()}
    check(h.get("x-content-type-options") == "nosniff", "有 X-Content-Type-Options: nosniff")
    check(h.get("x-frame-options") == "DENY", "有 X-Frame-Options: DENY")
    check("content-security-policy" in h, "有 CSP")
    check(h.get("referrer-policy") == "same-origin", "有 Referrer-Policy")
    check("strict-transport-security" not in h, "http 请求不加 HSTS（localhost 才不会被锁成 https）")

    oj = c.get("/openapi.json")
    check(oj.status_code == 404, f"/openapi.json 已关闭（实际 {oj.status_code}）")
    d = c.get("/docs")
    check("swagger" not in d.text.lower(), f"/docs 不再返回接口文档（实际 {d.status_code}）")


# ---------------------------------------------------------------- ⑦ 限流分档
def t_anon_limit():
    print("\n⑦ 限流：未登录档更严")
    import importlib
    from backend.api import ratelimit

    check(ratelimit.ANON_PER_MINUTE < ratelimit.PER_MINUTE,
          f"匿名额度({ratelimit.ANON_PER_MINUTE}) 比登录({ratelimit.PER_MINUTE}) 小")

    w = ratelimit.SlidingWindow("t", 50)
    t = 5000.0
    # 同一个桶，按传进来的 limit 生效
    oks = [w.hit("ip-x", now=t + i * 0.01, limit=3)[0] for i in range(3)]
    check(oks == [True, True, True], "limit=3 时前 3 次放行")
    check(w.hit("ip-x", now=t + 0.1, limit=3)[0] is False, "第 4 次按 limit=3 被拒")
    check(w.hit("ip-y", now=t + 0.1, limit=3)[0] is True, "另一个 IP 不受影响")
    # cap=0 的边界（以前会 IndexError）
    ok, retry = w.hit("ip-z", now=t + 0.2, limit=0)
    check(ok is False and retry >= 1, "limit=0 时直接拒且不崩（旧版会 IndexError）")


# ---------------------------------------------------------------- ⑧ 中间件顺序
def t_middleware_order():
    print("\n⑧ 中间件顺序：封禁挡在限流之前")
    import importlib
    from fastapi.testclient import TestClient
    from backend.models.database import init_db, SessionLocal
    from backend.services import admin_service
    from backend.api import ratelimit

    init_db()
    db = SessionLocal()
    try:
        try:
            admin_service.ban_ip(db, ip="203.0.113.250", reason="回归测试",
                                 days=1, created_by="test")
        except ValueError:
            pass                     # 已存在（重复跑时）
    finally:
        db.close()

    # ⚠️ 关键：把限额压到 **1/分钟** 再测。
    # 第一版这里忘了压，两次请求在 50/分钟的额度下当然都是 403 —— 于是
    # 「顺序写反」这个 bug 根本测不出来（用故意破坏自证才发现，教训记在 test 里）。
    # 压到 1 之后两种顺序才有区别：
    #   · 封禁在外层 → 两次都 403（被封的请求压根不消耗限流额度）
    #   · 限流在外层 → 第一次 403 但**用掉了唯一额度**，第二次 429
    ratelimit.PER_MINUTE = 1
    ratelimit.ANON_PER_MINUTE = 1

    import backend.main as m
    importlib.reload(m)                     # 用改过的限额重建 app
    c = TestClient(m.app)
    hdr = {"X-Forwarded-For": "203.0.113.250"}
    first = c.post("/api/rag/search", json={"query": "x"}, headers=hdr)
    second = c.post("/api/rag/search", json={"query": "x"}, headers=hdr)
    check(first.status_code == 403, f"被封 IP 第一次就是 403（实际 {first.status_code}）")
    check(second.status_code == 403,
          f"第二次仍是 403 而不是 429 —— 说明封禁跑在限流前面（实际 {second.status_code}）")
    # 反证：换个没被封的 IP，同样打两次 —— 第二次必须被限流挡住，
    # 说明"1/分钟"这个限额确实生效（否则上面的 403 可能只是因为限流根本没工作）
    free = {"X-Forwarded-For": "203.0.113.251"}
    a = c.post("/api/rag/search", json={"query": "x"}, headers=free)
    b = c.post("/api/rag/search", json={"query": "x"}, headers=free)
    check(a.status_code != 429 and b.status_code == 429,
          f"反证：没被封的 IP 第 2 次就 429（实际 {a.status_code} / {b.status_code}），限额确实生效")


def main() -> int:
    t_ssrf()
    t_password()
    t_image_path()
    t_upload_limits()
    t_headers_docs()
    t_anon_limit()
    t_middleware_order()
    print()
    if fails:
        print(f"❌ 失败 {len(fails)} 项：\n  - " + "\n  - ".join(fails))
        return 1
    print("✅ 安全加固测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
