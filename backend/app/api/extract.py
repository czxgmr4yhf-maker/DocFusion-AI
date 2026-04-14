from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import importlib.util
import json
import sys

from app.db.database import get_db
from app.db.models import Task, DocumentField, ExtractedEntity

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


def safe_json_loads(value):
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}
    return {}


def ensure_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed = safe_json_loads(value)
        if isinstance(parsed, list):
            return parsed
    return []


def normalize_extract_result(extract_result, parse_data: dict, task: Task):
    """
    统一抽取结果结构：
    1. 如果算法返回 {"results": [...]}，直接保留
    2. 如果算法返回单条 dict（比如 分类/指标/数值/...），包装成 results=[该dict]
    3. 如果算法返回 list，包装成 results=list
    """
    base = {
        "doc_id": parse_data.get("doc_id"),
        "doc_type": task.file_type,
        "table_id": "table_001",
        "results": []
    }

    if isinstance(extract_result, dict):
        result = dict(extract_result)
        result.setdefault("doc_id", parse_data.get("doc_id"))
        result.setdefault("doc_type", task.file_type)
        result.setdefault("table_id", "table_001")

        if isinstance(result.get("results"), list):
            return result

        record = {
            k: v for k, v in result.items()
            if k not in {"doc_id", "doc_type", "table_id", "results"}
        }
        result["results"] = [record] if record else []
        return result

    if isinstance(extract_result, list):
        base["results"] = extract_result
        return base

    return base


def get_source_paragraph(record: dict):
    for key in ["来源段落", "source_paragraph", "paragraph_index", "paragraph"]:
        if key in record and record[key] not in [None, ""]:
            try:
                return int(record[key])
            except Exception:
                return None
    return None


def get_source_text_from_paragraphs(paragraphs, paragraph_index):
    if paragraph_index is None:
        return None

    if not isinstance(paragraphs, list) or not paragraphs:
        return None

    # 优先按 0-based 取
    if 0 <= paragraph_index < len(paragraphs):
        value = paragraphs[paragraph_index]
        return str(value) if value is not None else None

    # 再兼容 1-based
    one_based_idx = paragraph_index - 1
    if 0 <= one_based_idx < len(paragraphs):
        value = paragraphs[one_based_idx]
        return str(value) if value is not None else None

    return None


def build_main_display_record(results: list):
    """
    给 document_fields 取一个“主结果”做兼容展示。
    默认取第一条 dict 结果。
    """
    if not isinstance(results, list):
        return {}

    for item in results:
        if isinstance(item, dict):
            return item

    return {}


def save_document_field(task: Task, parse_data: dict, extract_result: dict, db: Session):
    """
    保存一条主结果到 document_fields，兼容旧接口。
    """
    paragraphs = ensure_list(parse_data.get("paragraphs"))
    tables = ensure_list(parse_data.get("tables"))
    results = extract_result.get("results", [])
    main_record = build_main_display_record(results)

    source_paragraph = get_source_paragraph(main_record)
    source_text = (
        main_record.get("source_text")
        or get_source_text_from_paragraphs(paragraphs, source_paragraph)
    )

    existing = db.query(DocumentField).filter(DocumentField.task_id == task.id).first()
    if existing is None:
        existing = DocumentField(task_id=task.id)
        db.add(existing)

    existing.doc_id = str(parse_data.get("doc_id")) if parse_data.get("doc_id") is not None else None
    existing.doc_type = str(task.file_type) if task.file_type is not None else None
    existing.raw_text = str(parse_data.get("raw_text")) if parse_data.get("raw_text") is not None else None
    existing.paragraphs = json.dumps(paragraphs, ensure_ascii=False)
    existing.tables = json.dumps(tables, ensure_ascii=False)

    existing.category = (
        main_record.get("分类")
        or main_record.get("category")
    )
    existing.indicator = (
        main_record.get("指标")
        or main_record.get("indicator")
    )
    existing.value = (
        main_record.get("数值")
        or main_record.get("value")
    )
    existing.unit = (
        main_record.get("单位")
        or main_record.get("unit")
    )
    existing.time = (
        main_record.get("时间")
        or main_record.get("time")
    )
    existing.yoy = (
        main_record.get("同比")
        or main_record.get("yoy")
    )

    existing.source_document = task.file_name
    existing.source_paragraph = source_paragraph
    existing.source_text = source_text
    existing.source_span = None


def save_extracted_entities(task: Task, parse_data: dict, extract_result: dict, db: Session):
    """
    把抽取结果拆成通用字段，存到 extracted_entities。
    """
    paragraphs = ensure_list(parse_data.get("paragraphs"))
    doc_id = parse_data.get("doc_id")
    results = extract_result.get("results", [])

    db.query(ExtractedEntity).filter(ExtractedEntity.task_id == task.id).delete()

    for i, record in enumerate(results, start=1):
        if not isinstance(record, dict):
            continue

        record_id = str(record.get("record_id") or f"record_{i}")
        source_paragraph = get_source_paragraph(record)
        source_text = (
            record.get("source_text")
            or get_source_text_from_paragraphs(paragraphs, source_paragraph)
        )
        confidence = record.get("confidence")
        extractor_type = record.get("extractor_type") or "rule"

        for field_name, field_value in record.items():
            if field_name in {
                "record_id",
                "来源段落",
                "source_paragraph",
                "paragraph_index",
                "paragraph",
                "source_text",
                "confidence",
                "extractor_type"
            }:
                continue

            entity = ExtractedEntity(
                task_id=task.id,
                doc_id=str(doc_id) if doc_id is not None else None,
                source_document=task.file_name,
                record_id=record_id,
                field_name=str(field_name),
                field_value=str(field_value) if field_value is not None else None,
                normalized_value=str(field_value) if field_value is not None else None,
                source_paragraph=source_paragraph,
                source_text=str(source_text) if source_text is not None else None,
                source_span=None,
                confidence=float(confidence) if confidence not in [None, ""] else None,
                extractor_type=str(extractor_type) if extractor_type is not None else None
            )
            db.add(entity)


def run_extract(task_id: int, db: Session):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.result:
        raise HTTPException(status_code=400, detail="请先完成解析，再进行字段抽取")

    parse_data = safe_json_loads(task.result)
    if not isinstance(parse_data, dict) or not parse_data:
        raise HTTPException(status_code=500, detail="解析结果读取失败: task.result 不是有效 JSON")

    try:
        module = load_extract_module()
        word_config = load_word_config()

        raw_extract_result = module.extract(parse_data, word_config=word_config)
        extract_result = normalize_extract_result(raw_extract_result, parse_data, task)

        # 保存 tasks 表中的原始抽取输出
        task.extract_result = json.dumps(extract_result, ensure_ascii=False)

        # 同时把抽取结果合并回 task.result
        merged_result = dict(parse_data)
        merged_result["extract_result"] = extract_result
        task.result = json.dumps(merged_result, ensure_ascii=False)

        # 状态更新
        task.status = "extracted"
        task.parse_status = task.parse_status or "success"
        task.extract_status = "success"
        task.error_message = None

        # 保存主结果到 document_fields
        save_document_field(task, parse_data, extract_result, db)

        # 保存拆分结果到 extracted_entities
        save_extracted_entities(task, parse_data, extract_result, db)

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
        task.extract_status = "failed"
        task.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"字段抽取失败: {str(e)}")


@router.post("/extract/{task_id}")
def extract_task(task_id: int, db: Session = Depends(get_db)):
    return run_extract(task_id, db)