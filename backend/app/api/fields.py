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
        "created_at": field_data.created_at,
        "updated_at": field_data.updated_at,
    }