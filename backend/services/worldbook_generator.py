import json
import re
from openai import OpenAI

from backend.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


def generate_from_description(user_input: str) -> dict:
    client = _get_client()

    prompt = f"""你是一个世界书（World Book）生成助手。请根据用户的世界观描述，生成一份完整的 SillyTavern 世界书 JSON。

用户的世界观描述：
{user_input}

请分析描述中的世界观元素，生成以下 JSON 格式的世界书条目（只输出 JSON，不要其他内容）：

{{
  "name": "世界书名称（10字以内）",
  "description": "世界观简述（30-100字）",
  "tags": ["标签1", "标签2"],
  "entries": [
    {{
      "key": "条目关键词",
      "content": "条目的详细内容（30-200字）",
      "comment": "备注说明",
      "depth": 1,
      "trigger_words": ["触发词1", "触发词2"]
    }}
  ]
}}

要求：
1. 生成 5-10 个条目，覆盖世界观的核心要素（地点、人物、规则、历史、组织等）
2. 标签从以下选择：奇幻、科幻、现代、古代、末日、仙侠、武侠、魔法、赛博朋克
3. depth 范围 1-3，越核心的概念深度越小
4. trigger_words 是用户消息中触发该条目检索的关键词
5. key 用中文简短描述"""

    try:
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
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
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return {"error": "JSON 解析失败", "raw": raw[:500]}

    data.setdefault("tags", [])
    data.setdefault("entries", [])
    for entry in data.get("entries", []):
        entry.setdefault("depth", 1)
        entry.setdefault("comment", "")
        entry.setdefault("trigger_words", [])

    return data


def suggest_entries(worldbook_info: str, existing_keys: list = None) -> list:
    client = _get_client()
    existing = ", ".join(existing_keys) if existing_keys else "无"

    prompt = f"""根据以下世界观信息，建议补充 3-5 个新的世界书条目。只输出 JSON 数组格式。

世界观：{worldbook_info}
已有条目：{existing}

输出格式：
[
  {{"key": "条目关键词", "content": "内容描述", "depth": 1, "trigger_words": ["词1"]}},
  ...
]"""

    try:
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2048,
        )
        raw = resp.choices[0].message.content.strip()
        match = re.search(r'\[[\s\S]*?\]', raw)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return []
