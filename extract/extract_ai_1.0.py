import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import pandas as pd

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data.json"
SYNONYM_PATH = BASE_DIR / "field_synonyms.xlsx"

QWEN_API_KEY = "sk-640a6d0c77a6454286e029fe74d8a47b"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"

ENTITY_FIELDS = [
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

ENTITY_RULE_PATTERNS = {
    "项目名称": [r"(?:项目名称|项目名|课题名称|合同名称|工程名称)[:：]\s*([^\n，。；;]{2,100})"],
    "项目负责人": [r"(?:项目负责人|负责人|课题负责人)[:：]\s*([^\s，。,；;：:\n]{2,30})"],
    "单位名称": [r"(?:单位名称|申报单位|所属单位|公司名称|机构名称)[:：]\s*([^\n，。；;]{2,100})"],
    "甲方": [r"(?:甲方|采购人|发包人|委托方)[:：]\s*([^\n，。；;]{2,100})"],
    "乙方": [r"(?:乙方|供应商|承包方|投标人)[:：]\s*([^\n，。；;]{2,100})"],
    "联系人": [r"(?:联系人|项目联系人)[:：]\s*([^\s，。,；;：:\n]{2,30})"],
    "联系电话": [r"(?:联系电话|联系人电话|手机号|手机|电话)[:：]?\s*([0-9\-+() ]{7,20})"],
    "项目编号": [r"(?:项目编号|项目编码|项目号|立项编号|招标编号)[:：]\s*([A-Za-z0-9\-_\/]+)"],
    "合同编号": [r"(?:合同编号|合同编码|合同号|协议编号)[:：]\s*([A-Za-z0-9\-_\/]+)"],
    "日期": [r"(?:发布时间|签订日期|时间|日期)[:：]?\s*((?:19|20)\d{2}[年\-/]\d{1,2}[月\-/]\d{1,2}日?)"],
    "金额": [r"(?:金额|总金额|合同金额|预算金额|中标金额)[:：]?\s*([0-9][0-9,\.]*\s*(?:元|万元|亿元))"],
}

RULE_FIELD_CONFIG = {
    "适用条件": ["符合", "满足", "具备", "条件", "要求", "适用"],
    "禁止约束": ["不得", "禁止", "严禁", "不可", "不应"],
    "办理时限": ["工作日", "截止", "期限", "时限", "之前", "之内"],
    "申报材料": ["提交", "提供", "材料", "证明", "附件", "申请表"],
}


def build_client():
    if OpenAI is None:
        return None
    return OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)


def load_data(path=DATA_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_reverse_dict(path=SYNONYM_PATH):
    df = pd.read_excel(path)
    reverse_dict = {}
    for _, row in df.iterrows():
        field = str(row["标准字段"]).strip()
        synonyms = [item.strip() for item in str(row["同义词"]).split("、") if item.strip()]
        for synonym in synonyms:
            reverse_dict[synonym] = field
    return reverse_dict


def clamp_score(value):
    return round(max(0.0, min(1.0, value)), 3)


def keyword_confidence(trigger):
    if len(trigger) >= 4:
        return 0.82
    if len(trigger) >= 2:
        return 0.75
    return 0.66


def split_sentences(paragraph):
    parts = re.split(r"(?<=[。！？；;])", paragraph.strip())
    return [item.strip() for item in parts if item.strip()]


def extract_json_text(raw_text):
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text.strip(), re.S)
    return fenced.group(1).strip() if fenced else raw_text.strip()


def safe_load_json(raw_text, default_value):
    try:
        return json.loads(extract_json_text(raw_text))
    except Exception:
        return default_value


def chat_json(client, messages, default_value, model=QWEN_MODEL, temperature=0.1):
    if client is None:
        return default_value
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        content = completion.choices[0].message.content
        return safe_load_json(content, default_value)
    except Exception:
        return default_value


