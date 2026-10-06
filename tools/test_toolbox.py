#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具箱 5 个工具的回归测试：走真实 HTTP 打正在运行的后端。

为什么断言都落在**具体内容**上（字符、字段值、数量）而不是只看 HTTP 200：
    只查 200 的话，"静默返回原文/空壳还报转换完成"这种假成功会照样通过 ——
    JSONL 小说转换器就出过这个毛病（只认 OpenAI 的 role/content，遇到 SillyTavern
    的 name/mes 就取到空串，转出 117 个空标题且报"转换完成"）。

前置：后端在跑（python -m uvicorn backend.main:app --port 8000）
用法：python tools/test_toolbox.py [--base http://127.0.0.1:8000]
"""
import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

import httpx

# 可选：本机有真实 SillyTavern 导出时，用环境变量指过去顺手多验一遍
# （不设也不影响测试通过）
_real = os.environ.get("TOOLBOX_REAL_JSONL", "")
REAL_JSONL: Path | None = Path(_real) if _real else None

fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  {'✅' if cond else '❌'} {msg}")
    if not cond:
        fails.append(msg)


def make_st_jsonl() -> bytes:
    """造一份 SillyTavern 导出格式的聊天记录（含元数据头、system、空正文记录）。"""
    lines = [
        {"user_name": "unused", "character_name": "unused",
         "chat_metadata": {"integrity": "test"}},
        {"name": "测试用户", "is_user": True, "is_system": False, "mes": "你好，你是谁",
         "extra": {"reasoning": ""}},
        {"name": "心理医生", "is_user": False, "is_system": False, "mes": "我是心理医生。",
         "extra": {"reasoning": "先自我介绍"}},
        {"name": "心理医生", "is_user": False, "is_system": False, "mes": "你可以慢慢说。",
         "extra": {"reasoning": ""}},
        {"name": "测试用户", "is_user": True, "is_system": False, "mes": "好的。", "extra": {}},
        {"name": "系统", "is_user": False, "is_system": True, "mes": "（重置了上下文）", "extra": {}},
        {"name": "测试用户", "is_user": True, "is_system": False, "mes": "", "extra": {}},
    ]
    return ("\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/tools"

    def post(tool: str, files: dict, data: dict | None = None):
        try:
            r = httpx.post(f"{base}/{tool}", files=files, data=data or {}, timeout=120)
        except httpx.ConnectError:
            print(f"❌ 连不上后端 {base} —— 先把服务起起来再跑这个测试")
            sys.exit(2)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {"_raw": r.text[:200]}

    print("① 元数据分离器（PNG 里嵌角色卡 JSON）")
    from PIL import Image, PngImagePlugin
    card = {"name": "测试角色", "description": "一句话简介", "first_mes": "你好呀"}
    info = PngImagePlugin.PngInfo()
    info.add_text("chara", base64.b64encode(
        json.dumps(card, ensure_ascii=False).encode("utf-8")).decode("ascii"))
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (60, 120, 200)).save(buf, format="PNG", pnginfo=info)
    code, data = post("separator", {"file": ("test_card.png", buf.getvalue(), "image/png")})
    check(code == 200, f"HTTP 200（实际 {code}）")
    check((data.get("json_data") or {}).get("name") == "测试角色", "解出的角色名正确")
    check((data.get("json_data") or {}).get("first_mes") == "你好呀", "解出的开场白正确")
    check(base64.b64decode(data.get("image_base64") or "")[:8] == b"\x89PNG\r\n\x1a\n",
          "同时返回了 PNG 本体")
    plain = io.BytesIO()
    Image.new("RGB", (8, 8), (0, 0, 0)).save(plain, format="PNG")
    _c, d2 = post("separator", {"file": ("plain.png", plain.getvalue(), "image/png")})
    check(d2.get("json_data") is None and "未找到" in (d2.get("message") or ""),
          "无元数据的 PNG 明确说「未找到」，不假装成功")

    print("\n② 世界书转换器（CharacterBook → WorldBook → CharacterBook 往返）")
    cb = {"name": "测试世界书", "description": "测试用", "entries": [
        {"keys": ["龙", "dragon"], "content": "龙是传说中的生物", "comment": "龙的设定",
         "constant": True, "depth": 3, "secondary_keys": ["魔法"], "enabled": True},
        {"keys": ["剑"], "content": "剑是武器", "comment": "", "constant": False,
         "depth": 0, "secondary_keys": [], "enabled": False},
    ]}
    code, wb = post("worldbook-converter",
                    {"file": ("cb.json", json.dumps(cb, ensure_ascii=False).encode("utf-8"),
                              "application/json")},
                    {"direction": "characterbook_to_worldbook"})
    e0 = (wb.get("converted_data") or {}).get("entries", [{}])[0]
    check(code == 200 and bool(wb.get("converted_data")), "CharacterBook→WorldBook 有输出")
    check(e0.get("key") == "龙, dragon", f"多关键字合并成 key（实际 {e0.get('key')!r}）")
    check(e0.get("constant") is True and e0.get("depth") == 3, "constant 与 depth 没有互相串")
    check(e0.get("trigger_words") == ["魔法"], "secondary_keys → trigger_words")
    code, cb2 = post("worldbook-converter",
                     {"file": ("wb.json", json.dumps(wb["converted_data"], ensure_ascii=False)
                               .encode("utf-8"), "application/json")},
                     {"direction": "worldbook_to_characterbook"})
    back = (cb2.get("converted_data") or {}).get("entries", [{}, {}])
    check(code == 200 and len(back) == 2, "往返回来仍是 2 条")
    check(back[0].get("keys") == ["龙", "dragon"], f"往返后 keys 还原（{back[0].get('keys')}）")
    check(back[0].get("content") == "龙是传说中的生物" and back[0].get("constant") is True,
          "往返后正文与常驻标记不变")
    check(back[1].get("enabled") is False, "往返后 enabled=False 保住")

    print("\n③ 简繁转换器")
    code, r = post("chinese-converter",
                   {"file": ("t.txt", "简体字：汉字转换测试，后面跟着英文 ABC。".encode("utf-8"),
                             "text/plain")}, {"direction": "s2t"})
    if r.get("error"):
        check(False, f"简繁转换不可用：{r['error']}")
    else:
        out = r.get("converted_text", "")
        check(code == 200 and "簡體字" in out and "漢字轉換測試" in out,
              f"简体确实转成繁体（{out[:20]}）")
        check("ABC" in out, "英文原样保留")

    print("\n④ 宽窄转换器（全角↔半角 / JSON / 空行）")
    code, r = post("width-converter", {"file": ("w.txt", "ＡＢＣ１２３，全角！".encode("utf-8"),
                                                "text/plain")},
                   {"operation": "fullwidth_to_halfwidth"})
    check(code == 200 and r.get("converted_text") == "ABC123,全角!",
          f"全角→半角结果精确（实际 {r.get('converted_text')!r}）")
    _c, r2 = post("width-converter", {"file": ("w2.txt", "ABC123,全角!".encode("utf-8"), "text/plain")},
                  {"operation": "halfwidth_to_fullwidth"})
    check(r2.get("converted_text") == "ＡＢＣ１２３，全角！", "半角→全角转得回来")
    _c, r3 = post("width-converter", {"file": ("j.json", b'{ "a" :  1 }', "application/json")},
                  {"operation": "format_json"})
    check((r3.get("converted_text") or "").startswith('{\n  "a": 1'), "JSON 格式化可用")
    _c, r4 = post("width-converter", {"file": ("e.txt", b"a\n\n\nb\n\n", "text/plain")},
                  {"operation": "remove_empty_lines"})
    check(r4.get("converted_text") == "a\nb", "清除空行可用")

    print("\n⑤ JSONL 小说转换器（SillyTavern 格式，程序自己造的样本）")
    code, r = post("jsonl-novel-converter",
                   {"file": ("sample.jsonl", make_st_jsonl(), "application/jsonl")},
                   {"character_mapping": "{}", "include_reasoning": "false"})
    out = r.get("converted_text", "")
    check(code == 200, f"HTTP 200（实际 {code}）")
    check("你好，你是谁" in out and "我是心理医生。" in out, "正文被正确提取（不是空壳）")
    check("### 心理医生" in out and "### 测试用户" in out, "两个说话人都出现")
    check(out.count("### 心理医生") == 1, "连续同一人的发言被合并成一个段落")
    check("先自我介绍" not in out, "默认不写入 AI 的思考过程")
    check("### 系统" in out, "system 消息单独归类")
    check("### unused" not in out, "占位名 unused 不会当标题")
    check(out.startswith("# 心理医生 × 测试用户"), f"标题由实际发言推断（{out.splitlines()[0]}）")
    _c, r_map = post("jsonl-novel-converter",
                     {"file": ("sample.jsonl", make_st_jsonl(), "application/jsonl")},
                     {"character_mapping": json.dumps({"心理医生": "陈医生"}, ensure_ascii=False),
                      "include_reasoning": "true"})
    om = r_map.get("converted_text", "")
    check("### 陈医生" in om and "### 心理医生" not in om, "角色名映射生效")
    check("先自我介绍" in om, "勾选后思考过程会写进去")

    if REAL_JSONL and REAL_JSONL.exists():
        print(f"\n⑥ 附加：本机真实导出文件（{REAL_JSONL.name}）")
        code, r = post("jsonl-novel-converter",
                       {"file": (REAL_JSONL.name, REAL_JSONL.read_bytes(), "application/jsonl")},
                       {"character_mapping": "{}", "include_reasoning": "false"})
        out = r.get("converted_text", "")
        check(code == 200 and len(out) > 10000, f"转出正文 {len(out)} 字（>10000）")
        check("\n\n\n\n" not in out, "没有空壳段落")
    else:
        print("\n⑥ 附加：真实文件不在（已跳过，不影响测试通过）")

    print("\n⑦ 错误路径：不许静默成功")
    _c, r = post("width-converter", {"file": ("x.txt", b"abc", "text/plain")},
                 {"operation": "不存在的操作"})
    check("不支持的操作" in ((r.get("converted_text") or "") + (r.get("message") or "")),
          "未知操作明说「不支持」，不原样返回还报成功")
    _c, r = post("chinese-converter", {"file": ("x.txt", b"abc", "text/plain")}, {"direction": "nope"})
    check(bool(r.get("error")), "未知简繁方向会报错")
    _c, r = post("worldbook-converter",
                 {"file": ("e.json", b'{"name":"x","entries":[]}', "application/json")},
                 {"direction": "characterbook_to_worldbook"})
    check("未在文件中找到" in (r.get("message") or ""), "空世界书明说没找到条目")

    print()
    if fails:
        print(f"❌ 失败 {len(fails)} 项：")
        for f in fails:
            print("   ·", f)
        return 1
    print("✅ 工具箱回归测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
