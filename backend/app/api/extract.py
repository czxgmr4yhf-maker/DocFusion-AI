from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import re

from app.db.database import get_db
from app.db.models import DocumentField, Task

router = APIRouter()


@router.post("/extract/{task_id}")
def extract_task(task_id: int, db: Session = Depends(get_db)):

    # 1 查询任务
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 2 读取文件
    try:
        with open(task.file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        raise HTTPException(status_code=500, detail="文件读取失败")

    # 3 正则抽取字段
    project_name = None
    project_leader = None
    organization_name = None
    phone = None

    m = re.search(r"项目名称[:：]\s*(.+)", text)
    if m:
        project_name = m.group(1).strip()

    m = re.search(r"负责人[:：]\s*(.+)", text)
    if m:
        project_leader = m.group(1).strip()

    m = re.search(r"单位名称[:：]\s*(.+)", text)
    if m:
        organization_name = m.group(1).strip()

    m = re.search(r"1\d{10}", text)
    if m:
        phone = m.group(0)

    # 4 写入数据库
    field_data = DocumentField(
        task_id=task_id,
        doc_id=f"doc_{task_id}",
        doc_type=task.file_type,
        raw_text=text,
        paragraphs="[]",
        tables="[]",
        project_name=project_name,
        project_leader=project_leader,
        organization_name=organization_name,
        phone=phone
    )

    db.add(field_data)
    db.commit()

    return {
        "message": "字段抽取完成",
        "task_id": task_id
    }