def pseudo_ner_entity_candidates(paragraphs):
    candidates = defaultdict(list)
    org_pattern = r"([\u4e00-\u9fa5A-Za-z0-9]{2,40}(?:公司|集团|大学|学院|研究院|研究所|委员会|人民政府|文化和旅游部|国家文物局))"
    project_pattern = r"(?:《([^》]{2,60})》|“([^”]{2,60})”|项目名称[:：]\s*([^\n，。；;]{2,80}))"

    for para_id, para in enumerate(paragraphs):
        for match in re.finditer(org_pattern, para):
            candidates["单位名称"].append({
                "field": "单位名称",
                "candidate_text": match.group(1).strip(),
                "snippet": para,
                "para_id": para_id,
                "source": "ner",
                "trigger": "org_pattern",
                "confidence": 0.68,
                "raw_field": "单位名称",
            })

        for match in re.finditer(project_pattern, para):
            value = next((group for group in match.groups() if group), None)
            if value:
                candidates["项目名称"].append({
                    "field": "项目名称",
                    "candidate_text": value.strip(),
                    "snippet": para,
                    "para_id": para_id,
                    "source": "ner",
                    "trigger": "project_pattern",
                    "confidence": 0.64,
                    "raw_field": "项目名称",
                })

    return dict(candidates)


def locate_entity_candidates(paragraphs, reverse_dict, target_fields=None, window=100):
    target_fields = set(target_fields or ENTITY_FIELDS)
    candidates = defaultdict(list)

    for para_id, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue

        for field, patterns in ENTITY_RULE_PATTERNS.items():
            if field not in target_fields:
                continue
            for pattern in patterns:
                for match in re.finditer(pattern, para):
                    candidates[field].append({
                        "field": field,
                        "candidate_text": match.group(1).strip(),
                        "snippet": para,
                        "para_id": para_id,
                        "source": "paragraph",
                        "trigger": pattern,
                        "confidence": 0.93,
                        "raw_field": field,
                    })

        for trigger, field in reverse_dict.items():
            if field not in target_fields or trigger not in para:
                continue
            hit_pos = para.find(trigger)
            start = max(0, hit_pos - 24)
            end = min(len(para), hit_pos + len(trigger) + window)
            candidates[field].append({
                "field": field,
                "candidate_text": para[start:end].strip(),
                "snippet": para,
                "para_id": para_id,
                "source": "paragraph",
                "trigger": trigger,
                "confidence": keyword_confidence(trigger),
                "raw_field": trigger,
            })

    for field, items in pseudo_ner_entity_candidates(paragraphs).items():
        if field in target_fields:
            candidates[field].extend(items)

    return dict(candidates)


def build_entity_prompt(field, candidates):
    return {
        "task": "从候选片段中选择最可信的一个字段值，返回 JSON。",
        "field": field,
        "output_schema": {
            "raw_field": "string",
            "value": "string or null",
            "source": "paragraph|ner|llm",
            "para_id": "int",
            "confidence": "0~1",
        },
        "candidates": candidates,
    }


def fallback_entity_value(field, candidates):
    best = sorted(candidates, key=lambda x: x["confidence"], reverse=True)[0]
    return {
        "raw_field": best.get("raw_field", field),
        "value": best["candidate_text"],
        "source": best["source"],
        "para_id": best["para_id"],
        "confidence": clamp_score(best["confidence"]),
    }


