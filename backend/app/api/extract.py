from fastapi import APIRouter

router = APIRouter()


@router.post("/extract/{task_id}")
def extract_task(task_id: int):
    return {
        "message": "信息抽取接口（占位）",
        "task_id": task_id,
        "status": "extracted"
    }