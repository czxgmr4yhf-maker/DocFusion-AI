from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import re
import json

from app.db.database import get_db
from app.db.models import DocumentField, Task

router = APIRouter()


def run_extract(task_id: int, db: Session):
    # 1 查询任务
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 2 读取解析结果
    if not task.result:
        raise HTTPException(status_code=400, detail="请先完成解析，再进行字段抽取")

    try:
        parse_data = json.loads(task.result)
    except Exception:
        raise HTTPException(status_code=500, detail="解析结果读取失败")

    text = parse_data.get("raw_text", "")
    paragraphs = parse_data.get("paragraphs", [])
    tables = parse_data.get("tables", [])

    if not text.strip():
        raise HTTPException(status_code=400, detail="解析结果为空，无法抽取字段")

    # 3 正则抽取字段
    category = None
    indicator = None
    value = None

    m = re.search(r"(?:分类|类别)[:：]\s*(.+)", text)
    if m:
        category = m.group(1).strip()

    m = re.search(r"指标[:：]\s*(.+)", text)
    if m:
        indicator = m.group(1).strip()

    m = re.search(r"(?:数值|值)[:：]\s*(.+)", text)
    if m:
        value = m.group(1).strip()

    # 4 避免重复插入同一个 task_id 的结果
    old_field = db.query(DocumentField).filter(DocumentField.task_id == task_id).first()
    if old_field:
        db.delete(old_field)
        db.commit()

    # 5 写入数据库
    field_data = DocumentField(
        task_id=task_id,
        doc_id=parse_data.get("doc_id", f"doc_{task_id}"),
        doc_type=task.file_type,
        raw_text=text,
        paragraphs=json.dumps(paragraphs, ensure_ascii=False),
        tables=json.dumps(tables, ensure_ascii=False),
        category=category,
        indicator=indicator,
        value=value
    )

    db.add(field_data)
    db.commit()
    db.refresh(field_data)

    return {
        "message": "字段抽取完成",
        "task_id": task_id,
        "category": category,
        "indicator": indicator,
        "value": value
    }


@router.post("/extract/{task_id}")
def extract_task(task_id: int, db: Session = Depends(get_db)):
    return run_extract(task_id, db)