def normalize_entity_candidates(client, entity_candidates):
    results = []

    for field, candidates in entity_candidates.items():
        if not candidates:
            continue
        fallback = fallback_entity_value(field, candidates)
        prompt = build_entity_prompt(field, deepcopy(candidates))
        messages = [
            {"role": "system", "content": "你是信息抽取助手。只输出合法 JSON，不要输出解释。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, indent=2)},
        ]
        result = chat_json(client, messages, fallback)
        if not isinstance(result, dict):
            result = fallback
        result.setdefault("raw_field", fallback["raw_field"])
        result.setdefault("value", fallback["value"])
        result.setdefault("source", fallback["source"])
        result.setdefault("para_id", fallback["para_id"])
        result["confidence"] = clamp_score(float(result.get("confidence", fallback["confidence"])))
        results.append(result)

    return results


def locate_rule_candidates(paragraphs):
    results = defaultdict(list)
    for para_id, para in enumerate(paragraphs):
        for sent_id, sent in enumerate(split_sentences(para)):
            for field, triggers in RULE_FIELD_CONFIG.items():
                matched = [trigger for trigger in triggers if trigger in sent]
                if matched:
                    results[field].append({
                        "field": field,
                        "candidate_text": sent,
                        "para_id": para_id,
                        "sentence_id": sent_id,
                        "source": "sentence",
                        "matched_triggers": matched,
                        "confidence": clamp_score(0.62 + 0.08 * min(len(matched), 3)),
                    })
    return dict(results)


def build_rule_prompt(field, candidates):
    return {
        "task": "识别规则文本中的核心要求，返回简洁 JSON。",
        "field": field,
        "output_schema": {
            "raw_field": "string",
            "value": {
                "condition": "string or null",
                "subject": "string or null",
                "action": "string or null",
                "constraint": "string or null",
            },
            "source": "sentence|llm",
            "para_id": "int",
            "confidence": "0~1",
        },
        "candidates": candidates,
    }


def fallback_rule_values(field, candidates):
    outputs = []
    for item in sorted(candidates, key=lambda x: x["confidence"], reverse=True):
        sentence = item["candidate_text"]
        outputs.append({
            "raw_field": field,
            "value": {
                "condition": sentence if field == "适用条件" else None,
                "subject": None,
                "action": sentence if field in {"申报材料", "办理时限"} else None,
                "constraint": sentence if field == "禁止约束" else None,
            },
            "source": item["source"],
            "para_id": item["para_id"],
            "confidence": clamp_score(item["confidence"]),
        })
    return outputs


def structure_rule_candidates(client, rule_candidates):
    results = []
    for field, candidates in rule_candidates.items():
        if not candidates:
            continue
        fallback = fallback_rule_values(field, candidates)
        prompt = build_rule_prompt(field, deepcopy(candidates))
        messages = [
            {"role": "system", "content": "你是规则抽取助手。只输出合法 JSON 数组，不要输出解释。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, indent=2)},
        ]
        parsed = chat_json(client, messages, fallback)
        if not isinstance(parsed, list):
            parsed = fallback
        for idx, item in enumerate(parsed):
            base = fallback[min(idx, len(fallback) - 1)]
            if not isinstance(item, dict):
                item = base
            item.setdefault("raw_field", base["raw_field"])
            item.setdefault("value", base["value"])
            item.setdefault("source", base["source"])
            item.setdefault("para_id", base["para_id"])
            item["confidence"] = clamp_score(float(item.get("confidence", base["confidence"])))
            results.append(item)
    return results


def extract(data):
    client = build_client()
    reverse_dict = load_reverse_dict()
    paragraphs = data.get("paragraphs", [])

    entity_candidates = locate_entity_candidates(paragraphs, reverse_dict)
    entity_extractions = normalize_entity_candidates(client, entity_candidates)

    rule_candidates = locate_rule_candidates(paragraphs)
    rule_extractions = structure_rule_candidates(client, rule_candidates)

    extractions = entity_extractions + rule_extractions
    extractions.sort(key=lambda item: (item.get("para_id", 10**9), -item.get("confidence", 0)))

    simplified = []
    for item in extractions:
        simplified_item = {
            "raw_field": item["raw_field"],
            "value": item["value"],
            "source": item["source"],
            "para_id": item["para_id"],
        }
        simplified.append(simplified_item)

    return {
        "doc_id": data["doc_id"],
        "extractions": simplified,
    }


if __name__ == "__main__":
    result = extract(load_data())
    print(json.dumps(result, ensure_ascii=False, indent=2))
