import base64
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Optional
from PIL import Image

from backend.config import TMP_DIR


# ==================== 通用工具 ====================

def decode_text(file_bytes: bytes) -> Optional[str]:
    """按 UTF-8（含 BOM）→ GBK 的顺序解码。

    必须用 utf-8-sig：Windows 记事本 / PowerShell 的 `Set-Content -Encoding UTF8`
    都会写出带 BOM 的 UTF-8，用纯 utf-8 解出来的首字符是 \\ufeff，
    交给 json.loads 会直接报 "Unexpected UTF-8 BOM"。
    """
    for enc in ("utf-8-sig", "gbk"):
        try:
            return file_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def load_json(file_bytes: bytes):
    """解析 JSON，返回 (data, error)。自动处理 BOM / GBK。"""
    text = decode_text(file_bytes)
    if text is None:
        return None, "无法解码文件内容（既不是 UTF-8 也不是 GBK）"
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, f"JSON 解析失败: {str(e)[:100]}"


def _as_list(value) -> list:
    """把标量 / 字符串 / 列表统一成列表。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(value)]


def _extract_entries(data) -> list:
    """从各种世界书导出结构里取出条目列表。

    支持三种常见写法：
      1. 顶层就是条目数组：            [...]
      2. 数组：{"entries": [ {...}, ... ]}
      3. 字典（SillyTavern 原生导出）：{"entries": {"0": {...}, "1": {...}}}
         以及 {"data": {"entries": ...}} 这种多包一层的形式。
    """
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]

    if not isinstance(data, dict):
        return []

    node = data
    # 依次向下寻找 entries，最多下探两层（data.character_book / data 等）
    for _ in range(3):
        if not isinstance(node, dict):
            break
        if "entries" in node:
            entries = node["entries"]
            if isinstance(entries, dict):
                ordered = []
                for key in sorted(entries.keys(), key=lambda k: (len(str(k)), str(k))):
                    item = entries[key]
                    if isinstance(item, dict):
                        ordered.append(item)
                return ordered
            if isinstance(entries, list):
                return [e for e in entries if isinstance(e, dict)]
            return []
        # 常见包装层：data / character_book
        nxt = None
        for wrapper in ("data", "character_book", "world_book"):
            if isinstance(node.get(wrapper), dict):
                nxt = node[wrapper]
                break
        if nxt is None:
            break
        node = nxt
    return []


def _decode_png_json(raw: str):
    """SillyTavern 把角色卡 JSON 以 base64 存进 PNG 的 tEXt 块，这里还原。"""
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not raw:
        return None
    # 有些导出工具直接写明文 JSON
    if raw.startswith("{") or raw.startswith("["):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    try:
        decoded = base64.b64decode(raw)
    except Exception:
        return None
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return json.loads(decoded.decode(enc))
        except Exception:
            continue
    return None


def separate_metadata(file_bytes: bytes, filename: str) -> dict:
    """分离角色卡的 JSON 元数据与图片。

    返回的 image_data 是 PNG 的原始 bytes（由 api 层转 base64 出网）。
    """
    ext = Path(filename).suffix.lower()
    result = {"json_data": None, "image_data": None, "image_filename": "", "message": ""}

    if ext == ".png":
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.load()
        except Exception as e:
            return {**result, "error": f"图片解析失败: {str(e)[:100]}"}

        info = img.info or {}
        # V3 优先（ccv3 是更完整的新版结构），没有就回退到 V2 的 chara
        for key in ("ccv3", "chara"):
            if key in info:
                parsed = _decode_png_json(info[key])
                if parsed:
                    result["json_data"] = parsed
                    break

        # 兜底：扫其它 tEXt 块里像 JSON 的值
        if not result["json_data"]:
            for key, val in info.items():
                if not isinstance(val, str):
                    continue
                if val.strip().startswith(("{", "[")):
                    try:
                        result["json_data"] = json.loads(val)
                        break
                    except json.JSONDecodeError:
                        continue
                parsed = _decode_png_json(val)
                if parsed:
                    result["json_data"] = parsed
                    break

        output = io.BytesIO()
        img.save(output, format="PNG")
        result["image_data"] = output.getvalue()
        result["image_filename"] = Path(filename).stem + ".png"
        if result["json_data"]:
            result["message"] = "成功分离：找到嵌入的 JSON 元数据"
        else:
            result["message"] = "图片中未找到嵌入的 JSON 数据（已返回纯图片）"

    elif ext == ".json":
        data, error = load_json(file_bytes)
        if error:
            result["message"] = error
        else:
            result["json_data"] = data
            result["message"] = "成功读取 JSON 文件"
            # 如果 JSON 里带 base64 图片字段，一并还原出来
            for key in ("image", "img", "avatar", "portrait"):
                if isinstance(data, dict) and isinstance(data.get(key), str):
                    try:
                        result["image_data"] = base64.b64decode(data[key])
                        result["image_filename"] = Path(filename).stem + ".png"
                        break
                    except Exception:
                        continue
    else:
        result["message"] = f"不支持的文件格式: {ext}"

    return result



def convert_worldbook(file_bytes: bytes, filename: str, direction: str) -> dict:
    data, error = load_json(file_bytes)
    if error:
        return {"error": error}

    result = {"converted_data": None, "output_format": "", "message": ""}

    try:
        if direction == "characterbook_to_worldbook":
            # entries 可能是数组，也可能是 {"0": {...}, "1": {...}} 的字典（SillyTavern 原生导出）
            entries_data = _extract_entries(data)
            if not entries_data:
                return {**result, "message": "未在文件中找到任何世界书条目（entries 为空或结构无法识别）"}

            new_entries = []
            for entry in entries_data:
                keys = _as_list(entry.get("keys", entry.get("key", [])))
                trigger_words = _as_list(entry.get("secondary_keys", entry.get("trigger_words", [])))
                # constant 是「常驻/蓝灯」布尔量，与 depth（插入位置）不是一回事，
                # 以前把 constant 直接写进 depth，导致输出 "depth": true。
                constant = bool(entry.get("constant", False))
                depth = entry.get("depth", 0)
                if not isinstance(depth, int):
                    depth = 0
                new_entries.append({
                    "key": ", ".join(str(k) for k in keys),
                    "content": entry.get("content", ""),
                    "comment": entry.get("comment", ""),
                    "constant": constant,
                    "depth": depth,
                    "trigger_words": [str(t) for t in trigger_words],
                    "enabled": bool(entry.get("enabled", True)),
                })

            result["converted_data"] = {
                "name": data.get("name", "Unnamed World Book") if isinstance(data, dict) else "Unnamed World Book",
                "description": data.get("description", "") if isinstance(data, dict) else "",
                "entries": new_entries,
            }
            result["output_format"] = "worldbook"
            result["message"] = f"CharacterBook → WorldBook 转换完成，共 {len(new_entries)} 个条目"

        elif direction == "worldbook_to_characterbook":
            entries_data = _extract_entries(data)
            if not entries_data:
                return {**result, "message": "未在文件中找到任何世界书条目（entries 为空或结构无法识别）"}

            new_entries = []
            for entry in entries_data:
                key_str = entry.get("key", "")
                if isinstance(key_str, str):
                    keys = [k.strip() for k in key_str.split(",") if k.strip()]
                else:
                    keys = [str(k) for k in _as_list(key_str)]

                # 兼容两种写法：constant 是布尔（常驻），或 constant 被当成了数字（旧的 depth 误用）。
                raw_constant = entry.get("constant", False)
                if isinstance(raw_constant, bool):
                    constant = raw_constant
                    position = int(entry.get("depth", 0)) if isinstance(entry.get("depth"), int) else 0
                elif isinstance(raw_constant, int):
                    constant = False
                    position = raw_constant
                else:
                    constant = False
                    position = 0

                new_entries.append({
                    "keys": keys,
                    "content": entry.get("content", ""),
                    "comment": entry.get("comment", ""),
                    "constant": constant,
                    "depth": position,
                    # SillyTavern V2 用顺序数字表示插入位置，直观对应「越核心越靠前」
                    "insertion_order": entry.get("insertion_order", 100 - position * 10 if position else 100),
                    "enabled": bool(entry.get("enabled", True)),
                    "secondary_keys": _as_list(entry.get("trigger_words", entry.get("secondary_keys", []))),
                })

            result["converted_data"] = {
                "name": data.get("name", "Unnamed Character Book") if isinstance(data, dict) else "Unnamed Character Book",
                "description": data.get("description", "") if isinstance(data, dict) else "",
                "entries": new_entries,
            }
            result["output_format"] = "characterbook"
            result["message"] = f"WorldBook → CharacterBook 转换完成，共 {len(new_entries)} 个条目"

        else:
            result["message"] = f"不支持的转换方向: {direction}"
    except Exception as e:
        result["message"] = f"转换失败: {str(e)[:100]}"

    return result


def convert_chinese(file_bytes: bytes, filename: str, direction: str) -> dict:
    text = decode_text(file_bytes)
    if text is None:
        return {"error": "无法解码文本（既不是 UTF-8 也不是 GBK）"}

    cc_configs = {
        "s2t": "s2t", "t2s": "t2s", "s2tw": "s2tw", "tw2s": "tw2s",
        "s2hk": "s2hk", "hk2s": "hk2s", "tw2sp": "tw2sp",
    }
    if direction not in cc_configs:
        return {"error": f"不支持的转换方向: {direction}"}

    try:
        from opencc import OpenCC
    except ImportError:
        try:
            from opencc_rust import OpenCC  # type: ignore
        except ImportError:
            # 以前这里「静默返回原文 + 报转换完成」，界面上看起来成功、实际一个字没动。
            # 现在直接报错，让用户知道是缺依赖。
            return {
                "error": "简繁转换依赖 opencc 未安装，无法转换。"
                         "请执行：pip install opencc-python-reimplemented",
            }

    direction_names = {
        "s2t": "简体→繁体", "t2s": "繁体→简体", "s2tw": "简体→台湾繁体",
        "tw2s": "台湾繁体→简体", "s2hk": "简体→香港繁体", "hk2s": "香港繁体→简体",
        "tw2sp": "台湾繁体→简体（中国习惯）",
    }

    try:
        cc = OpenCC(cc_configs[direction])
    except Exception as e:
        return {"error": f"OpenCC 初始化失败: {str(e)[:100]}"}

    try:
        converted = cc.convert(text)
    except Exception as e:
        return {"error": f"转换失败: {str(e)[:100]}"}

    return {
        "converted_text": converted,
        "message": f"{direction_names.get(direction, direction)} 转换完成",
    }


def format_text(file_bytes: bytes, filename: str, operation: str) -> dict:
    text = decode_text(file_bytes)
    if text is None:
        return {"error": "无法解码文本（既不是 UTF-8 也不是 GBK）"}

    result = {"converted_text": text, "message": ""}

    if operation == "fullwidth_to_halfwidth":
        result["converted_text"] = _fullwidth_to_halfwidth(text)
        result["message"] = "全角→半角转换完成"
    elif operation == "halfwidth_to_fullwidth":
        result["converted_text"] = _halfwidth_to_fullwidth(text)
        result["message"] = "半角→全角转换完成"
    elif operation == "remove_empty_lines":
        lines = text.split("\n")
        result_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                result_lines.append(line)
        result["converted_text"] = "\n".join(result_lines)
        result["message"] = "清除独立空行完成"
    elif operation == "compress_json":
        try:
            data = json.loads(text)
            result["converted_text"] = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            result["message"] = "JSON 压缩完成"
        except Exception as e:
            return {"error": f"JSON 解析失败: {str(e)[:100]}"}
    elif operation == "format_json":
        try:
            data = json.loads(text)
            result["converted_text"] = json.dumps(data, ensure_ascii=False, indent=2)
            result["message"] = "JSON 格式化完成"
        except Exception as e:
            return {"error": f"JSON 解析失败: {str(e)[:100]}"}
    else:
        result["message"] = f"不支持的操作: {operation}"

    return result


def _fullwidth_to_halfwidth(text: str) -> str:
    result = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            result.append(chr(0x0020))
        elif 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        else:
            result.append(ch)
    return "".join(result)


def _halfwidth_to_fullwidth(text: str) -> str:
    result = []
    for ch in text:
        code = ord(ch)
        if code == 0x0020:
            result.append(chr(0x3000))
        elif 0x0021 <= code <= 0x007E:
            result.append(chr(code + 0xFEE0))
        else:
            result.append(ch)
    return "".join(result)


def convert_jsonl_to_novel(file_bytes: bytes, filename: str, character_mapping: dict = None) -> dict:
    text = decode_text(file_bytes)
    if text is None:
        return {"error": "无法解码 JSONL 文件（既不是 UTF-8 也不是 GBK）"}

    lines = text.strip().split("\n")
    messages = []
    for line in lines:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            messages.append(msg)
        except Exception:
            continue

    if not messages:
        return {"error": "未找到有效的 JSONL 消息"}

    novel_lines = []
    novel_lines.append("# 聊天记录小说\n")
    novel_lines.append("> 由 JSONL 聊天记录自动转换\n\n")

    mapping = character_mapping or {}

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        name = msg.get("name", "")

        if role == "system":
            novel_lines.append(f"> *系统提示*: {content}\n\n")
        elif role == "user":
            display_name = mapping.get("user", "你")
            novel_lines.append(f"### {display_name}\n\n{content}\n\n")
        elif role == "assistant":
            display_name = mapping.get(name, name) if name else mapping.get("assistant", "AI 角色")
            novel_lines.append(f"### {display_name}\n\n{content}\n\n")
        else:
            display_name = name or role
            novel_lines.append(f"### {display_name}\n\n{content}\n\n")

        if i < len(messages) - 1:
            novel_lines.append("---\n\n")

    result_text = "".join(novel_lines)
    return {"converted_text": result_text, "message": f"转换完成，共 {len(messages)} 条消息"}
