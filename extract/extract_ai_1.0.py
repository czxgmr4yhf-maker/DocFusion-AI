import json
import os
import re
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data.json"
OUTPUT_PATH = BASE_DIR / "test_output.json"

DEFAULT_API_KEY = "sk-640a6d0c77a6454286e029fe74d8a47b"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"

TARGET_FIELDS = [
    "项目名称",
    "项目负责人",
    "单位名称",
    "甲方",
    "乙方",
    "联系人",
    "联系电话",
    "项目编号",
    "合同编号",
    "日期",
    "金额",
]

def build_client():
    if OpenAI is None:
        raise RuntimeError("缺少 openai 依赖，请先执行 pip install openai")
    if not DEFAULT_API_KEY or DEFAULT_API_KEY == "YOUR_API_KEY_HERE":
        raise RuntimeError("请先在 extract_ai_1.0.py 里填写 DEFAULT_API_KEY")
    return OpenAI(api_key=DEFAULT_API_KEY, base_url=DEFAULT_BASE_URL)


def load_data(path=DATA_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract_json_text(raw_text):
    if not raw_text:
        return ""
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text.strip(), re.S)
    return fenced.group(1).strip() if fenced else raw_text.strip()


def safe_load_json(raw_text):
    try:
        return json.loads(extract_json_text(raw_text))
    except Exception:
        return None


def normalize_text(value):
    if value is None:
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def build_document_text(data):
    raw_text = normalize_text(data.get("raw_text"))
    if raw_text:
        return raw_text
    paragraphs = [normalize_text(item) for item in data.get("paragraphs", []) if normalize_text(item)]
    return "\n".join(paragraphs)


def locate_para_id(paragraphs, value):
    if not value:
        return -1
    normalized_value = normalize_text(value)
    for idx, paragraph in enumerate(paragraphs):
        if normalized_value and normalized_value in normalize_text(paragraph):
            return idx
    return -1


def build_prompt(data):
    document_text = build_document_text(data)
    payload = {
        "task": "你是文档字段抽取助手。请直接阅读整篇文档内容，抽取明确出现且有依据的字段。",
        "requirements": [
            "不要分段候选筛选，直接基于整篇文章理解并抽取。",
            "只保留有明确证据的字段，不要猜测，不要补全。",
            "每个字段最多输出一条。",
            "如果文档里没有该字段，就不要输出该字段。",
            "输出必须是合法 JSON。",
        ],
        "target_fields": TARGET_FIELDS,
        "output_schema": {
            "doc_id": "string",
            "extractions": [
                {
                    "raw_field": "string",
                    "value": "string",
                    "source": "llm",
                    "para_id": "int, unknown use -1",
                }
            ],
        },
        "document": {
            "doc_id": data.get("doc_id", ""),
            "paragraphs": data.get("paragraphs", []),
            "raw_text": document_text,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def llm_extract(data, client, model=DEFAULT_MODEL):
    messages = [
        {
            "role": "system",
            "content": "你是严谨的信息抽取助手。只输出 JSON，不要输出解释。",
        },
        {
            "role": "user",
            "content": build_prompt(data),
        },
    ]

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
        )
        content = completion.choices[0].message.content
        result = safe_load_json(content)
        if not isinstance(result, dict):
            raise ValueError("LLM 返回的不是合法 JSON 对象")
        return sanitize_result(result, data, default_source="llm")
    except Exception as exc:
        raise RuntimeError(f"LLM 抽取失败: {exc}") from exc


def deduplicate_extractions(extractions):
    deduped = []
    seen = set()
    for item in extractions:
        key = (item.get("raw_field"), item.get("value"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def sanitize_result(result, data, default_source="llm"):
    paragraphs = data.get("paragraphs", [])
    valid_fields = set(TARGET_FIELDS)
    cleaned = []

    for item in result.get("extractions", []):
        if not isinstance(item, dict):
            continue
        raw_field = normalize_text(item.get("raw_field"))
        value = normalize_text(item.get("value"))
        if not raw_field or raw_field not in valid_fields or not value:
            continue

        para_id = item.get("para_id", -1)
        if not isinstance(para_id, int):
            para_id = locate_para_id(paragraphs, value)
        elif para_id < -1 or para_id >= len(paragraphs):
            para_id = locate_para_id(paragraphs, value)

        cleaned.append(
            {
                "raw_field": raw_field,
                "value": value,
                "source": normalize_text(item.get("source")) or default_source,
                "para_id": para_id,
            }
        )

    if not cleaned:
        raise ValueError("LLM 返回中没有可用的抽取结果")

    return {
        "doc_id": normalize_text(result.get("doc_id")) or data.get("doc_id", ""),
        "extractions": deduplicate_extractions(cleaned),
    }


def extract(data, client=None, model=DEFAULT_MODEL):
    client = build_client() if client is None else client
    return llm_extract(data, client=client, model=model)


def main():
    data = load_data()
    result = extract(data)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
