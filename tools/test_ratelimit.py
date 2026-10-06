#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 IP 限流的测试（进程内跑，不碰正在运行的服务、也不花钱）。

分两段：
  ① 纯逻辑：SlidingWindow 的窗口行为、IP 隔离、两个桶互不影响
  ② 走真实 HTTP（TestClient，限额临时调到 3/分钟）：贵接口第 4 次该 429、
     非贵接口不受影响、登录注册走更严的那一档

为什么不在真服务上打 51 次：那会把本机 IP 的 60 秒窗口占满，
紧接着跑别的测试（比如工具箱回归）就会莫名 429 —— 用低限额的进程内实例最干净。
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ⚠️ 必须在 import backend.* 之前设：限流参数是模块导入时读的环境变量
os.environ["RATE_LIMIT_PER_MIN"] = "3"
os.environ["RATE_LIMIT_AUTH_PER_MIN"] = "2"
os.environ["TRUST_PROXY"] = "1"        # 这样能用 X-Forwarded-For 模拟不同 IP
os.environ["RATE_LIMIT_ENABLED"] = "1"

from backend.api.ratelimit import SlidingWindow, client_ip, _match, HEAVY_PREFIXES, AUTH_PREFIXES  # noqa: E402

fails: list[str] = []


def check(cond, msg):
    print(f"  {'✅' if cond else '❌'} {msg}")
    if not cond:
        fails.append(msg)


def test_sliding_window() -> None:
    print("① 滑动窗口本身")
    w = SlidingWindow("t", 3)
    t = 1000.0
    r1 = [w.hit("ip-a", now=t + i * 0.1)[0] for i in range(3)]
    check(r1 == [True, True, True], "前 3 次放行")
    ok, retry = w.hit("ip-a", now=t + 0.4)
    check(ok is False and retry >= 1, f"第 4 次被拒，并给出等待秒数（retry_after={retry}）")
    check(w.hit("ip-b", now=t + 0.5)[0] is True, "另一个 IP 不受影响（按 IP 分桶）")
    check(w.hit("ip-a", now=t + 61)[0] is True, "窗口滑过 60 秒后恢复放行")

    big = SlidingWindow("t2", 50)
    for i in range(50):
        assert big.hit("ip-c", now=t + i * 0.5)[0] is True
    check(big.hit("ip-c", now=t + 30)[0] is False, "50 次上限本身是准的（第 51 次被拒）")

    print("② 路径分类：哪些算'贵的'")
    check(_match("/api/rag/search", HEAVY_PREFIXES), "/api/rag/search 算贵的")
    check(_match("/api/tools/jsonl-novel-converter", HEAVY_PREFIXES), "工具箱算贵的")
    check(_match("/api/cards/generate/preview", HEAVY_PREFIXES), "AI 生成算贵的")
    check(not _match("/api/cards/12/image", HEAVY_PREFIXES), "卡片图片**不算**（否则翻页就被限）")
    check(not _match("/api/cards", HEAVY_PREFIXES), "卡片列表不算")
    check(not _match("/api/llm/providers", HEAVY_PREFIXES), "平台清单不算")
    check(_match("/api/auth/login", AUTH_PREFIXES), "登录走单独那一档")


def test_over_http() -> None:
    print("\n③ 走真实 HTTP（限额临时调到 3/分钟）")
    from fastapi.testclient import TestClient
    from backend.main import app          # 不 with：不进 lifespan，避免加载向量库

    c = TestClient(app)
    files = {"file": ("t.jsonl", b'{"name":"A","is_user":true,"mes":"hi"}', "application/jsonl")}
    hdr = {"X-Forwarded-For": "203.0.113.9"}

    codes = [c.post("/api/tools/jsonl-novel-converter", files=files, headers=hdr).status_code
             for _ in range(3)]
    check(codes == [200, 200, 200], f"贵接口前 3 次都 200（实际 {codes}）")

    r = c.post("/api/tools/jsonl-novel-converter", files=files, headers=hdr)
    check(r.status_code == 429, f"第 4 次被限流 → 429（实际 {r.status_code}）")
    check("Retry-After" in r.headers, f"带 Retry-After 头（{r.headers.get('Retry-After')}s）")
    check("每分钟" in (r.json().get("detail") or ""), f"错误信息说得清：{(r.json().get('detail') or '')[:46]}")

    other = c.get("/api/llm/providers", headers={"X-Forwarded-For": "198.51.100.7"})
    check(other.status_code == 200, "换一个 IP 立刻可用（限的是 IP，不是全站）")
    light = c.get("/api/llm/providers", headers=hdr)
    check(light.status_code == 200, "**同一个 IP** 打非贵接口仍然 200（范围没扩大）")

    print("     登录档（限额 2/分钟）")
    acodes = [c.post("/api/auth/login", json={"username": "nobody", "password": "x"},
                     headers={"X-Forwarded-For": "203.0.113.55"}).status_code for _ in range(2)]
    check(all(x == 400 for x in acodes), f"前 2 次是正常业务失败 400（实际 {acodes}）")
    r = c.post("/api/auth/login", json={"username": "nobody", "password": "x"},
               headers={"X-Forwarded-For": "203.0.113.55"})
    check(r.status_code == 429, f"第 3 次被限流（实际 {r.status_code}）")


def main() -> int:
    test_sliding_window()
    test_over_http()
    print()
    if fails:
        print(f"❌ 失败 {len(fails)} 项：" + "；".join(fails))
        return 1
    print("✅ 限流测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
