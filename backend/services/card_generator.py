import json
import re
from typing import Optional

from openai import OpenAI

from backend.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from backend.schemas.character_card import CharacterCardCreate

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


TAG_OPTIONS = [
    "RPG", "日常聊天", "科幻", "奇幻", "现代", "古代", "中世纪", "未来",
    "校园", "职场", "冒险", "恐怖", "悬疑", "恋爱", "喜剧", "悲剧",
    "战争", "武侠", "仙侠", "末日", "赛博朋克", "蒸汽朋克", "魔法",
    "超能力", "吸血鬼", "狼人", "天使", "恶魔", "神明", "机器人",
    "异世界", "穿越", "游戏", "运动", "音乐", "美食", "推理",
]


def generate_from_description(user_input: str) -> dict:
    client = _get_client()

    tags_str = "、".join(TAG_OPTIONS)
    prompt = f"""你是一个角色卡生成助手。请根据用户的描述，生成一个完整的 SillyTavern 风格角色卡 JSON。

用户描述：
{user_input}

请生成以下 JSON 格式的角色卡（只输出 JSON，不要其他内容）：

{{
  "name": "角色名称",
  "age": "年龄",
  "gender": "性别",
  "species": "种族",
  "occupation": "职业",
  "appearance": "外貌描述（50-200字，详细描述发型、眼睛、身高、体型、服装等）",
  "personality": "性格描述（50-200字，描述性格特点、喜好、习惯等）",
  "background": "背景故事（100-300字，描述角色的过往经历）",
  "description": "一句话简介（20-50字）",
  "tags": ["标签1", "标签2", "标签3"],
  "first_message": "开场白/问候语（角色会对用户说的第一句话）"
}}

要求：
1. 标签从以下列表中选择 3-5 个最合适的：{tags_str}
2. 外貌、性格、背景要详细生动
3. 开场白要符合角色性格
4. 根据用户描述推断角色是否为 R18 内容（在额外字段标注）
5. 如果是 R18 角色，开场白和描述要保持适度"""

    try:
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096,
        )
        raw = resp.choices[0].message.content.strip()
    except Exception as e:
        return {"error": f"生成失败: {str(e)[:100]}"}

    json_match = re.search(r'\{[\s\S]*\}', raw)
    if not json_match:
        return {"error": "无法解析生成的 JSON", "raw": raw[:500]}

    try:
        card_data = json.loads(json_match.group())
    except json.JSONDecodeError:
        try:
            cleaned = json_match.group()
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            card_data = json.loads(cleaned)
        except json.JSONDecodeError:
            return {"error": "JSON 解析失败", "raw": raw[:500]}

    card_data["tags"] = card_data.get("tags", [])
    if isinstance(card_data["tags"], str):
        card_data["tags"] = [t.strip() for t in card_data["tags"].split(",")]

    card_data.setdefault("custom_css", "")
    card_data.setdefault("is_r18", False)
    card_data.setdefault("has_status_bar", False)
    card_data.setdefault("status_bar_content", "")
    card_data.setdefault("status_bar_content_r18", "")
    card_data.setdefault("image_path", "")

    return card_data


def suggest_tags(character_info: str) -> list:
    client = _get_client()
    tags_str = "、".join(TAG_OPTIONS)

    prompt = f"""根据以下角色信息，从可用标签列表中选择 3-5 个最合适的标签。只输出标签列表（JSON 数组格式）。

角色信息：{character_info}

可用标签：{tags_str}

输出格式：["标签1", "标签2", "标签3"]"""

    try:
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=256,
        )
        raw = resp.choices[0].message.content.strip()
        match = re.search(r'\[[\s\S]*?\]', raw)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return []


def generate_status_bar(character_info: str, is_r18: bool) -> str:
    client = _get_client()
    r18_hint = "R18成人内容" if is_r18 else "全年龄"
    prompt = f"""为角色生成一个状态栏内容（适用于{r18_hint}场景），格式如下：
状态栏包含角色的关键数值或当前状态，每条一行。

角色信息：{character_info}

请生成 JSON 数组格式，每一项包含 label 和 value：
[{{"label": "心情", "value": "愉悦"}}, {{"label": "好感度", "value": "50"}}, ...]

只输出 JSON 数组。"""

    try:
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=512,
        )
        raw = resp.choices[0].message.content.strip()
        match = re.search(r'\[[\s\S]*?\]', raw)
        if match:
            return match.group()
    except Exception:
        pass
    return "[]"


def generate_greeting(character_info: str, is_r18: bool = False) -> str:
    client = _get_client()
    r18_hint = "可以适当暧昧但不过分露骨" if is_r18 else "保持全年龄友好"
    prompt = f"""为以下角色生成一段开场白（first_message），这是角色在对话开始时对用户说的第一句话。
{r18_hint}

角色信息：{character_info}

要求：
1. 30-100字
2. 体现角色的性格特点
3. 自然亲切，吸引用户继续对话
4. 只输出开场白文字，不要其他内容"""

    try:
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=256,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "你好，很高兴认识你！"
