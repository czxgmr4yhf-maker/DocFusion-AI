from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.db.database import get_db
from app.db.models import Task

router = APIRouter(prefix="/fields", tags=["fields"])


def safe_load_json(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


def build_parse_summary(parse_result):
    if not isinstance(parse_result, dict):
        return parse_result

    paragraphs = parse_result.get("paragraphs")
    tables = parse_result.get("tables")
    raw_text = parse_result.get("raw_text")

    return {
        "doc_id": parse_result.get("doc_id"),
        "doc_type": parse_result.get("doc_type"),
        "paragraph_count": len(paragraphs) if isinstance(paragraphs, list) else None,
        "table_count": len(tables) if isinstance(tables, list) else None,
        "raw_text_preview": str(raw_text)[:500] if raw_text else None
    }


def resolve_pipeline(parse_result, extract_result, match_result):
    if isinstance(match_result, dict):
        match_status = match_result.get("match_status")
        if match_status == "success":
            return "match"
        if match_status == "skipped":
            return match_result.get("pipeline_used", "extract")

    if extract_result:
        return "extract"

    if parse_result:
        return "parse"

    return "unknown"


def resolve_match_status(match_result):
    if isinstance(match_result, dict):
        return match_result.get("match_status")
    return None


@router.get("/{task_id}")
def get_fields(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    parse_result = safe_load_json(task.result)
    extract_result = safe_load_json(task.extract_result)
    match_result = safe_load_json(task.match_result)

    pipeline_used = resolve_pipeline(parse_result, extract_result, match_result)
    match_status = resolve_match_status(match_result)

    return {
        "task_id": task.id,
        "file_name": task.file_name,
        "file_type": task.file_type,
        "status": task.status,
        "pipeline_used": pipeline_used,
        "match_status": match_status,
        "parse_result_summary": build_parse_summary(parse_result),
        "extract_result": extract_result,
        "match_result": match_result,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.get("/{task_id}/source/{field_name}")
def get_field_source(task_id: int, field_name: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    match_result = safe_load_json(task.match_result)
    if not isinstance(match_result, dict):
        raise HTTPException(status_code=404, detail="当前任务没有 matcher 结果")

    if match_result.get("match_status") != "success":
        raise HTTPException(status_code=404, detail="当前任务未生成可用的 matcher 字段来源")

    matched = match_result.get("matched_result", {})
    input_data = match_result.get("input_data", {})

    if field_name not in matched:
        raise HTTPException(
            status_code=400,
            detail=f"当前 matcher 结果中不包含字段：{field_name}"
        )

    value = matched.get(field_name)

    source_key = None
    for k, v in input_data.items():
        if v == value:
            source_key = k
            break

    return {
        "task_id": task.id,
        "field_name": field_name,
        "value": value,
        "source_file": task.file_name,
        "source_key": source_key,
        "source_paragraph": None,
        "source_text": None,
    }