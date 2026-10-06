#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""并发测试：证明"一个人提问不会卡住其他人"。

背景：`/api/rag/*` 与 `/api/tools/*` 内部是同步阻塞调用（检索 + API 精排 + 大模型生成）。
如果写在 `async def` 里，它们会把**整个事件循环**卡住 —— 表现是"只要有人在搜索，
其他人连页面静态资源都要排队"。改成普通 `def` 后由 FastAPI 丢进线程池并发执行。

判据（两条都要过，且都有宽裕余量）：
  ① 8 个并发搜索的总耗时 ≈ 单个搜索（并行），而不是 8 倍（串行）
  ② 在搜索风暴期间，/health 依然秒回（事件循环没被占住）

用法：python tools/test_concurrency.py [--base http://127.0.0.1:8000]
"""
import argparse
import statistics
import sys
import threading
import time

import httpx

fails: list[str] = []


def check(cond, msg):
    print(f"  {'✅' if cond else '❌'} {msg}")
    if not cond:
        fails.append(msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--n", type=int, default=8)
    args = ap.parse_args()
    base = args.base.rstrip("/")

    try:
        httpx.get(f"{base}/health", timeout=5)
    except httpx.ConnectError:
        print(f"❌ 连不上后端 {base} —— 先把服务起起来")
        return 2

    q = {"query": "世界书的递归扫描怎么用？", "top_k": 5}

    print("预热一次（让向量库/连接先就绪）")
    t0 = time.time()
    r = httpx.post(f"{base}/api/rag/search", json=q, timeout=120)
    single = time.time() - t0
    if r.status_code != 200:
        print(f"❌ 预热失败：HTTP {r.status_code} {r.text[:120]}")
        return 2
    print(f"  单次搜索耗时 {single:.2f}s\n")

    print(f"① {args.n} 个并发搜索：总耗时应接近单次（并行），而不是 {args.n} 倍（串行）")
    results: list = []
    lock = threading.Lock()

    def one():
        t = time.time()
        try:
            rr = httpx.post(f"{base}/api/rag/search", json=q, timeout=180)
            code = rr.status_code
        except Exception as e:
            code = f"异常 {type(e).__name__}"
        with lock:
            results.append((code, time.time() - t))

    # ② 同时不停地打 /health，看事件循环有没有被占住
    health_lat: list = []
    stop = threading.Event()

    def poll_health():
        while not stop.is_set():
            t = time.time()
            try:
                httpx.get(f"{base}/health", timeout=10)
                health_lat.append(time.time() - t)
            except Exception:
                health_lat.append(9.99)
            time.sleep(0.05)

    hp = threading.Thread(target=poll_health, daemon=True)
    hp.start()

    t0 = time.time()
    threads = [threading.Thread(target=one) for _ in range(args.n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    burst = time.time() - t0
    stop.set()
    hp.join(timeout=3)

    codes = [c for c, _ in results]
    check(all(c == 200 for c in codes), f"{args.n} 个请求全部 200（实际 {codes}）")
    check(burst < single * args.n * 0.5,
          f"并发总耗时 {burst:.2f}s < 串行预期的一半（{single * args.n:.2f}s × 0.5）→ 确实并行")
    print(f"     各请求耗时：{', '.join(f'{d:.2f}s' for _, d in results)}")

    print("\n② 搜索风暴期间 /health 的响应")
    if health_lat:
        worst = max(health_lat)
        med = statistics.median(health_lat)
        check(worst < 1.0, f"/health 最慢 {worst*1000:.0f}ms（中位 {med*1000:.0f}ms，共 {len(health_lat)} 次）"
                           " → 事件循环没被占住")
    else:
        check(False, "没采到 /health 样本")

    print()
    if fails:
        print(f"❌ 失败 {len(fails)} 项：" + "；".join(fails))
        return 1
    print("✅ 并发测试通过：请求是并行的，事件循环也没被占住")
    return 0


if __name__ == "__main__":
    sys.exit(main())
