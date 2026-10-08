"""给 README 截图：在**隔离实例**上造演示数据 → 逐页截图。

另一条理由是：不能碰真实库里的真实数据。
所以流程是：复制公网版源码 → 构建 → 用独立 DB_PATH 起一个实例 → 在这里注册演示账号、
造演示卡与世界书 → 截图 → 用完把整个临时实例删掉。

用法：
    python tools/shot_readme.py --base http://127.0.0.1:8001 --out docs/screenshots

注意：演示账号是**该实例的第一个注册者**，按设计自动成为管理员，
所以后台管理页也能截到（这是本脚本要跑在空库实例上的原因）。
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DEMO_USER = "demo_viewer"
DEMO_PASS = "Demo#2026viewer"

CARDS = [
    {
        "name": "星轨占卜师 · 薇拉",
        "age": "外观 24 岁",
        "gender": "女",
        "species": "人类（星纹血脉）",
        "occupation": "占卜师",
        "appearance": "银灰色长发里缀着细碎星点，右眼下有一枚浅蓝的星形印记",
        "personality": "温和耐心，说话慢。不轻易下断言，习惯把选择权交回对方手里。",
        "background": "出身北境观星台，十七岁独自南下，在钟楼街角开了间只有两张椅子的占卜铺。",
        "description": "在群星之间读命运的人。她从不告诉你「一定会怎样」，只告诉你「现在哪条路更亮」。",
        "tags": ["奇幻", "治愈", "占卜"],
        "first_message": "（她把桌上的星盘轻轻转了半圈）坐吧。今晚的星象不太安分——我猜你不是来问天气的。",
        "has_status_bar": True,
        "status_bar_content": '[{"label":"心情","value":"平静"},{"label":"好感度","value":"30"}]',
    },
    {
        "name": "赛博侦探 · 林夜",
        "age": "29",
        "gender": "男",
        "species": "人类（义体化 43%）",
        "occupation": "私家侦探",
        "appearance": "黑色短发，左臂是旧型号义体，常年穿一件洗褪色的风衣",
        "personality": "话少、爱吐槽，对细节近乎偏执。嘴上说不管闲事，最后还是会把案子查到底。",
        "background": "前新港区刑侦科警员，因为一份不肯签字的报告离了职，现在靠接零散的委托过活。",
        "description": "在新港区的雨夜里找真相的人。收费不高，但从不接受「别往下查了」这种建议。",
        "tags": ["赛博朋克", "推理", "悬疑"],
        "first_message": "（他把烟摁灭在旧茶杯里）委托费先付一半。另一半，等我把人找出来再说。",
    },
    {
        "name": "魔法学院讲师 · 塞德里克",
        "age": "37",
        "gender": "男",
        "species": "半精灵",
        "occupation": "符文学讲师",
        "appearance": "深绿色学者长袍，袖口总是沾着墨水和研磨过的符粉",
        "personality": "严厉但护短。上课时不许任何人碰笔，下课却会留下来把每个问题讲到听懂为止。",
        "background": "在灰塔学院教了十二年符文学，拒绝过三次升迁——他说离学生越远，教的东西就越没用。",
        "description": "把「你写错了」说得像「你差点就对了」的讲师。",
        "tags": ["学院", "奇幻", "师生"],
        "first_message": "（他头也不抬地推过来一张纸）把你昨天那道符文画一遍。别翻书——我要看你自己记住了多少。",
    },
    {
        "name": "深夜食堂店主 · 阿澈",
        "age": "31",
        "gender": "男",
        "species": "人类",
        "occupation": "小餐馆老板",
        "appearance": "亚麻围裙，手指上有几道旧烫伤，笑起来右脸颊有个酒窝",
        "personality": "话不多，先递一碗热汤再问你怎么了。从不追问客人不想说的事。",
        "background": "店开在巷子最里头，只做晚上十点到凌晨三点。菜单写在墙上，一共七道菜。",
        "description": "深夜的收容所。谁都可以坐下来，吃完再决定要不要说话。",
        "tags": ["日常", "治愈", "都市"],
        "first_message": "（他把一碗汤推到你面前，汤面还冒着热气）先喝口热的。别的，等你想说的时候再说。",
    },
]

WORLD_BOOKS = [
    {
        "name": "星轨大陆 · 世界设定集",
        "description": "北境观星台、群星教团与星纹血脉的基础设定，供奇幻题材角色卡使用。",
        "tags": ["奇幻", "设定集"],
        "entries": [
            {"key": "观星台", "content": "建在断崖之上的白色高塔，塔顶的青铜星盘直径三十米。观星者在这里记录星轨的偏移，并以此推算人间的变动。", "comment": "地理", "depth": 1, "trigger_words": ["观星台", "星盘"]},
            {"key": "星纹血脉", "content": "极少数人天生带有星形印记，能感知他人命运的走向。印记越清晰，感知越强，但寿命也越短。", "comment": "体系", "depth": 1, "trigger_words": ["星纹", "血脉", "印记"]},
            {"key": "群星教团", "content": "认为星轨不可违逆的教派。他们供奉的不是神，而是一份被抄写了七百年的星象记录。", "comment": "势力", "depth": 1, "trigger_words": ["教团", "群星教团"]},
        ],
    },
    {
        "name": "新港区 · 赛博都市设定",
        "description": "赛博朋克题材的背景资料：城区结构、义体黑市与雨夜经济。",
        "tags": ["赛博朋克", "设定集"],
        "entries": [
            {"key": "新港区", "content": "填海造出来的第九区，平均每年下沉两厘米。上层是玻璃幕墙的写字楼，下层是终年不见阳光的管线城。", "comment": "地理", "depth": 1, "trigger_words": ["新港区", "第九区"]},
            {"key": "义体黑市", "content": "藏在旧地铁三号线尽头的地下交易场，卖二手义体，也卖别人的记忆。只收现金，不问来路。", "comment": "场所", "depth": 1, "trigger_words": ["义体", "黑市"]},
        ],
    },
]

# 用真实用户会问的问题去检索一遍，让后台的「提问记录」有内容可展示
DEMO_QUERIES = [
    "如何用正则替换 AI 回复里的特定文字？",
    "世界书的递归扫描是什么？",
    "SillyTavern 的预设文件放在哪里？",
    "怎么配置 OpenRouter API 连接？",
    "CSS 自定义主题怎么设置？",
    "角色卡里的第一条消息起什么作用？",
    "怎么让 AI 记住更长的对话？",
]


def log(msg: str) -> None:
    print(f"[shot] {msg}", flush=True)


def api_session(base: str) -> requests.Session:
    """注册演示账号（该实例的第一个注册者 → 自动成为管理员）并返回带 Cookie 的会话。"""
    s = requests.Session()
    r = s.post(f"{base}/api/auth/register",
               json={"username": DEMO_USER, "password": DEMO_PASS, "invite_code": ""},
               timeout=30)
    if r.ok:                      # 2xx 都算成功（新用户注册可能返回 201）
        log(f"已注册演示账号 {DEMO_USER}（空库首注册者 → 管理员）")
        return s
    r2 = s.post(f"{base}/api/auth/login",
                json={"username": DEMO_USER, "password": DEMO_PASS}, timeout=30)
    if r2.status_code != 200:
        raise SystemExit(f"既不能注册也不能登录演示账号：{r.status_code} {r.text[:200]}")
    log(f"演示账号已存在，直接登录：{DEMO_USER}")
    return s


def seed(s: requests.Session, base: str) -> None:
    """造演示数据。已有的先跳过（幂等，方便反复跑）。"""
    existing = {c["name"] for c in s.get(f"{base}/api/cards", params={"page_size": 100},
                                        timeout=30).json().get("items", [])}
    for c in CARDS:
        if c["name"] in existing:
            continue
        r = s.post(f"{base}/api/cards", json=c, timeout=60)
        log(f"建卡 {c['name']} → {r.status_code}")

    wb = {w["name"] for w in s.get(f"{base}/api/worldbooks", params={"page_size": 100},
                                  timeout=30).json().get("items", [])}
    for w in WORLD_BOOKS:
        if w["name"] in wb:
            continue
        r = s.post(f"{base}/api/worldbooks", json=w, timeout=60)
        log(f"建世界书 {w['name']} → {r.status_code}")

    logs = s.get(f"{base}/api/admin/queries", params={"limit": 1}, timeout=30)
    have = 0
    if logs.status_code == 200:
        body = logs.json()
        have = body.get("total", 0) if isinstance(body, dict) else len(body)
    if have < 3:
        for q in DEMO_QUERIES:
            r = s.post(f"{base}/api/rag/search", json={"query": q, "top_k": 5}, timeout=90)
            log(f"检索留痕：{q[:18]}… → {r.status_code}")
            time.sleep(0.6)
    else:
        log(f"已有 {have} 条提问记录，跳过检索留痕")


def playwright_cookies(s: requests.Session, base: str) -> list:
    """把 requests 的会话 Cookie 转成 playwright 的格式。

    少了这一步，浏览器就是匿名身份 —— 卡片页 / 世界书页 / 后台页会一律
    截成「需要登录」的锁屏插画（第一次跑就踩了这个，白截了 6 张）。
    """
    host = base.split("//", 1)[1].split(":")[0].rstrip("/")
    return [{"name": c.name, "value": c.value, "domain": host, "path": c.path or "/"}
            for c in s.cookies]


def shoot(base: str, out: Path, api_key: str, cookies: list) -> None:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    V = {"width": 1440, "height": 900}

    def snap(page, name: str, full: bool = False) -> None:
        page.wait_for_timeout(900)
        p = out / f"{name}.png"
        page.screenshot(path=str(p), full_page=full)
        log(f"截图 {p.name}  ({p.stat().st_size // 1024} KB)")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, channel="chrome")

        # ── ① 未登录可见的部分：登录/注册页 ──────────────────────────────
        anon = browser.new_context(viewport=V)
        page = anon.new_page()
        page.goto(f"{base}/login", wait_until="networkidle", timeout=60000)
        page.get_by_role("tab", name="注册").click()
        page.wait_for_timeout(600)
        snap(page, "01-登录注册页")
        anon.close()

        # ── ② 登录态 ───────────────────────────────────────────────────
        ctx = browser.new_context(viewport=V)
        ctx.add_cookies(cookies)
        if api_key:
            # Key 只注入到浏览器内存（与用户选「只存这台浏览器」是同一条路），不落盘
            ctx.add_init_script(
                "localStorage.setItem('strag_llm_settings', %s)" % json.dumps(
                    json.dumps({"provider": "deepseek", "apiKey": api_key})))
        page = ctx.new_page()

        page.goto(f"{base}/", wait_until="networkidle", timeout=60000)
        snap(page, "02-首页搜索")

        # 真跑一次问答：流式生成 + 参考来源 + 回答评价
        try:
            page.get_by_placeholder("输入你的问题").fill("如何用正则给 AI 回复中的魔法咒语自动添加斜体？")
            page.get_by_role("button", name="搜索").click()
            page.wait_for_selector("text=参考来源", timeout=120000)
            page.wait_for_timeout(1500)
            snap(page, "03-搜索问答（带来源）", full=True)
        except Exception as e:                                    # noqa: BLE001
            log(f"问答截图失败（可能没配 Key / 检索超时）：{str(e)[:120]}")

        for name, path in [("04-角色卡管理", "/cards"),
                           ("05-角色卡编辑", "/cards/1"),
                           ("06-世界书管理", "/worldbooks"),
                           ("07-世界书编辑", "/worldbooks/1"),
                           ("08-工具箱", "/toolbox"),
                           ("09-后台管理", "/admin")]:
            try:
                page.goto(f"{base}{path}", wait_until="networkidle", timeout=60000)
                snap(page, name)
            except Exception as e:                                # noqa: BLE001
                log(f"{name} 失败：{str(e)[:120]}")

        ctx.close()
        browser.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8001")
    ap.add_argument("--out", default="docs/screenshots")
    ap.add_argument("--skip-seed", action="store_true")
    a = ap.parse_args()

    out = (ROOT / a.out) if not Path(a.out).is_absolute() else Path(a.out)
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        try:                      # 自己加载 .env（脚本是入口，不像 backend 那样有 config）
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
            api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        except ImportError:
            pass
    if not api_key:
        log("⚠️  没读到 DEEPSEEK_API_KEY —— 问答页会停在「请设置 API Key」")

    s = api_session(a.base)          # 无论造不造数据都要登录态（截图要用）
    if not a.skip_seed:
        seed(s, a.base)
    cookies = playwright_cookies(s, a.base)

    shoot(a.base, out, api_key, cookies)
    log(f"完成，共 {len(list(out.glob('*.png')))} 张 → {out}")


if __name__ == "__main__":
    sys.exit(main())
