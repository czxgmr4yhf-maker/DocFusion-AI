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
WORD_PATH = BASE_DIR / "word.json"
OUTPUT_PATH = BASE_DIR / "test_output.json"

DEFAULT_BASE_URL = os.getenv("EXTRACT_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DEFAULT_MODEL = os.getenv("EXTRACT_MODEL", "qwen-plus")
MAX_FIELD_CANDIDATES = 12
ENTITY_CONTEXT_WINDOW = 1
MAX_ENTITY_CANDIDATES = 24


def load_json_file(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_data_json(path=DATA_PATH):
    return load_json_file(path)


def load_word_json(path=WORD_PATH):
    return load_json_file(path)


def normalize_text(text):
    if text is None:
        return ""
    text = str(text).replace("\u3000", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    text = text.replace("：", ":")
    return text.strip()


def normalize_for_match(text):
    normalized = normalize_text(text).lower()
    return re.sub(r"[，,。；;！!？?\-_/（）()\[\]【】\"'`~·:：]", "", normalized)


def split_text_units(text):
    normalized = normalize_text(text)
    if not normalized:
        return []
    units = []
    for chunk in re.split(r"(?:\n|(?<=。)|(?<=；)|(?<=;))", normalized):
        chunk = normalize_text(chunk)
        if not chunk:
            continue
        if chunk.startswith("- "):
            chunk = chunk[2:].strip()
        units.append(chunk)
    return units


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


def ensure_paragraphs(data):
    paragraphs = data.get("paragraphs") or []
    cleaned = [normalize_text(item) for item in paragraphs if normalize_text(item)]
    if cleaned:
        return cleaned
    raw_text = normalize_text(data.get("raw_text"))
    if not raw_text:
        return []
    return [item.strip() for item in re.split(r"\n+", raw_text) if item.strip()]


def build_client():
    api_key = (
        os.getenv("EXTRACT_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key, base_url=DEFAULT_BASE_URL)


def infer_field_type(field_name, raw_type):
    field_type = normalize_text(raw_type).lower()
    if field_type in {"int", "float", "double", "number", "numeric"}:
        return "numeric"
    if field_type in {"date", "datetime", "time"}:
        return "date"
    if field_type in {"category", "enum"}:
        return "category"

    if any(token in field_name for token in ["时间", "日期", "年月", "时点"]):
        return "date"
    if any(token in field_name for token in ["数值", "同比", "环比", "数量", "金额", "比重", "增速", "增长率", "占比", "单位"]):
        return "numeric" if field_name != "单位" else "text"
    if any(token in field_name for token in ["分类", "类别", "地区", "行业"]):
        return "category"
    return "text"


def build_field_tasks(word_config):
    # 将当前 word.json 的字段列定义转成内部任务对象。
    tasks = []
    for item in word_config.get("fields", []):
        field_name = normalize_text(item.get("field_name") or item.get("name") or item.get("word"))
        if not field_name:
            continue
        tasks.append(
            {
                "name": field_name,
                "type": infer_field_type(field_name, item.get("type") or "string"),
                "aliases": [normalize_text(alias) for alias in item.get("aliases", []) if normalize_text(alias)],
                "description": normalize_text(item.get("description") or ""),
                "multi": bool(item.get("multi", True)),
            }
        )
    return tasks


def build_description_prompt(raw_text, field_tasks):
    payload = {
        "task": "阅读原文后，为每个字段补充一个适合召回与抽取的 description，并给出可用别名。",
        "requirements": [
            "只基于原文语义理解字段在当前文档中的可能含义。",
            "description 应简短、可检索，适合后续 paragraph 召回。",
            "aliases 给出 0 到 5 个可能原文表达。",
            "如果无法判断，也要保留字段并给出保守 description。",
            "只输出 JSON。",
        ],
        "fields": [{"name": item["name"], "type": item["type"]} for item in field_tasks],
        "document": raw_text[:12000],
        "output_schema": {
            "fields": [
                {
                    "name": "字段名",
                    "description": "字段在当前文档中的含义描述",
                    "aliases": ["别名1", "别名2"],
                }
            ]
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def default_field_description(field_task):
    defaults = {
        "分类": "统计对象所属的类别、地区、层级或分组名称",
        "指标": "描述统计口径或指标名称，例如收入、人数、数量、增速等",
        "数值": "与指标对应的具体数值",
        "单位": "数值使用的单位，例如亿元、万人次、家、%",
        "时间": "该统计口径对应的时间、时点或年份",
        "同比": "同比增长、同比下降或同比变化幅度",
        "来源段落": "结果所在的主要段落编号",
    }
    return defaults.get(field_task["name"], f"与“{field_task['name']}”相关的文本信息")


def default_field_aliases(field_task):
    defaults = {
        "分类": ["全国", "东部地区", "中部地区", "西部地区", "城镇居民", "农村居民"],
        "指标": ["收入", "利润", "人数", "人次", "数量", "总量", "比重", "事业费", "营业收入"],
        "数值": ["亿元", "万人次", "万人", "家", "%", "个百分点"],
        "单位": ["亿元", "万元", "元", "家", "%", "个百分点", "万人次", "万人"],
        "时间": ["年末", "全年", "截至", "发布时间"],
        "同比": ["同比", "增长", "下降", "提高", "持平"],
    }
    return defaults.get(field_task["name"], [])


def enrich_field_tasks_with_descriptions(data, field_tasks, client, model=DEFAULT_MODEL):
    # 预处理：先让模型通读原文，为字段补充 description / aliases。
    raw_text = normalize_text(data.get("raw_text"))
    if not raw_text:
        raw_text = "\n".join(ensure_paragraphs(data))

    if client is None:
        enriched = []
        for item in field_tasks:
            clone = dict(item)
            if not clone.get("description"):
                clone["description"] = default_field_description(clone)
            clone["aliases"] = sorted(set(clone.get("aliases", []) + default_field_aliases(clone)))
            enriched.append(clone)
        return enriched

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是信息抽取预处理助手。只输出 JSON。"},
                {"role": "user", "content": build_description_prompt(raw_text, field_tasks)},
            ],
            temperature=0.1,
        )
        parsed = safe_load_json(completion.choices[0].message.content)
    except Exception:
        parsed = None

    description_map = {}
    if isinstance(parsed, dict):
        for item in parsed.get("fields", []):
            if not isinstance(item, dict):
                continue
            name = normalize_text(item.get("name"))
            if not name:
                continue
            aliases = item.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            description_map[name] = {
                "description": normalize_text(item.get("description")),
                "aliases": [normalize_text(alias) for alias in aliases if normalize_text(alias)],
            }

    enriched = []
    for item in field_tasks:
        clone = dict(item)
        llm_info = description_map.get(clone["name"], {})
        aliases = clone.get("aliases", []) + llm_info.get("aliases", []) + default_field_aliases(clone)
        clone["aliases"] = sorted({alias for alias in aliases if alias and alias != clone["name"]})
        clone["description"] = llm_info.get("description") or clone.get("description") or default_field_description(clone)
        enriched.append(clone)
    return enriched


def score_paragraph_for_task(field_task, paragraph):
    normalized_paragraph = normalize_for_match(paragraph)
    score = 0.0
    matched_terms = []

    for term in [field_task["name"], *field_task.get("aliases", [])]:
        normalized_term = normalize_for_match(term)
        if normalized_term and normalized_term in normalized_paragraph:
            score += 2.0 if term == field_task["name"] else 1.2
            matched_terms.append(term)

    for token in re.split(r"[\s,，;；/]+", field_task.get("description", "")):
        normalized_token = normalize_for_match(token)
        if len(normalized_token) >= 2 and normalized_token in normalized_paragraph:
            score += 0.35

    if field_task["type"] == "numeric" and re.search(r"\d", paragraph):
        score += 0.8
    if field_task["type"] == "date" and re.search(r"\d{4}[-/年]\d{1,2}([-/月]\d{1,2}日?)?", paragraph):
        score += 0.9
    if field_task["name"] == "来源段落":
        score = 0.0

    return round(score, 4), sorted(set(matched_terms))


def recall_candidate_paragraphs(field_task, paragraphs, top_k=MAX_FIELD_CANDIDATES):
    # 基于字段名、预处理 description、别名综合召回段落。
    recalled = []
    for para_id, paragraph in enumerate(paragraphs):
        score, matched_terms = score_paragraph_for_task(field_task, paragraph)
        if score <= 0:
            continue
        recalled.append(
            {
                "para_id": para_id,
                "paragraph": paragraph,
                "score": score,
                "matched_terms": matched_terms,
                "field_name": field_task["name"],
            }
        )
    recalled.sort(key=lambda item: (-item["score"], item["para_id"]))
    return recalled[:top_k]


def score_unit_for_fields(unit_text, field_tasks):
    total = 0.0
    hit_fields = set()
    matched_terms = set()
    for task in field_tasks:
        if task["name"] == "来源段落":
            continue
        score, terms = score_paragraph_for_task(task, unit_text)
        if score <= 0:
            continue
        total += score
        hit_fields.add(task["name"])
        matched_terms.update(terms)

    if re.search(r"\d", unit_text):
        total += 0.8
    if "同比" in unit_text or "增长" in unit_text or "下降" in unit_text:
        total += 0.6
    return round(total, 4), sorted(hit_fields), sorted(matched_terms)


def build_entity_candidates(field_tasks, paragraphs):
    # 将不同字段命中的文本单元聚合为“实体候选”，允许不同实体共享段落。
    unit_candidates = []
    for para_id, paragraph in enumerate(paragraphs):
        for unit_index, unit_text in enumerate(split_text_units(paragraph) or [paragraph]):
            score, fields, matched_terms = score_unit_for_fields(unit_text, field_tasks)
            if score <= 0:
                continue
            unit_candidates.append(
                {
                    "para_id": para_id,
                    "unit_index": unit_index,
                    "unit_text": unit_text,
                    "score": score,
                    "fields": fields,
                    "matched_terms": matched_terms,
                }
            )

    unit_candidates.sort(key=lambda item: (-item["score"], item["para_id"], item["unit_index"]))
    entities = []
    seen_signatures = set()
    for anchor in unit_candidates[:MAX_ENTITY_CANDIDATES]:
        para_ids = {anchor["para_id"]}
        for offset in range(-ENTITY_CONTEXT_WINDOW, ENTITY_CONTEXT_WINDOW + 1):
            candidate_id = anchor["para_id"] + offset
            if candidate_id < 0 or candidate_id >= len(paragraphs):
                continue
            para_ids.add(candidate_id)

        entity_paragraphs = [{"para_id": para_id, "text": paragraphs[para_id]} for para_id in sorted(para_ids)]
        signature = (anchor["para_id"], anchor["unit_index"], tuple(item["para_id"] for item in entity_paragraphs))
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        entities.append(
            {
                "anchor_para_id": anchor["para_id"],
                "anchor_unit_text": anchor["unit_text"],
                "score": anchor["score"],
                "fields": anchor["fields"],
                "matched_terms": anchor["matched_terms"],
                "paragraphs": entity_paragraphs,
            }
        )

    return entities


def build_entity_extraction_prompt(field_tasks, entity_candidate):
    payload = {
        "task": "你将看到同一个实体相关的一组段落。请基于这些段落抽取 1 条结构化结果。",
        "requirements": [
            "只输出一个实体对象，不要拆成多条。",
            "字段应尽量从段落原文中抽取，没有就返回空字符串。",
            "如果这组段落不足以形成有效实体，返回 matched=false。",
            "来源段落 填最主要证据所在的 para_id。",
            "优先围绕 anchor_unit_text 这条核心文本抽取，再参考相邻段落补全分类、时间、单位等。",
            "输出 record 时，键名必须严格使用 schema 中的字段名。",
            "不要输出 markdown，不要输出解释，只输出 JSON。",
        ],
        "schema": [{"field_name": item["name"], "type": item["type"], "description": item["description"], "aliases": item.get("aliases", [])} for item in field_tasks],
        "entity_candidate": entity_candidate,
        "output_schema": {
            "matched": False,
            "confidence": 0.0,
            "record": {item["name"]: "" for item in field_tasks},
            "evidence_para_id": -1,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def extract_first_numeric_with_unit(text):
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*(亿元|万元|元|万家|家|万人次|万人|人次|个|场|册|平方米|万平方米|亿册|%|个百分点)?", normalize_text(text))
    if not match:
        return "", ""
    return normalize_text(match.group(1)), normalize_text(match.group(2))


def extract_first_date(text):
    match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日|\d{4}年\d{1,2}月|\d{4}年|\d{4}-\d{1,2}-\d{1,2})", normalize_text(text))
    return normalize_text(match.group(1)) if match else ""


def find_category(text):
    patterns = [
        r"(全国)",
        r"(东部地区|中部地区|西部地区)",
        r"(城镇居民|农村居民)",
        r"(公共图书馆|群众文化机构|旅行社|星级饭店|A级景区)",
        r"(县以上|县及县以下)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_text(match.group(1))
    return ""


def find_indicator(text):
    patterns = [
        r"([\u4e00-\u9fa5A-Za-z0-9]+?)(?:为|达|共|有)\s*-?\d",
        r"([\u4e00-\u9fa5A-Za-z0-9]+?)同比(?:增长|下降|提高|减少)",
        r"([\u4e00-\u9fa5A-Za-z0-9]+?)(?:占比|比重|增长率)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = normalize_text(match.group(1))
            candidate = re.sub(r"^(全年|年末|其中|全国|全市|全省)", "", candidate)
            candidate = candidate.strip("，,。；;:： ")
            if candidate:
                return candidate
    return ""


def find_yoy(text):
    patterns = [
        r"(同比(?:增长|下降|提高|减少)?\s*-?\d+(?:\.\d+)?%)",
        r"(比上年(?:增长|下降|提高|减少)?\s*-?\d+(?:\.\d+)?(?:个百分点|%|元|亿元|万人次|万人|家)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_text(match.group(1))
    return ""


def find_value_and_unit(text):
    patterns = [
        r"(?:为|达|有|共|实现|收入|利润|接待游客|出游人次|事业费|平均房价|出租率)\s*(-?\d+(?:\.\d+)?)\s*(亿元|万元|元|万家|家|万人次|万人|人次|个|场|册|平方米|万平方米|亿册|%|个百分点)?",
        r"(-?\d+(?:\.\d+)?)\s*(亿元|万元|元|万家|家|万人次|万人|人次|个|场|册|平方米|万平方米|亿册|%|个百分点)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_text(match.group(1)), normalize_text(match.group(2))
    return "", ""


def choose_best_text_units(entity_candidate):
    units = []
    for para in entity_candidate["paragraphs"]:
        for unit in split_text_units(para["text"]):
            if unit == entity_candidate["anchor_unit_text"]:
                units.insert(0, {"para_id": para["para_id"], "text": unit})
            else:
                units.append({"para_id": para["para_id"], "text": unit})
    if not units:
        units = [{"para_id": para["para_id"], "text": para["text"]} for para in entity_candidate["paragraphs"]]
    return units


def fallback_extract_one_entity(field_tasks, entity_candidate):
    # 无模型时使用规则回退，至少保证流程可跑通。
    paragraphs = entity_candidate["paragraphs"]
    text_units = choose_best_text_units(entity_candidate)
    merged_text = " ".join(item["text"] for item in text_units)
    record = {task["name"]: "" for task in field_tasks}
    anchor_text = normalize_text(entity_candidate.get("anchor_unit_text", ""))
    anchor_para_id = entity_candidate["anchor_para_id"]

    category = find_category(merged_text)
    indicator = find_indicator(anchor_text) or find_indicator(merged_text)
    value, unit = find_value_and_unit(anchor_text)
    if not value:
        value, unit = find_value_and_unit(merged_text)
    time_value = extract_first_date(merged_text)
    yoy = find_yoy(anchor_text) or find_yoy(merged_text)

    for task in field_tasks:
        name = task["name"]
        if name == "来源段落":
            continue
        if name == "分类":
            record[name] = category
        elif name == "指标":
            record[name] = indicator
        elif name == "数值":
            record[name] = value
        elif name == "单位":
            record[name] = unit
        elif name == "时间":
            record[name] = time_value
        elif name == "同比":
            record[name] = yoy
        elif task["type"] == "date":
            record[name] = time_value
        elif task["type"] == "numeric":
            record[name] = value

    record["来源段落"] = anchor_para_id
    is_meaningful = any(normalize_text(value) for key, value in record.items() if key != "来源段落")
    return {
        "matched": is_meaningful,
        "confidence": 0.58 if is_meaningful else 0.0,
        "record": record,
        "evidence_para_id": anchor_para_id,
    }


def llm_extract_one_entity(field_tasks, entity_candidate, client, model=DEFAULT_MODEL):
    if client is None:
        return fallback_extract_one_entity(field_tasks, entity_candidate)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是实体级信息抽取助手。只输出 JSON。"},
                {"role": "user", "content": build_entity_extraction_prompt(field_tasks, entity_candidate)},
            ],
            temperature=0.1,
        )
        parsed = safe_load_json(completion.choices[0].message.content)
        if isinstance(parsed, dict):
            parsed.setdefault("matched", bool(parsed.get("record")))
            parsed.setdefault("confidence", 0.0)
            parsed.setdefault("record", {})
            parsed.setdefault("evidence_para_id", entity_candidate["anchor_para_id"])
            return parsed
    except Exception:
        pass

    return fallback_extract_one_entity(field_tasks, entity_candidate)


def normalize_record_value(field_task, value, record):
    value = normalize_text(value)
    name = field_task["name"]

    if name == "来源段落":
        try:
            return int(value)
        except Exception:
            return record.get("来源段落", -1)

    if field_task["type"] == "numeric" and name in {"数值", "同比"}:
        numeric, unit = extract_first_numeric_with_unit(value or record.get(name, ""))
        if name == "数值" and unit and not normalize_text(record.get("单位")):
            record["单位"] = unit
        return numeric or normalize_text(value)

    if name == "单位":
        _, unit = extract_first_numeric_with_unit(value)
        return unit or value

    if field_task["type"] == "date" or name == "时间":
        return extract_first_date(value) or value

    return value


def sanitize_entity_record(field_tasks, raw_record, entity_candidate, paragraphs, llm_confidence):
    record = {task["name"]: "" for task in field_tasks}
    for task in field_tasks:
        raw_value = raw_record.get(task["name"], "") if isinstance(raw_record, dict) else ""
        record[task["name"]] = normalize_record_value(task, raw_value, record)

    evidence_para_id = raw_record.get("来源段落", entity_candidate["anchor_para_id"]) if isinstance(raw_record, dict) else entity_candidate["anchor_para_id"]
    try:
        evidence_para_id = int(evidence_para_id)
    except Exception:
        evidence_para_id = entity_candidate["anchor_para_id"]
    if evidence_para_id < 0 or evidence_para_id >= len(paragraphs):
        evidence_para_id = entity_candidate["anchor_para_id"]

    record["来源段落"] = evidence_para_id
    record["_confidence"] = round(min(0.25 + min(entity_candidate["score"] / 6.0, 0.45) + min(max(float(llm_confidence), 0.0), 1.0) * 0.2, 0.99), 4)
    record["_entity_para_ids"] = [item["para_id"] for item in entity_candidate["paragraphs"]]
    return record


def sanitize_and_merge_results(results, field_tasks):
    cleaned = []
    seen = set()
    field_names = [task["name"] for task in field_tasks]

    for item in results:
        if not isinstance(item, dict):
            continue
        if not any(normalize_text(item.get(field_name)) for field_name in field_names if field_name != "来源段落"):
            continue

        dedupe_key = tuple(normalize_text(item.get(field_name)) for field_name in field_names)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        result = {field_name: item.get(field_name, "" if field_name != "来源段落" else -1) for field_name in field_names}
        if "来源段落" in result:
            try:
                result["来源段落"] = int(result["来源段落"])
            except Exception:
                result["来源段落"] = -1
        cleaned.append(result)

    cleaned.sort(key=lambda item: item.get("来源段落", -1))
    return cleaned


def extract(data, word_config=None, client=None, model=DEFAULT_MODEL):
    paragraphs = ensure_paragraphs(data)
    word_config = load_word_json() if word_config is None else word_config
    field_tasks = build_field_tasks(word_config)
    client = build_client() if client is None else client

    enriched_field_tasks = enrich_field_tasks_with_descriptions(data, field_tasks, client=client, model=model)
    entity_candidates = build_entity_candidates(enriched_field_tasks, paragraphs)

    all_records = []
    for entity_candidate in entity_candidates:
        extracted = llm_extract_one_entity(enriched_field_tasks, entity_candidate, client=client, model=model)
        if not extracted.get("matched"):
            continue
        record = sanitize_entity_record(
            enriched_field_tasks,
            extracted.get("record", {}),
            entity_candidate,
            paragraphs,
            extracted.get("confidence", 0.0),
        )
        all_records.append(record)

    return {
        "doc_id": normalize_text(data.get("doc_id", "")),
        "table_id": normalize_text(word_config.get("table_id", "")),
        "results": sanitize_and_merge_results(all_records, enriched_field_tasks),
    }


def main():
    data = load_data_json()
    word_config = load_word_json()
    result = extract(data, word_config=word_config)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
