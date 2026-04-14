from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.db.database import get_db
from app.db.models import Task

router = APIRouter()


def safe_json_loads(value):
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}
    return {}


def ensure_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed = safe_json_loads(value)
        if isinstance(parsed, list):
            return parsed
    return []


def build_parse_result_summary(task_result: dict):
    paragraphs = ensure_list(task_result.get("paragraphs"))
    tables = ensure_list(task_result.get("tables"))
    raw_text = task_result.get("raw_text") or ""

    return {
        "doc_id": task_result.get("doc_id"),
        "doc_type": task_result.get("doc_type"),
        "paragraph_count": len(paragraphs),
        "table_count": len(tables),
        "raw_text_preview": str(raw_text)[:1000] if raw_text is not None else ""
    }


def build_pipeline_used(match_result: dict, extract_result: dict):
    if isinstance(match_result, dict) and match_result.get("match_status") == "success":
        return "match"
    if isinstance(extract_result, dict) and isinstance(extract_result.get("results"), list) and extract_result.get("results"):
        return "extract"
    return "unknown"


def get_source_text_from_paragraphs(paragraphs, paragraph_index):
    if paragraph_index is None:
        return None
    if not isinstance(paragraphs, list) or not paragraphs:
        return None

    try:
        paragraph_index = int(paragraph_index)
    except Exception:
        return None

    # 优先按 0-based
    if 0 <= paragraph_index < len(paragraphs):
        return str(paragraphs[paragraph_index])

    # 再兼容 1-based
    idx = paragraph_index - 1
    if 0 <= idx < len(paragraphs):
        return str(paragraphs[idx])

    return None


def find_source_record(task_result: dict, field_name: str):
    """
    给旧前端的 /fields/{task_id}/source/{field_name} 做兼容。

    优先级：
    0. 优先命中 match_result.matched_trace_map[field_name]
    1. 直接命中旧 source 字段
    2. 命中 match_result.matched_result[field_name] 的值，再去 extract_result 里反查
    3. 直接在 extract_result.results 里按字段名/指标名模糊找
    """
    extract_result = task_result.get("extract_result", {})
    results = extract_result.get("results", []) if isinstance(extract_result, dict) else []

    match_result = task_result.get("match_result", {})
    matched_result = match_result.get("matched_result", {}) if isinstance(match_result, dict) else {}
    matched_trace_map = match_result.get("matched_trace_map", {}) if isinstance(match_result, dict) else {}

    paragraphs = ensure_list(task_result.get("paragraphs"))

    # 0) 优先查 match_result 里的 matched_trace_map
    if isinstance(matched_trace_map, dict) and field_name in matched_trace_map:
        trace = matched_trace_map.get(field_name) or {}
        return {
            "source_file": trace.get("source_file"),
            "source_key": trace.get("source_key") or field_name,
            "value": trace.get("value"),
            "source_paragraph": trace.get("source_paragraph"),
            "source_text": trace.get("source_text"),
            "record_index": trace.get("record_index"),
            "raw_record": trace.get("raw_record")
        }

    # 1) 兼容旧表单字段
    legacy_value = task_result.get(field_name)
    legacy_source_file = task_result.get(f"{field_name}_source_file")
    legacy_source_paragraph = task_result.get(f"{field_name}_source_paragraph")
    legacy_source_text = task_result.get(f"{field_name}_source_text")
    if legacy_value or legacy_source_file or legacy_source_paragraph or legacy_source_text:
        return {
            "source_file": legacy_source_file,
            "source_key": field_name,
            "value": legacy_value,
            "source_paragraph": legacy_source_paragraph,
            "source_text": legacy_source_text,
            "record_index": None,
            "raw_record": None
        }

    # 2) 如果 match_result 里有这个字段，拿 value 去 extract_result 里反查
    target_value = None
    if isinstance(matched_result, dict) and field_name in matched_result:
        target_value = matched_result.get(field_name)

    if isinstance(results, list):
        if target_value is not None:
            for idx, item in enumerate(results):
                if not isinstance(item, dict):
                    continue
                if str(item.get("数值", "")).strip() == str(target_value).strip():
                    source_paragraph = item.get("来源段落")
                    return {
                        "source_file": None,
                        "source_key": item.get("指标") or field_name,
                        "value": item.get("数值"),
                        "source_paragraph": source_paragraph,
                        "source_text": get_source_text_from_paragraphs(paragraphs, source_paragraph),
                        "record_index": idx,
                        "raw_record": item
                    }

        # 3) 直接按字段名模糊找
        aliases = {
            "project_name": ["项目名称"],
            "project_leader": ["项目负责人", "负责人"],
            "organization_name": ["申报单位", "单位名称", "公司名称", "企业名称"],
            "phone": ["联系电话", "电话", "手机号"],
            "负责人": ["项目负责人", "负责人"],
            "项目名称": ["项目名称"],
            "联系电话": ["联系电话", "电话", "手机号"],
            "单位名称": ["申报单位", "单位名称", "公司名称", "企业名称"],
        }
        candidates = [field_name]
        candidates.extend(aliases.get(field_name, []))

        for idx, item in enumerate(results):
            if not isinstance(item, dict):
                continue

            indicator = str(item.get("指标", "")).strip()
            for candidate in candidates:
                if candidate and candidate in indicator:
                    source_paragraph = item.get("来源段落")
                    return {
                        "source_file": None,
                        "source_key": indicator or field_name,
                        "value": item.get("数值"),
                        "source_paragraph": source_paragraph,
                        "source_text": get_source_text_from_paragraphs(paragraphs, source_paragraph),
                        "record_index": idx,
                        "raw_record": item
                    }

    return None


