#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反馈附件测试：五道闸门 + 权限边界（进程内跑，临时库与临时目录，不碰真实数据）。

    python tools/test_attachments.py

**为什么重点在权限**：「本人能下载自己的文件」是最容易碰巧通过的一条断言 ——
所以每个"看不到"的断言都配一条"它其实存在"的反证：
  · 本人下载 → 200（反证：文件确实在）
  · **别人下载 → 404**（不是 403 —— 403 等于承认"这条存在"）
  · 管理员下载 → 200

**路径穿越**也要挡：文件名是用户可控的字符串，不能拿它拼路径。
这里用 `../../evil.md` 这类名字试，断言文件**没有落到附件目录之外**。
"""
import os
import sys
import tempfile
from pathlib import Path

try:            # Windows 控制台默认 GBK，中文与 emoji 会炸，自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ⚠️ 必须都在 import backend.* **之前**设好：config 在导入时就把这些定下来了。
# load_dotenv 是 override=False，所以这里设过的值不会被 .env 覆盖回来。
_TMP = Path(tempfile.mkdtemp(prefix="strag-attach-"))
os.environ["DB_PATH"] = str(_TMP / "test.db")
os.environ["STATIC_DIR"] = str(_TMP / "static")
os.environ["REGISTER_INVITE_CODE"] = ""      # 测试环境不要邀请码

from fastapi.testclient import TestClient      # noqa: E402
from backend.main import app                   # noqa: E402
from backend.models.database import init_db    # noqa: E402
from backend.services import attachment_service  # noqa: E402

PASSED, FAILED = 0, 0


def check(cond: bool, msg: str) -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  ✅ {msg}")
    else:
        FAILED += 1
        print(f"  ❌ {msg}")


def reg(client, name, pwd="Test#12345"):
    r = client.post("/api/auth/register", json={"username": name, "password": pwd})
    # 注册成功是 201（不是 200）—— 第一次写测试时这里断言写严了，当场就红
    assert r.status_code in (200, 201), f"注册失败 {r.status_code}: {r.text[:200]}"
    return client


def main() -> int:
    init_db()
    admin = TestClient(app)      # 第一个注册者 → 自动成为管理员
    other = TestClient(app)
    reg(admin, "attach_admin")
    reg(other, "attach_user")

    print("\n① 未登录不能上传（匿名上传 = 任何人可往站长磁盘写东西）")
    anon = TestClient(app)
    r = anon.post("/api/attachments", files={"files": ("a.md", b"hello", "text/markdown")})
    check(r.status_code == 401, f"匿名上传被挡（实际 {r.status_code}）")

    print("\n② 正常上传")
    r = admin.post("/api/attachments",
                   files={"files": ("档案.md", "# 标题\n正文".encode("utf-8"), "text/markdown")})
    check(r.status_code == 201, f"上传成功（实际 {r.status_code} {r.text[:120]}）")
    item = (r.json().get("items") or [{}])[0]
    aid = item.get("id")
    check(bool(aid), f"拿到附件 id = {aid}")
    check(item.get("orig_name") == "档案.md", f"原文件名被保留用于展示（{item.get('orig_name')}）")

    # 反证：文件真的落盘了
    row_path = attachment_service.ATTACH_DIR / (r.json()["items"][0].get("orig_name") or "")
    stored = list(attachment_service.ATTACH_DIR.glob("*"))
    check(len(stored) == 1, f"磁盘上确实有 1 个文件（{len(stored)} 个）")
    check(row_path.exists() is False,
          "磁盘名**不是**原文件名（用原文件名拼路径就是路径穿越的入口）")

    print("\n③ 权限边界：本人 / 别人 / 管理员")
    r = admin.get(f"/api/attachments/{aid}")
    check(r.status_code == 200 and b"#" in r.content, f"本人能下载（实际 {r.status_code}）")
    r = other.get(f"/api/attachments/{aid}")
    check(r.status_code == 404, f"**别人 404**（实际 {r.status_code}）")
    anon2 = TestClient(app)
    r = anon2.get(f"/api/attachments/{aid}")
    check(r.status_code == 404, f"未登录 404（实际 {r.status_code}）")

    print("\n④ 闸门：类型白名单")
    r = admin.post("/api/attachments", files={"files": ("evil.exe", b"MZ", "application/octet-stream")})
    check(r.status_code == 400, f"exe 被拒（实际 {r.status_code}）")
    r = admin.post("/api/attachments", files={"files": ("pack.zip", b"PK", "application/zip")})
    check(r.status_code == 400, f"zip 被拒（实际 {r.status_code}）")

    print("\n⑤ 闸门：单文件大小")
    big = b"x" * (21 * 1024 * 1024)          # 21MB > 默认 20MB
    r = admin.post("/api/attachments", files={"files": ("big.md", big, "text/markdown")})
    check(r.status_code == 413, f"21MB 被拒（实际 {r.status_code}）")

    print("\n⑥ 闸门：每次个数")
    many = [("files", (f"f{i}.md", b"x", "text/markdown")) for i in range(4)]
    r = admin.post("/api/attachments", files=many)
    check(r.status_code == 400, f"一次 4 个被拒（默认上限 3，实际 {r.status_code}）")

    print("\n⑦ 闸门：每 IP 每天（临时把上限压到「已用 + 2」—— 参数太宽松就测不出鉴别力）")
    # ⚠️ 前面的用例也在用同一个 IP（testclient），已经占掉了一些额度。
    # 直接断言"前两个放行"会红 —— 那不是 bug，是我没把前面的占用算进去。
    # 教训：限额类断言必须**基于当前用量**来设，否则测的是"前面用了多少"。
    from backend.models.database import SessionLocal as _SL
    from backend.models.admin import FeedbackAttachment as _FA
    _db = _SL()
    used_today = _db.query(_FA).count()
    _db.close()
    old = os.environ.get("ATTACH_MAX_PER_IP_PER_DAY")
    os.environ["ATTACH_MAX_PER_IP_PER_DAY"] = str(used_today + 2)      # 再留 2 个额度
    try:
        codes = []
        for i in range(4):
            rr = other.post("/api/attachments",
                            files={"files": (f"d{i}.md", b"x", "text/markdown")})
            codes.append(rr.status_code)
        check(codes[:2] == [201, 201] and codes[2] == 400,
              f"再用掉 2 个后第 3 个被日限挡住（进来前已用 {used_today}，实际 {codes}）")
    finally:
        if old is None:
            os.environ.pop("ATTACH_MAX_PER_IP_PER_DAY", None)
        else:
            os.environ["ATTACH_MAX_PER_IP_PER_DAY"] = old

    print("\n⑧ 闸门：全局总量（压到 1MB 试 —— 同上，不压小测不出来）")
    old_total = os.environ.get("ATTACH_MAX_TOTAL_MB")
    os.environ["ATTACH_MAX_TOTAL_MB"] = "1"
    try:
        from backend.models.database import SessionLocal
        db = SessionLocal()
        used = attachment_service.total_bytes(db)
        db.close()
        payload = b"y" * (1024 * 1024)        # 1MB，加上已用的必然超 1MB
        r = admin.post("/api/attachments", files={"files": ("t.md", payload, "text/markdown")})
        check(r.status_code == 400 and "空间" in r.text,
              f"全局总量满时被拒且说明原因（已用 {used} B，实际 {r.status_code}）")
    finally:
        if old_total is None:
            os.environ.pop("ATTACH_MAX_TOTAL_MB", None)
        else:
            os.environ["ATTACH_MAX_TOTAL_MB"] = old_total

    print("\n⑨ 路径穿越：文件名里带 ../ 不会让它跑出附件目录")
    before = {p.name for p in attachment_service.ATTACH_DIR.glob("*")}
    r = admin.post("/api/attachments",
                   files={"files": ("../../evil.md", b"pwn", "text/markdown")})
    after = {p.name for p in attachment_service.ATTACH_DIR.glob("*")}
    new_files = after - before
    outside = (ROOT / "evil.md").exists() or (_TMP.parent / "evil.md").exists()
    check(r.status_code == 201, f"上传没崩（实际 {r.status_code}）")
    check(not outside, "**附件目录之外**没有出现 evil.md")
    check(all(".." not in n for n in new_files), f"落盘名不含 ..（{new_files}）")

    print("\n⑩ 绑定：附件会挂到反馈上")
    r = admin.post("/api/feedback", json={"content": "这是一条带附件的反馈",
                                          "category": "建议", "attachment_ids": [aid]})
    check(r.status_code == 200, f"提交带附件的反馈（实际 {r.status_code}）")
    from backend.models.database import SessionLocal as _SL2
    from backend.models.admin import FeedbackAttachment as _FA2
    _db2 = _SL2()
    _row = _db2.get(_FA2, aid)
    check(_row is not None and _row.ref_id is not None and _row.source == "feedback",
          f"附件确实绑上了（ref_id={getattr(_row, 'ref_id', None)}、"
          f"source={getattr(_row, 'source', None)}）")
    _db2.close()

    print("\n⑪ 删除规则（必须用**普通用户**走 —— 管理员本来就能删任何附件）")
    # 后面只验业务规则，别让每 IP 日限来捣乱
    os.environ["ATTACH_MAX_PER_IP_PER_DAY"] = "99"
    r = other.post("/api/attachments", files={"files": ("user_own.md", b"x", "text/markdown")})
    aid2 = (r.json().get("items") or [{}])[0].get("id")
    check(r.status_code == 201, f"普通用户上传（实际 {r.status_code}）")
    r = other.post("/api/feedback", json={"content": "普通用户的带附件反馈",
                                          "attachment_ids": [aid2]})
    check(r.status_code == 200, f"普通用户提交（实际 {r.status_code}）")
    r = other.delete(f"/api/attachments/{aid2}")
    check(r.status_code == 400, f"**本人撤不回**已提交的附件（实际 {r.status_code}）")
    r = admin.delete(f"/api/attachments/{aid2}")
    check(r.status_code == 200, f"但站长能删（实际 {r.status_code}）")
    r = other.delete(f"/api/attachments/{aid2}")
    check(r.status_code == 404, f"删掉之后再删 → 404（实际 {r.status_code}）")

    print("\n" + "=" * 62)
    print(f"  通过 {PASSED} 项，失败 {FAILED} 项")
    print("=" * 62)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
