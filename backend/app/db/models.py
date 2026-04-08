from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from .database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    status = Column(String, default="uploaded")
    error_message = Column(String, nullable=True)
    result = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class DocumentField(Base):
    __tablename__ = "document_fields"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    # 第一版字段字典（P0）
    doc_id = Column(String, nullable=True)
    doc_type = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    paragraphs = Column(Text, nullable=True)   # 先用字符串保存，后面可转 JSON
    tables = Column(Text, nullable=True)       # 先用字符串保存，后面可转 JSON

    category = Column(String, nullable=True)
    indicator = Column(String, nullable=True)
    value = Column(String, nullable=True)

    # ===== 字段来源追溯信息 =====
    project_name_source_file = Column(String, nullable=True)
    project_name_source_paragraph = Column(Integer, nullable=True)
    project_name_source_text = Column(Text, nullable=True)

    project_leader_source_file = Column(String, nullable=True)
    project_leader_source_paragraph = Column(Integer, nullable=True)
    project_leader_source_text = Column(Text, nullable=True)

    organization_name_source_file = Column(String, nullable=True)
    organization_name_source_paragraph = Column(Integer, nullable=True)
    organization_name_source_text = Column(Text, nullable=True)

    phone_source_file = Column(String, nullable=True)
    phone_source_paragraph = Column(Integer, nullable=True)
    phone_source_text = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
