from fastapi import APIRouter
from app.db.database import SessionLocal
from app.db.models import Task

router = APIRouter()


@router.get("/tasks/{task_id}")
def get_task(task_id: int):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            return {"error": "task not found"}

        return {
            "task_id": task.id,
            "file_name": task.file_name,
            "file_path": task.file_path,
            "file_type": task.file_type,
            "status": task.status,
            "error_message": task.error_message,
            "result": task.result,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
    finally:
        db.close()