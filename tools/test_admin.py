#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""后台管理 / 封禁 回归测试。

**不需要后端在跑**：用临时 SQLite + TestClient，绝不碰你的真实 backend/data.db。

    python tools/test_admin.py

覆盖十条：
  ① 封号三段式：先证明「这套密码本来能登录」→ 封 → 同一套密码必须被拒（且原因是封禁）
     → 解封 → 又能登录。三段缺一段，断言就没有鉴别力。
  ② 封号立刻踢掉在线会话（旧令牌当场失效）
  ③ IP 封禁：封之前能进 → 封之后 403 → 换一个 IP 照样进（证明不是全站挂了）→ 解封恢复
  ④ 环回地址 127.0.0.1 既不能被写进黑名单，也不会被中间件挡住（防自锁）
  ⑤ 过期的封禁自动不算数
  ⑥ 提问的「答没答上来」判定：高分=已解答 / 低分=未解答 / 没召回=未解答
  ⑦ 用户点「没解决」后，即使分数高也翻成未解答（用户说了算）
  ⑧ 管理接口权限：未登录 401、非管理员 403、管理员 200
  ⑨ 管理员不能封自己
  ⑩ 活跃 IP 聚合能看出「一个 IP 上有多个账号」（共享账号的线索）
  ⑪ 用户主动反馈：落库 / 待处理筛选 / 谁处理的；未登录 401、太短 400
