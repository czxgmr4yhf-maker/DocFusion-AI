from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import sys

from app.db.database import get_db
from app.db.models import DocumentField

router = APIRouter()

# 把项目根目录加入 Python 路径
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from matcher.semantic_matcher import FieldSemanticMatcher

matcher = FieldSemanticMatcher()


@router.post("/match/{task_id}")
def match_task(task_id: int, db: Session = Depends(get_db)):
    # 1 查询抽取结果
    field_data = db.query(DocumentField).filter(DocumentField.task_id == task_id).first()

    if not field_data:
        raise HTTPException(status_code=404, detail="未找到抽取结果，请先执行 /extract")

    # 2 组装传给 matcher 的数据
    raw_data = {}

    if field_data.category:
        raw_data["分类"] = field_data.category
    if field_data.indicator:
        raw_data["指标"] = field_data.indicator
    if field_data.value:
        raw_data["数值"] = field_data.value

    if not raw_data:
        raise HTTPException(status_code=400, detail="当前没有可匹配的字段，请先检查抽取结果")

    # 3 调用 matcher
    matched_result = matcher.process_data(raw_data)

    # 4 返回结果
    return {
        "task_id": task_id,
        "input_data": raw_data,
        "matched_result": matched_result
    }
