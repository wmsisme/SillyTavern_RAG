#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署后冒烟测试：对着**跑起来的实例**（容器或裸机都行）走一遍真实路径。

与其它测试的分工：那些验逻辑与权限，这个验"**部署出来到底能不能用**"——
2026-10-06 首次在容器里跑，一次抓出 4 个只有真部署才暴露的问题：
  ① 走 API 时 `_retrieve_raw` 仍无条件预热本机模型 → 精简镜像（无 torch）里检索直接 500
  ② `StaticFiles(html=True)` 不做 SPA 兜底 → 直接打开 /login、/cards 这种前端路由会 404
  ③（上面两条修完后）数据卷持久化、跨容器重建后账号仍在 ✓
  ④ 打错的 API 路径曾被静态挂载吞成 200 HTML

用法：python tools/test_deployed_site.py [--base http://127.0.0.1:8000]
"""
import argparse
import sys
import time

import httpx

try:  # Windows 管道 / 控制台默认 GBK：中文与 emoji 输出会炸，这里自保一次
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


fails: list[str] = []


def check(cond, msg):
    print(f"  {'✅' if cond else '❌'} {msg}")
    if not cond:
        fails.append(msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    BASE = args.base.rstrip("/")

    print("① 健康检查（容器的 HEALTHCHECK 用的就是它）")
    try:
        r = httpx.get(f"{BASE}/health", timeout=30)
    except httpx.ConnectError:
        print(f"❌ 连不上 {BASE} —— 先把实例跑起来（docker compose up -d）")
        return 2
    h = r.json()
    check(r.status_code == 200, f"HTTP {r.status_code}")
    check(isinstance(h.get("chroma_count"), int) and h["chroma_count"] > 0,
          f"索引条数 = {h.get('chroma_count')}（说明 RAG 卷挂对了、不是空库）")

    print("\n② 前端（构建产物 + SPA 深链接兜底）")
    r = httpx.get(f"{BASE}/", timeout=30)
    check(r.status_code == 200 and "<div id=\"root\">" in r.text, f"GET / 返回页面（{len(r.text)} 字节）")
    r = httpx.get(f"{BASE}/login", timeout=30)
    check(r.status_code == 200, f"深链接 /login 直接可开（HTTP {r.status_code}）—— 上线后分享的链接能不能用就看这条")

    print("\n③ 公开接口 & 打错的接口")
    r = httpx.get(f"{BASE}/api/llm/providers", timeout=30)
    check(r.status_code == 200 and len(r.json().get("providers", [])) == 7,
          f"平台清单 {len(r.json().get('providers', []))} 个")
    r = httpx.get(f"{BASE}/api/这个接口不存在", timeout=30)
    check(r.status_code == 404, f"打错的 API 返回 404（实际 {r.status_code}，不能是 200 的 HTML）")

    print("\n④ 注册 + 登录态 + 数据隔离")
    uname = f"smoke{int(time.time()) % 1000000}"
    c = httpx.Client(base_url=BASE, timeout=60)
    r = c.post("/api/auth/register", json={"username": uname, "password": "pw123456"})
    check(r.status_code == 201, f"注册 {uname}（HTTP {r.status_code}）")
    r = c.get("/api/auth/me")
    check(r.status_code == 200 and r.json().get("username") == uname, "带 Cookie 能问到本人")
    r = c.get("/api/cards")
    check(r.status_code == 200 and r.json().get("total") == 0, "新账号名下 0 张卡")
    r = httpx.get(f"{BASE}/api/cards", timeout=30)
    check(r.status_code == 401, f"匿名访问私有接口 → 401（实际 {r.status_code}）")

    print("\n⑤ 真正的检索（同时验证索引与出网）")
    r = httpx.post(f"{BASE}/api/rag/search",
                   json={"query": "世界书的递归扫描怎么用？", "top_k": 3}, timeout=180)
    check(r.status_code == 200, f"HTTP {r.status_code}（500 的话多半是 provider 配错或装漏了依赖）")
    res = r.json().get("results", []) if r.status_code == 200 else []
    check(len(res) == 3, f"返回 {len(res)} 条")
    if res:
        top = str(res[0].get("content") or "")[:50].replace("\n", " ")
        check("世界" in top or "递归" in top, f"top-1 切题：{top}")

    print()
    if fails:
        print(f"❌ 失败 {len(fails)} 项：" + "；".join(fails))
        return 1
    print("✅ 部署冒烟测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
