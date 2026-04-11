import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])


def safe_json_loads(value):
    if value is None:
        return {}
    if isinstance(value, dict):
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


def build_parse_result_summary(result_data: dict) -> dict | None:
    """
    从 task.result 里提取统一的 parse_result_summary
    """
    if not isinstance(result_data, dict) or not result_data:
        return None

    # 如果本来就有 parse_result_summary，直接用
    if isinstance(result_data.get("parse_result_summary"), dict):
        return result_data.get("parse_result_summary")

    paragraphs = result_data.get("paragraphs", [])
    tables = result_data.get("tables", [])
    raw_text = result_data.get("raw_text", "") or ""

    if not isinstance(paragraphs, list):
        paragraphs = []
    if not isinstance(tables, list):
        tables = []

    summary = {
        "doc_id": result_data.get("doc_id"),
        "doc_type": result_data.get("doc_type"),
        "paragraph_count": len(paragraphs),
        "table_count": len(tables),
        "raw_text_preview": raw_text[:1000] if isinstance(raw_text, str) else str(raw_text)[:1000],
    }

    return summary


@router.get("/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    result_data = safe_json_loads(task.result)

    parse_result_summary = build_parse_result_summary(result_data)

    # 统一抽取结果出口
    extract_result = result_data.get("extract_result")
    if not isinstance(extract_result, dict):
        extract_result = None

    # 如果后面还有 match 逻辑，也留出口
    match_result = result_data.get("match_result")
    if not isinstance(match_result, dict):
        match_result = None

    return {
        "task_id": task.id,
        "file_name": task.file_name,
        "file_path": task.file_path,
        "file_type": task.file_type,
        "status": task.status,
        "error_message": task.error_message,

        # 保留原始 result，兼容旧前端/旧逻辑
        "result": task.result,

        # 新的统一结构
        "parse_result_summary": parse_result_summary,
        "extract_result": extract_result,
        "match_result": match_result,

        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }