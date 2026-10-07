#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""接口层隔离测试：走真实 HTTP（FastAPI TestClient），验 Cookie 登录态与归属校验。

与 tools/test_multitenant.py 的分工：
  那个测服务层逻辑；这个测「浏览器实际会走的路径」—— Cookie 有没有真的种上、
  未登录到底回不回 401、别人的卡是不是真的拿不到、图片端点认不认身份。

    python tools/test_api_auth.py
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

_DB = Path(tempfile.mkdtemp(prefix="strag-api-")) / "api.db"
os.environ["DB_PATH"] = str(_DB)
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
# 这个测试验的是「注册 → 登录态 → 归属隔离」这条链本身，不是邀请码门槛：
# 把邀请码清空，免得线上 .env 一启用邀请码，这里就全部注册不上（2026-10-07 踩到）。
# 邀请码自己的逻辑在 tools/test_security.py 里单独测。
os.environ["REGISTER_INVITE_CODE"] = ""

from fastapi.testclient import TestClient                      # noqa: E402
from backend.main import app                                   # noqa: E402
from backend.models.database import init_db                    # noqa: E402

fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  {'✅' if cond else '❌'} {msg}")
    if not cond:
        fails.append(msg)


def main() -> int:
    init_db()
    # 不进 lifespan（那会去加载向量库）；这里只测接口层
    anon = TestClient(app)
    alice = TestClient(app)
    bob = TestClient(app)
    print(f"临时库：{_DB}\n")

    print("① 未登录：私有接口必须 401，公共接口必须放行")
    check(anon.get("/api/cards").status_code == 401, "匿名 GET /api/cards → 401")
    check(anon.get("/api/worldbooks").status_code == 401, "匿名 GET /api/worldbooks → 401")
    check(anon.post("/api/cards", json={}).status_code == 401, "匿名建卡 → 401")
    check(anon.get("/api/update/check").status_code == 401, "匿名看更新状态 → 401")
    check(anon.get("/api/auth/me").status_code == 401, "匿名 /auth/me → 401")
    check(anon.get("/health").status_code == 200, "匿名 /health 照常可用（健康检查不是私有的）")

    print("② 注册：首个用户是管理员，Cookie 直接种上")
    r = alice.post("/api/auth/register", json={"username": "alice", "password": "pw123456"})
    check(r.status_code == 201, f"注册返回 201（实际 {r.status_code}）")
    check(r.json()["user"]["is_admin"] is True, "首个注册者是管理员")
    check("strag_session" in alice.cookies, "注册后浏览器拿到会话 Cookie")
    check(alice.get("/api/auth/me").json()["username"] == "alice", "带 Cookie 能问到本人")
    r2 = bob.post("/api/auth/register", json={"username": "bob", "password": "pw123456"})
    check(r2.json()["user"]["is_admin"] is False, "第二个注册者不是管理员")

    print("③ 建卡与跨用户读取")
    created = alice.post("/api/cards", json={"name": "爱丽丝的卡", "description": "d"})
    check(created.status_code == 200, f"建卡返回 200（实际 {created.status_code}）")
    cid = created.json()["id"]
    check(alice.get(f"/api/cards/{cid}").status_code == 200, "本人读自己的卡 → 200")
    check(bob.get(f"/api/cards/{cid}").status_code == 404, "别人读同一张卡 → 404（不是 403）")
    check(anon.get(f"/api/cards/{cid}").status_code == 401, "匿名读 → 401")
    check(alice.get("/api/cards").json()["total"] == 1, "本人列表 1 张")
    check(bob.get("/api/cards").json()["total"] == 0, "别人列表 0 张")
    check(bob.put(f"/api/cards/{cid}", json={"name": "偷改"}).status_code == 404, "别人改 → 404")
    check(bob.delete(f"/api/cards/{cid}").status_code == 404, "别人删 → 404")
    check(alice.get(f"/api/cards/{cid}").json()["name"] == "爱丽丝的卡", "反证：卡没被改也没被删")

    print("④ 世界书同样隔离")
    _ = bob.post("/api/worldbooks", json={"name": "鲍勃的世界书", "description": "d", "entries": []})
    check(bob.get("/api/worldbooks").json()["total"] == 1, "本人 1 本")
    check(alice.get("/api/worldbooks").json()["total"] == 0, "别人 0 本")

    print("⑤ 图片端点认身份（这是「别人看不到」里最容易漏的一环）")
    fake_png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    up = alice.post(f"/api/cards/{cid}/image",
                    files={"file": ("a.png", fake_png, "image/png")})
    check(up.status_code == 200, f"本人上传图片 → 200（实际 {up.status_code}）")
    got = alice.get(f"/api/cards/{cid}/image")
    check(got.status_code == 200 and got.content == fake_png, "本人取图 → 200 且内容一致")
    check(bob.get(f"/api/cards/{cid}/image").status_code == 404, "别人取图 → 404")
    check(anon.get(f"/api/cards/{cid}/image").status_code == 401, "匿名取图 → 401")
    check(anon.get(up.json()["image_path"]).status_code == 404,
          "老直链 /static/... 已经取不到了（静态目录不再对外挂载）")

    print("⑥ 退出登录后立刻失效")
    check(alice.post("/api/auth/logout").status_code == 200, "退出接口 → 200")
    check(alice.get("/api/cards").status_code == 401, "退出后私有接口 → 401")

    print("⑦ 管理动作只给管理员")
    check(bob.post("/api/update/run").status_code == 403, "普通用户触发索引更新 → 403")

    print()
    if fails:
        print(f"❌ 失败 {len(fails)} 项：")
        for f in fails:
            print("   ·", f)
        return 1
    print("✅ 接口层隔离测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
