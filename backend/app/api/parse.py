from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Task
from app.core.logger import logger
import json

router = APIRouter()


def fake_parse_document(file_path: str):
    return {
        "doc_id": file_path,
        "paragraphs": ["这是测试段落1", "这是测试段落2"],
        "tables": [],
        "raw_text": "这是模拟解析出来的全文内容"
    }


@router.post("/parse/{task_id}")
def parse_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        parse_result = fake_parse_document(task.file_path)

        task.status = "parsed"
        task.result = json.dumps(parse_result, ensure_ascii=False)
        db.commit()
        db.refresh(task)

        logger.info(f"任务解析成功: task_id={task.id}")

        return {
            "message": "解析成功",
            "task_id": task.id,
            "status": task.status,
            "result": parse_result
        }

    except Exception as e:
        task.status = "failed"
        db.commit()
        logger.error(f"任务解析失败: task_id={task.id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")