@router.get("/fields/{task_id}")
def get_fields(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.result:
        raise HTTPException(status_code=400, detail="当前任务没有结果")

    task_result = safe_json_loads(task.result)
    if not isinstance(task_result, dict):
        raise HTTPException(status_code=500, detail="task.result 不是有效 JSON")

    # 兼容：优先从合并后的 task.result 里拿，没有再从独立字段里拿
    extract_result = task_result.get("extract_result")
    if not isinstance(extract_result, dict):
        extract_result = safe_json_loads(task.extract_result)
        if not isinstance(extract_result, dict):
            extract_result = {}

    match_result = task_result.get("match_result")
    if not isinstance(match_result, dict):
        match_result = safe_json_loads(task.match_result)
        if not isinstance(match_result, dict):
            match_result = {}

    results = extract_result.get("results", []) if isinstance(extract_result, dict) else []
    if not isinstance(results, list):
        results = []

    formatted_results = []
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            continue

        formatted_results.append({
            "record_index": idx,
            "category": item.get("分类"),
            "indicator": item.get("指标"),
            "value": item.get("数值"),
            "unit": item.get("单位"),
            "time": item.get("时间"),
            "yoy": item.get("同比"),
            "source_paragraph": item.get("来源段落"),
            "raw_record": item
        })

    parse_result_summary = build_parse_result_summary(task_result)
    pipeline_used = build_pipeline_used(match_result, extract_result)

    return {
        # 前端旧代码正在用的字段
        "task_id": task.id,
        "pipeline_used": pipeline_used,
        "parse_result_summary": parse_result_summary,
        "extract_result": extract_result,
        "match_result": match_result,

        # 你现在新做的字段，继续保留
        "file_name": task.file_name,
        "doc_id": task_result.get("doc_id"),
        "doc_type": extract_result.get("doc_type") if isinstance(extract_result, dict) else None,
        "total": len(formatted_results),
        "results": formatted_results
    }


@router.get("/fields/{task_id}/source/{field_name}")
def get_field_source(task_id: int, field_name: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.result:
        raise HTTPException(status_code=400, detail="当前任务没有结果")

    task_result = safe_json_loads(task.result)
    if not isinstance(task_result, dict):
        raise HTTPException(status_code=500, detail="task.result 不是有效 JSON")

    source_data = find_source_record(task_result, field_name)
    if source_data is None:
        raise HTTPException(status_code=404, detail=f"未找到字段 {field_name} 的溯源信息")

    return {
        "task_id": task.id,
        "field_name": field_name,
        "source_file": source_data.get("source_file") or task.file_name,
        "source_key": source_data.get("source_key") or field_name,
        "value": source_data.get("value"),
        "source_paragraph": source_data.get("source_paragraph"),
        "source_text": source_data.get("source_text"),
        "record_index": source_data.get("record_index"),
        "raw_record": source_data.get("raw_record")
    }