from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Task
from app.services.file_service import save_upload_file
from app.core.logger import logger
import os

router = APIRouter()


@router.post("/upload")
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        file_path = save_upload_file(file)
        file_size = os.path.getsize(file_path)

        task = Task(
            filename=file.filename,
            file_path=file_path,
            status="uploaded",
            result=None
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(f"文件上传成功: {file.filename}, task_id={task.id}")

        return {
            "message": "文件上传成功",
            "task_id": task.id,
            "filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "status": task.status
        }

    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")