"""
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta

try:  # Windows 管道 / 控制台默认 GBK：中文与 emoji 输出会炸，这里自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ⚠️ 必须在 import backend.* 之前设：配置是模块导入时读的
_tmpdir = tempfile.mkdtemp(prefix="strag_admin_test_")
os.environ["DB_PATH"] = os.path.join(_tmpdir, "test.db")
os.environ["RATE_LIMIT_ENABLED"] = "0"     # 关掉限流，免得干扰封禁判定
os.environ["TRUST_PROXY"] = "1"            # 这样才能用 X-Forwarded-For 模拟不同 IP
os.environ["UNANSWERED_THRESHOLD"] = "0.45"

from backend.models.admin import IpBan, QueryLog                          # noqa: E402
from backend.models.database import SessionLocal, init_db                 # noqa: E402
from backend.models.user import User                                      # noqa: E402
from backend.services import admin_service, auth_service                  # noqa: E402

init_db()

from fastapi.testclient import TestClient                                 # noqa: E402
from backend.main import app                                              # noqa: E402

fails: list[str] = []


def check(cond, msg):
    print(f"  {'✅' if cond else '❌'} {msg}")
    if not cond:
        fails.append(msg)


# ------------------------------------------------------------------ ① ②
def test_ban_flow():
    print("① 封号三段式")
    db = SessionLocal()
    user = auth_service.register(db, "banme", "pw123456")
    _, token, _ = auth_service.login(db, "banme", "pw123456")
    check(bool(token), "【封之前】同一套密码能登录 —— 后面失败才不是因为密码错")

    killed = admin_service.ban_user(db, user, reason="测试：共享账号")
    check(killed >= 1, f"封号时踢掉 {killed} 个在线会话")
    check(auth_service.resolve_token(db, token) is None,
          "【在线会话】拿旧令牌已经解析不出用户（不是等 Cookie 过期）")
    try:
        auth_service.login(db, "banme", "pw123456")
        check(False, "【封之后】同一套密码必须被拒，但它居然登进来了")
    except auth_service.AuthError as e:
        check("停用" in str(e), f"【封之后】被拒且原因是封禁 →「{e}」")

    admin_service.unban_user(db, user)
    _, token2, _ = auth_service.login(db, "banme", "pw123456")
    check(bool(token2), "【解封后】原密码又能登录 —— 证明前面被拒确实是封禁造成的")
    db.close()


# ------------------------------------------------------------------ ③ ④ ⑤
def test_ip_ban():
    print("\n③ IP 封禁（封之前 / 封之后 / 换 IP / 解封后）")
    c = TestClient(app)
    hdr = {"X-Forwarded-For": "203.0.113.66"}
    check(c.get("/api/llm/providers", headers=hdr).status_code == 200,
          "【封之前】该 IP 正常 200")

    db = SessionLocal()
    admin_service.ban_ip(db, "203.0.113.66", reason="测试刷站")
    r = c.get("/api/llm/providers", headers=hdr)
    check(r.status_code == 403, f"【封之后】同一 IP 被挡 → HTTP {r.status_code}")
    check("封禁" in (r.json().get("detail") or ""), "返回的是「被封禁」，不是别的错误")
    check(c.get("/api/llm/providers", headers={"X-Forwarded-For": "198.51.100.9"}).status_code == 200,
          "另一个 IP 仍然正常 —— 证明不是全站挂了")

    row = admin_service.get_active_ban(db, "203.0.113.66")
    admin_service.unban_ip(db, row.id)
    check(c.get("/api/llm/providers", headers=hdr).status_code == 200, "【解封后】又能进")

    print("\n④ 环回地址防自锁")
    try:
        admin_service.ban_ip(db, "127.0.0.1")
        check(False, "封 127.0.0.1 本该被拒绝，但它居然接受并写进黑名单了")
    except ValueError as e:
        check("环回" in str(e), f"拒绝把环回地址写进黑名单 →「{e}」")
    check(c.get("/api/llm/providers", headers={"X-Forwarded-For": "127.0.0.1"}).status_code == 200,
          "127.0.0.1 的请求照样放行（反代场景下全站不至于被一封到底）")

    print("\n⑤ 过期封禁")
    expired = admin_service.ban_ip(db, "203.0.113.88", reason="临时封")
    expired.expires_at = datetime.now() - timedelta(minutes=1)
    db.commit()
    check(admin_service.get_active_ban(db, "203.0.113.88") is None, "过期的封禁自动不算数")
    db.close()


# ------------------------------------------------------------------ ⑥ ⑦ ⑩
def test_query_log():
    print("\n⑥ 提问的「答没答上来」判定")
    db = SessionLocal()
    good = admin_service.log_query(db, ip="10.0.0.1", user=None, kind="search",
                                   query="高分问题", sources_count=3, top_score=0.80)
    check(good.answered is True, "有来源 + 0.80 → 已解答")

    low = admin_service.log_query(db, ip="10.0.0.1", user=None, kind="search",
                                  query="低分问题", sources_count=2, top_score=0.20)
    check(low.answered is False, "有来源但只有 0.20（低于 0.45 阈值）→ 未解答")

    none = admin_service.log_query(db, ip="10.0.0.1", user=None, kind="search",
                                   query="没召回的问题", sources_count=0, top_score=0.0)
    check(none.answered is False, "一条来源都没召回 → 未解答")

    total, rows = admin_service.list_queries(db, only_unanswered=True, page_size=50)
    check(total >= 2 and all(not r.answered for r in rows),
          f"「只看未解答」筛出 {total} 条，且条条都是未解答")

    print("\n⑦ 用户反馈（三档 + 原因）")
    admin_service.mark_feedback(db, good.id, kind="unsolved", reason="答得不对")
    db.refresh(good)
    check(good.answered is False and good.feedback == "unsolved",
          "分数虽高，用户说没解决就翻成未解答（用户判断优先于阈值）")
    check(good.feedback_reason == "答得不对", "用户填的原因原样落库")

    # 第三档：检索到内容了、但内容不相关 —— 这档最容易暴露「召回给错了」
    admin_service.mark_feedback(db, low.id, kind="irrelevant",
                                reason="三条都是正则书里的，和我的问题无关")
    db.refresh(low)
    check(low.feedback == "irrelevant" and low.answered is False,
          "「检索到内容、但不相关」同样计入未解答")
    n_irr, rows_irr = admin_service.list_queries(db, feedback="irrelevant", page_size=50)
    check(n_irr >= 1 and all(r.feedback == "irrelevant" for r in rows_irr),
          f"按 feedback=irrelevant 筛出 {n_irr} 条，条条都是这一档")

    # solved 要能覆盖阈值判断（反方向也要验：不能只会把记录判成"没答上来"）
    admin_service.mark_feedback(db, none.id, kind="solved", reason="自己看懂了")
    db.refresh(none)
    check(none.answered is True,
          "点「有帮助」能把阈值判成未解答的记录翻回已解答 —— 用户说了算，两个方向都通")

    print("\n⑦b 来源摘要（反馈能复现的前提）")
    again = admin_service.log_query(
        db, ip="10.0.0.2", user=None, kind="search", query="带来源的问题",
        sources_count=2, top_score=0.9,
        sources=[{"source": "official", "score": 0.9, "content": "这是第一段的内容"},
                 {"source": "supplement", "score": 0.8, "content": "这是第二段的内容"}])
    digest = json.loads(again.sources_digest or "[]")
    check(len(digest) == 2 and digest[0]["source"] == "official",
          f"来源摘要记下了当时给出的 {len(digest)} 条")
    check(all("preview" in d and d["preview"] for d in digest),
          "每条都带正文摘要（不然只看到分类名，事后说不清是召回错了还是文档没写清楚）")

    print("\n⑩ 活跃 IP 聚合（共享账号线索）")
    u1 = auth_service.register(db, "share1", "pw123456")
    u2 = auth_service.register(db, "share2", "pw123456")
    admin_service.log_query(db, ip="5.6.7.8", user=u1, kind="search", query="aa", sources_count=1, top_score=0.9)
    admin_service.log_query(db, ip="5.6.7.8", user=u2, kind="search", query="bb", sources_count=1, top_score=0.9)
    rows = admin_service.active_ips(db, days=7, limit=50)
    hit = [r for r in rows if r["ip"] == "5.6.7.8"]
    check(bool(hit) and hit[0]["users"] == 2,
          f"同一 IP 上出现 2 个账号（users={hit[0]['users'] if hit else '-'}）—— 共享账号一眼看得出")
    db.close()


# ------------------------------------------------------------------ ⑧ ⑨
def test_admin_api():
    print("\n⑧ 管理接口权限")
    c = TestClient(app)
    check(c.get("/api/admin/overview").status_code == 401, "未登录 → 401")

    db = SessionLocal()
    # 临时库是空的，"banme" 是第一个注册的 → 它已经是管理员
    admin_user = db.query(User).filter_by(username="banme").first()
    check(admin_user is not None and admin_user.is_admin,
          "第一个注册的账号自动是管理员（临时库里的 banme）")
    # ⚠️ 先把要用的标量取出来：session 一关，实例属性就过期，
    #    再去碰 admin_user.id 会抛 DetachedInstanceError。
    admin_id = admin_user.id

    auth_service.register(db, "plain", "pw123456")     # 普通用户
    _, tok_plain, _ = auth_service.login(db, "plain", "pw123456")
    _, tok_admin, _ = auth_service.login(db, "banme", "pw123456")
    db.close()

    r = c.get("/api/admin/overview", headers={"Authorization": f"Bearer {tok_plain}"})
    check(r.status_code == 403, f"非管理员 → 403（实际 {r.status_code}）")

    r = c.get("/api/admin/overview", headers={"Authorization": f"Bearer {tok_admin}"})
    check(r.status_code == 200, f"管理员 → 200（实际 {r.status_code}）")
    if r.status_code == 200:
        data = r.json()
        check("queries_total" in data and "users_total" in data,
              f"概览字段齐全（用户 {data.get('users_total')} 个、提问 {data.get('queries_total')} 条、"
              f"未解答 {data.get('queries_unanswered')} 条）")

    print("\n⑨ 管理员不能封自己")
    r = c.post(f"/api/admin/users/{admin_id}/ban", json={"reason": "手滑"},
               headers={"Authorization": f"Bearer {tok_admin}"})
    check(r.status_code == 400, f"封自己 → 400（实际 {r.status_code}）")
    db = SessionLocal()
    still = db.query(User).filter_by(id=admin_id).first()
    check(still.is_active is True, "自己仍然可以正常使用（没被封）")
    db.close()


def test_user_feedback():
    print("\n⑪ 用户主动反馈（顶部栏按钮）")
    db = SessionLocal()
    u = auth_service.register(db, "fbuser", "pw123456")
    row = admin_service.log_user_feedback(db, user=u, ip="9.9.9.9", category="体验",
                                          content="手机上打开排版乱了", page="/cards")
    check(row is not None and row.content == "手机上打开排版乱了", "反馈内容原样落库")
    check(row.handled is False, "新反馈默认是「待处理」")

    total, unhandled, rows = admin_service.list_user_feedback(db, only_unhandled=True)
    check(total >= 1 and unhandled >= 1 and all(not r.handled for r in rows),
          f"「只看待处理的」筛出 {len(rows)} 条，条条都没处理过")

    admin_service.mark_user_feedback_handled(db, row.id, True, by="banme")
    db.refresh(row)
    check(row.handled is True and row.handled_by == "banme",
          "标记已处理会记住是谁处理的（免得两个人重复看同一条）")

    c = TestClient(app)
    check(c.post("/api/feedback", json={"content": "匿名反馈"}).status_code == 401,
          "未登录提交反馈 → 401 —— 界面藏起来不算权限控制，服务端也要拦")
    _, tok, _ = auth_service.login(db, "fbuser", "pw123456")
    r = c.post("/api/feedback", json={"content": "1"},
               headers={"Authorization": f"Bearer {tok}"})
    check(r.status_code == 400, f"太短的反馈被挡 → {r.status_code}")
    r = c.post("/api/feedback",
               json={"content": "希望支持导出角色卡", "category": "建议", "page": "/cards"},
               headers={"Authorization": f"Bearer {tok}"})
    check(r.status_code == 200, f"登录用户能正常提交 → {r.status_code}")
    db.close()


def main() -> int:
    test_ban_flow()
    test_ip_ban()
    test_query_log()
    test_admin_api()
    test_user_feedback()
    print()
    if fails:
        print(f"❌ 失败 {len(fails)} 项：")
        for f in fails:
            print(f"   · {f}")
        return 1
    print("✅ 后台管理与封禁测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
