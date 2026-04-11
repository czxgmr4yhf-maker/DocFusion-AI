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
    error_message = Column(Text, nullable=True)

    # parser 输出
    result = Column(Text, nullable=True)

    # extract 模块原样输出
    extract_result = Column(Text, nullable=True)

    # matcher 模块原样输出
    match_result = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class DocumentField(Base):
    """
    旧表先保留，避免其他地方引用时报错。
    现在主流程不再依赖这个表做最终返回。
    """
    __tablename__ = "document_fields"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    doc_id = Column(String, nullable=True)
    doc_type = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    paragraphs = Column(Text, nullable=True)
    tables = Column(Text, nullable=True)

    category = Column(String, nullable=True)
    indicator = Column(String, nullable=True)
    value = Column(String, nullable=True)

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