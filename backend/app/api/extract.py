from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import importlib.util
import json
import sys

from app.db.database import get_db
from app.db.models import Task

router = APIRouter()

ROOT_DIR = Path(__file__).resolve().parents[3]
EXTRACT_DIR = ROOT_DIR / "extract"
EXTRACT_FILE = EXTRACT_DIR / "extract_ai_1.0.py"
WORD_JSON = EXTRACT_DIR / "word.json"

_extract_module = None
_word_config_cache = None


def load_extract_module():
    global _extract_module

    if _extract_module is not None:
        return _extract_module

    if not EXTRACT_FILE.exists():
        raise FileNotFoundError(f"未找到抽取模块文件: {EXTRACT_FILE}")

    spec = importlib.util.spec_from_file_location("extract_ai_module", EXTRACT_FILE)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载抽取模块: {EXTRACT_FILE}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["extract_ai_module"] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "extract"):
        raise AttributeError("extract_ai_1.0.py 中未找到 extract 函数")

    _extract_module = module
    return _extract_module


def load_word_config():
    global _word_config_cache

    if _word_config_cache is not None:
        return _word_config_cache

    if not WORD_JSON.exists():
        raise FileNotFoundError(f"未找到词表配置文件: {WORD_JSON}")

    _word_config_cache = json.loads(WORD_JSON.read_text(encoding="utf-8"))
    return _word_config_cache


def run_extract(task_id: int, db: Session):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.result:
        raise HTTPException(status_code=400, detail="请先完成解析，再进行字段抽取")

    try:
        parse_data = json.loads(task.result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析结果读取失败: {str(e)}")

    try:
        module = load_extract_module()
        word_config = load_word_config()

        extract_result = module.extract(parse_data, word_config=word_config)

        task.extract_result = json.dumps(extract_result, ensure_ascii=False)
        task.status = "extracted"
        task.error_message = None
        db.commit()
        db.refresh(task)

        return {
            "message": "字段抽取完成",
            "task_id": task.id,
            "status": task.status,
            "extract_result": extract_result
        }

    except Exception as e:
        task.status = "extract_failed"
        task.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"字段抽取失败: {str(e)}")


@router.post("/extract/{task_id}")
def extract_task(task_id: int, db: Session = Depends(get_db)):
    return run_extract(task_id, db)