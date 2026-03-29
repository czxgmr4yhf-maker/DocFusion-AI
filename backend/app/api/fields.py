from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DocumentField

router = APIRouter(prefix="/fields", tags=["fields"])


@router.get("/{task_id}")
def get_fields(task_id: int, db: Session = Depends(get_db)):
    field_data = db.query(DocumentField).filter(DocumentField.task_id == task_id).first()

    if not field_data:
        raise HTTPException(status_code=404, detail="未找到该任务的字段结果")

    return {
        "task_id": field_data.task_id,
        "doc_id": field_data.doc_id,
        "doc_type": field_data.doc_type,
        "raw_text": field_data.raw_text,
        "paragraphs": field_data.paragraphs,
        "tables": field_data.tables,

        "project_name": field_data.project_name,
        "project_leader": field_data.project_leader,
        "organization_name": field_data.organization_name,
        "phone": field_data.phone,

        # 字段来源信息
        "project_name_source_file": field_data.project_name_source_file,
        "project_name_source_paragraph": field_data.project_name_source_paragraph,
        "project_name_source_text": field_data.project_name_source_text,

        "project_leader_source_file": field_data.project_leader_source_file,
        "project_leader_source_paragraph": field_data.project_leader_source_paragraph,
        "project_leader_source_text": field_data.project_leader_source_text,

        "organization_name_source_file": field_data.organization_name_source_file,
        "organization_name_source_paragraph": field_data.organization_name_source_paragraph,
        "organization_name_source_text": field_data.organization_name_source_text,

        "phone_source_file": field_data.phone_source_file,
        "phone_source_paragraph": field_data.phone_source_paragraph,
        "phone_source_text": field_data.phone_source_text,

        "created_at": field_data.created_at,
        "updated_at": field_data.updated_at,
    }


@router.get("/{task_id}/source/{field_name}")
def get_field_source(task_id: int, field_name: str, db: Session = Depends(get_db)):
    field_data = db.query(DocumentField).filter(DocumentField.task_id == task_id).first()

    if not field_data:
        raise HTTPException(status_code=404, detail="未找到该任务的字段结果")

    allowed_fields = {
        "project_name": {
            "value": field_data.project_name,
            "source_file": field_data.project_name_source_file,
            "source_paragraph": field_data.project_name_source_paragraph,
            "source_text": field_data.project_name_source_text,
        },
        "project_leader": {
            "value": field_data.project_leader,
            "source_file": field_data.project_leader_source_file,
            "source_paragraph": field_data.project_leader_source_paragraph,
            "source_text": field_data.project_leader_source_text,
        },
        "organization_name": {
            "value": field_data.organization_name,
            "source_file": field_data.organization_name_source_file,
            "source_paragraph": field_data.organization_name_source_paragraph,
            "source_text": field_data.organization_name_source_text,
        },
        "phone": {
            "value": field_data.phone,
            "source_file": field_data.phone_source_file,
            "source_paragraph": field_data.phone_source_paragraph,
            "source_text": field_data.phone_source_text,
        }
    }

    if field_name not in allowed_fields:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的字段名：{field_name}，当前仅支持 {list(allowed_fields.keys())}"
        )

    result = allowed_fields[field_name]

    return {
        "task_id": task_id,
        "field_name": field_name,
        "value": result["value"],
        "source_file": result["source_file"],
        "source_paragraph": result["source_paragraph"],
        "source_text": result["source_text"],
    }