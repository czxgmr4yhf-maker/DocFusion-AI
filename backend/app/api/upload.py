from fastapi import APIRouter, UploadFile, File
import os
import shutil
from app.db.database import SessionLocal
from app.db.models import Task

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db = SessionLocal()
    try:
        task = Task(
            file_name=file.filename,
            file_path=file_path,
            file_type=file.filename.split(".")[-1] if "." in file.filename else "",
            status="uploaded"
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return {"task_id": task.id, "status": task.status}
    finally:
        db.close()