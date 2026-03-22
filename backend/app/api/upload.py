from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil

from app.db.database import SessionLocal
from app.db.models import Task
from app.api.parse import run_parse
from app.api.extract import run_extract

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # 1 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db = SessionLocal()
    try:
        # 2 创建任务
        task = Task(
            file_name=file.filename,
            file_path=file_path,
            file_type=file.filename.split(".")[-1] if "." in file.filename else "",
            status="uploaded"
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        # 3 自动解析
        parse_result = run_parse(task.id, db)

        # 4 自动抽取
        extract_result = run_extract(task.id, db)

        # 5 更新最终状态
        task.status = "extracted"
        task.error_message = None
        db.commit()
        db.refresh(task)

        return {
            "message": "文件上传并自动处理成功",
            "task_id": task.id,
            "status": task.status,
            "parse_message": parse_result["message"],
            "extract_message": extract_result["message"]
        }

    except HTTPException as e:
        try:
            if "task" in locals():
                task.status = "failed"
                task.error_message = str(e.detail)
                db.commit()
        except Exception:
            pass
        raise e

    except Exception as e:
        try:
            if "task" in locals():
                task.status = "failed"
                task.error_message = str(e)
                db.commit()
        except Exception:
            pass

        raise HTTPException(status_code=500, detail=f"上传后自动处理失败: {str(e)}")

    finally:
        db.close()