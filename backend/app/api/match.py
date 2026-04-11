from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import json
import sys

from app.db.database import get_db
from app.db.models import Task

router = APIRouter()

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

_matcher = None


def get_matcher():
    global _matcher

    if _matcher is None:
        try:
            from matcher.semantic_matcher import FieldSemanticMatcher
            _matcher = FieldSemanticMatcher()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"matcher 初始化失败: {str(e)}")

    return _matcher


def safe_load_json(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


def extract_kv_from_text_line(line: str, result: dict):
    if not line:
        return

    text = str(line).strip()
    if not text:
        return

    text = text.lstrip("-•* ").strip()

    for sep in ["：", ":"]:
        if sep in text:
            key, value = text.split(sep, 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                result[key] = value
            return


def build_input_data_from_parse(parse_data: dict):
    input_data = {}

    if not isinstance(parse_data, dict):
        return input_data

    paragraphs = parse_data.get("paragraphs", [])
    if isinstance(paragraphs, list):
        for item in paragraphs:
            if isinstance(item, str):
                extract_kv_from_text_line(item, input_data)

    raw_text = parse_data.get("raw_text", "")
    if raw_text and not input_data:
        for line in str(raw_text).splitlines():
            extract_kv_from_text_line(line, input_data)

    return input_data


def is_suitable_for_match(parse_data: dict, input_data: dict):
    """
    自动判断当前文件是否适合走 matcher。
    规则：
    1. 必须先能抽出一些 键:值
    2. 更偏向短字段名、业务字段名、键值对密度高的文本
    3. 对统计报告 / 表格 / 超长描述文本，倾向跳过 matcher
    """
    if not input_data:
        return False, "当前文件不包含适合 matcher 处理的“字段名:字段值”键值对"

    business_keywords = [
        "姓名", "名称", "项目名称", "联系人", "联系电话", "电话", "手机号", "邮箱",
        "单位", "公司", "学校", "学院", "专业", "预算", "金额", "负责人",
        "招考单位", "人数", "地址", "法人", "信用代码", "证件号"
    ]

    keys = list(input_data.keys())
    values = list(input_data.values())

    key_count = len(keys)
    avg_key_len = sum(len(str(k)) for k in keys) / key_count if key_count else 999
    short_key_count = sum(1 for k in keys if len(str(k)) <= 12)
    business_key_count = sum(
        1 for k in keys
        if any(keyword in str(k) for keyword in business_keywords)
    )
    very_long_value_count = sum(1 for v in values if len(str(v)) >= 40)

    paragraphs = parse_data.get("paragraphs", [])
    tables = parse_data.get("tables", [])
    paragraph_count = len(paragraphs) if isinstance(paragraphs, list) else 0
    table_count = len(tables) if isinstance(tables, list) else 0

    score = 0

    # 正向信号
    if key_count >= 3:
        score += 2
    if short_key_count >= max(2, key_count // 2):
        score += 2
    if business_key_count >= 1:
        score += 3
    if avg_key_len <= 10:
        score += 1

    # 负向信号：更像报告/表格/长文本
    if very_long_value_count >= max(1, key_count // 2):
        score -= 2
    if paragraph_count >= 30 and business_key_count == 0:
        score -= 2
    if table_count >= 1 and business_key_count == 0:
        score -= 1
    if avg_key_len >= 18:
        score -= 2

    if score >= 3:
        return True, "当前文件具备较明显的业务键值对特征，适合 matcher"

    return False, "当前文件更像统计/报告/表格内容，优先走 extract"


def build_skipped_result(reason: str, pipeline_used: str):
    return {
        "pipeline_used": pipeline_used,
        "match_status": "skipped",
        "reason": reason,
        "input_data": {},
        "matched_result": None
    }


@router.post("/match/{task_id}")
def match_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.result:
        raise HTTPException(status_code=400, detail="请先完成解析，再进行字段匹配")

    parse_data = safe_load_json(task.result)
    if not isinstance(parse_data, dict):
        raise HTTPException(status_code=500, detail="解析结果格式异常，无法执行 matcher")

    input_data = build_input_data_from_parse(parse_data)
    suitable, reason = is_suitable_for_match(parse_data, input_data)

    if not suitable:
        pipeline_used = "extract" if task.extract_result else "parse"
        skipped_result = build_skipped_result(reason, pipeline_used)

        task.match_result = json.dumps(skipped_result, ensure_ascii=False)
        task.error_message = None

        if task.extract_result:
            task.status = "extracted"
        else:
            task.status = "parsed"

        db.commit()
        db.refresh(task)

        return {
            "message": "当前文件不适合 matcher，已自动跳过",
            "task_id": task.id,
            "status": task.status,
            "match_result": skipped_result
        }

    matcher = get_matcher()

    try:
        matched_result = matcher.process_data(input_data)

        save_data = {
            "pipeline_used": "match",
            "match_status": "success",
            "reason": None,
            "input_data": input_data,
            "matched_result": matched_result
        }

        task.match_result = json.dumps(save_data, ensure_ascii=False)
        task.status = "matched"
        task.error_message = None
        db.commit()
        db.refresh(task)

        return {
            "message": "字段标准化完成",
            "task_id": task.id,
            "status": task.status,
            "match_result": save_data
        }

    except Exception as e:
        task.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"字段匹配失败: {str(e)}")