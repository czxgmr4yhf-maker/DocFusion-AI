from fastapi import APIRouter, Depends, HTTPException, Query
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


def get_paragraph_text(paragraphs, paragraph_index):
    if paragraph_index is None:
        return None

    if not isinstance(paragraphs, list) or not paragraphs:
        return None

    # 先按 0-based
    if 0 <= paragraph_index < len(paragraphs):
        return str(paragraphs[paragraph_index])

    # 再兼容 1-based
    idx = paragraph_index - 1
    if 0 <= idx < len(paragraphs):
        return str(paragraphs[idx])

    return None


@router.get("/trace/{task_id}")
def trace_field(
    task_id: int,
    record_index: int | None = Query(None, description="抽取结果中的第几条，从0开始"),
    indicator: str | None = Query(None, description="抽取结果中的 指标"),
    value: str | None = Query(None, description="可选，抽取结果中的 数值"),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.result:
        raise HTTPException(status_code=400, detail="当前任务没有解析结果")

    task_result = safe_json_loads(task.result)
    if not isinstance(task_result, dict):
        raise HTTPException(status_code=500, detail="task.result 不是有效 JSON")

    paragraphs = ensure_list(task_result.get("paragraphs"))
    extract_result = task_result.get("extract_result", {})
    results = extract_result.get("results", []) if isinstance(extract_result, dict) else []

    if not isinstance(results, list) or not results:
        raise HTTPException(status_code=404, detail="当前任务没有抽取结果")

    matched_record = None
    matched_index = None

    # 优先按 record_index 查
    if record_index is not None:
        if record_index < 0 or record_index >= len(results):
            raise HTTPException(status_code=400, detail="record_index 超出范围")
        item = results[record_index]
        if not isinstance(item, dict):
            raise HTTPException(status_code=404, detail="该索引位置不是有效记录")
        matched_record = item
        matched_index = record_index
    else:
        # 再兼容旧逻辑：按 indicator + value 查
        if not indicator:
            raise HTTPException(
                status_code=400,
                detail="请提供 record_index，或至少提供 indicator"
            )

        for idx, item in enumerate(results):
            if not isinstance(item, dict):
                continue

            item_indicator = str(item.get("指标", "")).strip()
            item_value = str(item.get("数值", "")).strip()

            if item_indicator != indicator.strip():
                continue

            if value is not None and item_value != value.strip():
                continue

            matched_record = item
            matched_index = idx
            break

    if matched_record is None:
        raise HTTPException(status_code=404, detail="未找到匹配的抽取结果")

    source_paragraph = matched_record.get("来源段落")
    try:
        source_paragraph = int(source_paragraph) if source_paragraph is not None else None
    except Exception:
        source_paragraph = None

    source_text = get_paragraph_text(paragraphs, source_paragraph)

    return {
        "task_id": task.id,
        "file_name": task.file_name,
        "record_index": matched_index,
        "indicator": matched_record.get("指标"),
        "value": matched_record.get("数值"),
        "unit": matched_record.get("单位"),
        "time": matched_record.get("时间"),
        "yoy": matched_record.get("同比"),
        "source_paragraph": source_paragraph,
        "source_text": source_text,
        "record": matched_record
    }