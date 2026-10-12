#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手机端（窄屏）显示检查 —— 改完界面跑一遍，别靠肉眼猜。

为什么要有这个脚本（2026-10-12 达铭反馈「手机端显示有问题」那次）：
桌面版布局被硬塞进手机宽度时，症状很隐蔽 —— 侧面导航栏不收会把正文挤成一列几个字，
**手机浏览器还会把 layout viewport 撑大再整体缩放**（实测 390 → 478），
用户只感觉"字变小了、排版挤成一团"，而在桌面上一切正常。

它检查四件事（对应四类最常见的窄屏坑）：
  ① 文档宽度 vs 视口宽度 —— 不相等就是横向溢出；
  ② 右边界超出视口的元素（**排除** `.ant-table-content` 这类"本就可横向滚动"的容器）；
  ③ 必要时截图，人眼复核观感（量出来的数字不能替代"好不好看"）；
  ④ 需要登录的页面用 --user/--password 传账号，脚本自己登录再逐页检查。

用法：
    python tools/check_mobile.py http://127.0.0.1:8000
    python tools/check_mobile.py https://站点 --pages /,/cards,/admin
    python tools/check_mobile.py http://127.0.0.1:8000 --user 我的号 --password '密码' --pages /,/cards
    python tools/check_mobile.py http://127.0.0.1:8000 --device "Pixel 5" --out tmp/mobile

退出码：全部页面都没有溢出 → 0；任意一页溢出 → 1（可以直接当门禁用）。
"""
import argparse
import sys
from pathlib import Path

try:      # Windows 控制台默认 GBK，中文与 emoji 会直接把脚本打崩
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from playwright.sync_api import sync_playwright


# 只报"真的会把布局撑坏"的元素：表格内层本来就是可横向滚动的，不算
DIAG = """() => {
  const vw = window.innerWidth;
  const bad = [];
  document.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    if (el.closest('.ant-table-content, .ant-table-body')) return;   // 表格可滑动，正常
    if (el.closest('.ant-tabs-nav')) return;                          // 页签条自带滚动，正常
    if (r.right > vw + 1 || r.left < -1) {
      bad.push({
        tag: el.tagName,
        w: Math.round(r.width),
        left: Math.round(r.left),
        right: Math.round(r.right),
        cls: (typeof el.className === 'string' ? el.className : '').slice(0, 50),
        text: (el.innerText || '').trim().slice(0, 24).replace(/\\n/g, ' '),
      });
    }
  });
  return { vw, doc: document.documentElement.scrollWidth, bad: bad.slice(0, 10) };
}"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="http://127.0.0.1:8000", help="站点地址")
    ap.add_argument("--pages", default="/,/toolbox,/login", help="要检查的路径，逗号分隔")
    ap.add_argument("--device", default="iPhone 13", help="Playwright 设备名（如 iPhone 13 / Pixel 5）")
    ap.add_argument("--user", default="", help="需要登录时：用户名")
    ap.add_argument("--password", default="", help="需要登录时：密码（只在本机用，不写进任何文件）")
    ap.add_argument("--out", default="tmp/mobile", help="截图目录")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pages = [p.strip() for p in args.pages.split(",") if p.strip()]

    fails = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        device = p.devices.get(args.device)
        if device is None:
            print(f"❌ 不认识的设备名：{args.device}（可用的见 playwright 的 p.devices）")
            return 2
        ctx = browser.new_context(**device)
        page = ctx.new_page()

        if args.user and args.password:
            print(f"① 先登录（{args.user}）")
            page.goto(base + "/login", wait_until="load", timeout=60000)
            page.wait_for_timeout(1500)
            # ⚠️ antd 的 Tabs 会把未激活页签的表单也留在 DOM 里，选择器必须点名 :visible
            page.locator('input[placeholder="用户名"]:visible').first.fill(args.user)
            page.locator('input[placeholder*="密码"]:visible').first.fill(args.password)
            page.locator('button[type="submit"]:visible').first.click()
            page.wait_for_timeout(3500)
            print(f"   登录后停在：{page.url}")
        else:
            print("① 未登录模式（只检查公开页面）")

        print(f"\n② 逐页检查（设备：{args.device} = {device.get('viewport')}）")
        for path in pages:
            url = base + path
            name = path.strip("/").replace("/", "_") or "home"
            try:
                page.goto(url, wait_until="load", timeout=60000)
                page.wait_for_timeout(2200)
                d = page.evaluate(DIAG)
                overflow = d["doc"] - d["vw"]
                ok = overflow <= 1 and not d["bad"]
                tag = "✅" if ok else "❌"
                print(f"  {tag} {path:16} 视口 {d['vw']} / 文档 {d['doc']}"
                      + ("" if overflow <= 1 else f"  ← 横向溢出 {overflow}px"))
                for o in d["bad"]:
                    print(f"      超出视口：{o['tag']} w={o['w']} right={o['right']} "
                          f"class={o['cls']!r} text={o['text']!r}")
                if not ok:
                    fails.append(f"{path}（视口 {d['vw']} / 文档 {d['doc']}）")
                page.screenshot(path=str(out / f"mobile_{name}.png"), full_page=False)
            except Exception as e:
                print(f"  ❌ {path:16} 打不开：{type(e).__name__}: {e}")
                fails.append(f"{path}（打不开）")
        browser.close()

    print(f"\n截图在 {out}/。")
    if fails:
        print(f"❌ {len(fails)} 个页面有问题：" + "；".join(fails))
        return 1
    print("✅ 所有页面都无横向溢出。**别只看这个结论** —— 打开截图复核一下观感，"
          "数值检查抓不到「排得难看」（比如标题折行、卡片被压扁）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
