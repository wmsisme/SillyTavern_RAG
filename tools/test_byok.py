#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BYOK 回归测试：验证「没带 key 明确报错 / 带了 key 真能出结果」。

默认只跑**不花钱**的部分（平台清单、无凭证报错、假 key 被拒）；
加 --live 才会用 .env 里的 DEEPSEEK_API_KEY 发两次真实调用（约 ¥0.002）。

不新建账号：给已有账号插一个临时会话令牌，跑完删除。

⚠️ **对着容器跑时要让 DB_PATH 指向容器那份库**，否则本脚本插的令牌容器不认识
（表现是一堆莫名其妙的 401「请先登录」）：

    $env:DB_PATH='<仓库目录>/data/data.db'; python tools/test_byok.py

本地开发（后端直接跑在宿主机）时不用设，默认就是 backend/data.db ✓

前置：后端在跑。用法：python tools/test_byok.py [--live] [--base http://127.0.0.1:8000]
"""
import argparse
import datetime
import json
import pathlib
import secrets
import sys

import httpx

try:  # Windows 管道 / 控制台默认 GBK：中文与 emoji 输出会炸，这里自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.models.database import SessionLocal          # noqa: E402
from backend.models.user import SessionToken, User, UserLLMSettings  # noqa: E402

fails: list[str] = []


def check(cond, msg):
    print(f"  {'✅' if cond else '❌'} {msg}")
    if not cond:
        fails.append(msg)


def env(k: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith(k + "="):
            return line.split("=", 1)[1].strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--live", action="store_true", help="真发两次大模型调用（会花一点点钱）")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    db = SessionLocal()
    user = db.query(User).order_by(User.id).first()
    if not user:
        print("❌ 库里没有账号，先在界面上注册一个再来跑")
        return 2
    token = "test-" + secrets.token_urlsafe(24)
    db.add(SessionToken(token=token, user_id=user.id,
                        expires_at=datetime.datetime.now() + datetime.timedelta(hours=1)))
    db.commit()
    print(f"（临时会话已挂到 {user.username}(id={user.id})，跑完删除）\n")
    client = httpx.Client(base_url=f"{base}/api", cookies={"strag_session": token}, timeout=300)
    try:
        print("① 平台清单（公开接口）")
        try:
            r = httpx.get(f"{base}/api/llm/providers", timeout=30)
        except httpx.ConnectError:
            print(f"❌ 连不上后端 {base} —— 先把服务起起来")
            return 2
        provs = r.json().get("providers", [])
        ids = {p["id"] for p in provs}
        check(r.status_code == 200, f"HTTP {r.status_code}")
        check(len(provs) == 7, f"共 {len(provs)} 个平台")
        check({"deepseek", "siliconflow", "moonshot", "dashscope", "volcengine",
               "openai", "anthropic"} <= ids, f"7 家都在：{sorted(ids)}")

        print("\n② 没带凭证 → 必须明确报错，绝不回落到服务端 key")
        r = client.post("/cards/generate/preview", json={"description": "测试"})
        check(r.status_code == 400, f"HTTP {r.status_code}（期望 400）")
        check("API Key" in (r.json().get("detail") or ""),
              f"错误信息可读：{(r.json().get('detail') or '')[:50]}")
        r = client.post("/rag/ask", json={"query": "世界书怎么用"})
        check(r.status_code == 400, f"/rag/ask 也是 400（实际 {r.status_code}）")

        print("\n③ 伪造 key → 由平台拒绝（说明凭证真的透传到了平台）")
        r = client.post("/cards/generate/preview", json={"description": "x"},
                        headers={"X-LLM-Provider": "deepseek", "X-LLM-Key": "sk-not-a-real-key"},
                        timeout=120)
        check(r.status_code != 200 or "error" in json.dumps(r.json(), ensure_ascii=False),
              "假 key 没能成功")

        print("\n④ 「测试连接」接口（不需要登录，前端设置框直接调它）")
        r = httpx.post(f"{base}/api/llm/test", timeout=60)
        check(r.status_code == 400, f"没带凭证 → 400（实际 {r.status_code}）")
        r = httpx.post(f"{base}/api/llm/test", timeout=120,
                       headers={"X-LLM-Provider": "deepseek", "X-LLM-Key": "sk-not-a-real-key"})
        body = r.json()
        check(r.status_code == 200 and body.get("ok") is False,
              "假 key → HTTP 200 + {ok:false}（让前端能显示成人话，而不是一个 500）")
        check(bool(body.get("error")), f"带回了可读错误：{str(body.get('error'))[:60]}")

        if args.live:
            key = env("DEEPSEEK_API_KEY")
            if not key:
                check(False, ".env 里没有 DEEPSEEK_API_KEY，没法跑 --live")
            else:
                h = {"X-LLM-Provider": "deepseek", "X-LLM-Key": key, "X-LLM-Model": "deepseek-chat"}
                print("\n⑤ 「测试连接」用真 key → 应当 ok:true")
                r = httpx.post(f"{base}/api/llm/test", headers=h, timeout=120)
                b = r.json()
                check(b.get("ok") is True, f"连接成功：{b.get('provider')} / {b.get('model')} → {b.get('reply')}")
                print("\n⑥ 带真凭证：生成角色卡")
                r = client.post("/cards/generate/preview",
                                json={"description": "一个叫小蓝的蓝鲸助手"},
                                headers=h, timeout=300)
                check(r.status_code == 200 and bool(r.json().get("name")),
                      f"生成了角色名：{r.json().get('name')}")
                print("\n⑦ 带真凭证：检索问答")
                r = client.post("/rag/ask", json={"query": "世界书的递归扫描怎么用？"},
                                headers=h, timeout=600)
                ans = r.json().get("answer") or ""
                check(r.status_code == 200 and len(ans) > 20, f"答案长度 {len(ans)}")
                check(bool(r.json().get("sources")),
                      f"带回 {len(r.json().get('sources') or [])} 条来源")
        else:
            print("\n⑤⑥⑦ 真实调用已跳过（加 --live 才跑，会花约 ¥0.002）")

        print("\n⑧ 「Key 存进账号」：加密落库、原文不回传、不带 header 也能用")
        # 运行时拼出来：源码里不留「sk- + 长串」这种密钥形态的字面量
        # （不然它会被密钥扫描器当成真 Key 报出来，白白吓人）
        FAKE = "sk-" + "account-test" + "-1234567890" + "abcdef"
        r = client.put("/llm/settings",
                       json={"provider": "deepseek", "api_key": FAKE, "model": "deepseek-chat"})
        check(r.status_code == 200 and r.json().get("configured") is True,
              f"保存成功（HTTP {r.status_code}）")
        check(FAKE not in json.dumps(r.json(), ensure_ascii=False), "响应里**没有** Key 原文")
        check((r.json().get("masked_key") or "").startswith("sk-acc"),
              f"只回打码形态：{r.json().get('masked_key')}")

        db.expire_all()
        row = db.query(UserLLMSettings).filter(UserLLMSettings.user_id == user.id).first()
        check(row is not None, "库里确实写入了这行配置")
        check(row is not None and FAKE not in (row.api_key_enc or ""),
              "**库里存的是密文**，不含 Key 原文")
        check(row is not None and len(row.api_key_enc or "") > 40,
              "密文长度正常（Fernet 输出）")

        r = client.get("/llm/settings")
        check(r.json().get("decryptable") is True, "能正常解开（decryptable=true）")
        masked_before = r.json().get("masked_key")

        # 传空 api_key = 保留原来那把（只改模型），不能把 Key 抹掉
        r = client.put("/llm/settings",
                       json={"provider": "deepseek", "api_key": "", "model": "deepseek-reasoner"})
        check(r.status_code == 200, f"只改模型、不重填 Key（HTTP {r.status_code}）")
        check(r.json().get("masked_key") == masked_before,
              f"原 Key 保住了（{r.json().get('masked_key')}）")
        check(r.json().get("model") == "deepseek-reasoner", "模型确实改了")

        # 不带任何 X-LLM-* 头，只带会话 Cookie → 应当自动用账号里存的那把
        r = httpx.post(f"{base}/api/llm/test", cookies={"strag_session": token}, timeout=120)
        check(r.status_code == 200 and r.json().get("ok") is False,
              "没带请求头时，后端自动回落到账号里存的 Key（假 Key 被平台拒，说明真的用了它）")

        r = client.delete("/llm/settings")
        check(r.status_code == 200 and r.json().get("configured") is False, "删除后恢复未配置")
        r = httpx.post(f"{base}/api/llm/test", cookies={"strag_session": token}, timeout=60)
        check(r.status_code == 400, f"删掉后无凭证 → 400（实际 {r.status_code}）")
    finally:
        db.query(SessionToken).filter(SessionToken.token == token).delete()
        db.commit()
        db.close()
        client.close()
        print("\n（临时会话令牌已删除）")

    print()
    if fails:
        print(f"❌ 失败 {len(fails)} 项：" + "；".join(fails))
        return 1
    print("✅ BYOK 回归测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
