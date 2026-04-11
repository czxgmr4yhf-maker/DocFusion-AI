from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_tasks_columns()
    ensure_document_fields_columns()


def ensure_tasks_columns():
    inspector = inspect(engine)

    if "tasks" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("tasks")}

    required_columns = {
        "result": "ALTER TABLE tasks ADD COLUMN result TEXT",
        "extract_result": "ALTER TABLE tasks ADD COLUMN extract_result TEXT",
        "match_result": "ALTER TABLE tasks ADD COLUMN match_result TEXT",
        "error_message": "ALTER TABLE tasks ADD COLUMN error_message TEXT",
    }

    with engine.begin() as connection:
        for column_name, ddl in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))


def ensure_document_fields_columns():
    inspector = inspect(engine)

    if "document_fields" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("document_fields")}

    required_columns = {
        "category": "ALTER TABLE document_fields ADD COLUMN category VARCHAR",
        "indicator": "ALTER TABLE document_fields ADD COLUMN indicator VARCHAR",
        "value": "ALTER TABLE document_fields ADD COLUMN value VARCHAR",

        "project_name_source_file": "ALTER TABLE document_fields ADD COLUMN project_name_source_file VARCHAR",
        "project_name_source_paragraph": "ALTER TABLE document_fields ADD COLUMN project_name_source_paragraph INTEGER",
        "project_name_source_text": "ALTER TABLE document_fields ADD COLUMN project_name_source_text TEXT",

        "project_leader_source_file": "ALTER TABLE document_fields ADD COLUMN project_leader_source_file VARCHAR",
        "project_leader_source_paragraph": "ALTER TABLE document_fields ADD COLUMN project_leader_source_paragraph INTEGER",
        "project_leader_source_text": "ALTER TABLE document_fields ADD COLUMN project_leader_source_text TEXT",

        "organization_name_source_file": "ALTER TABLE document_fields ADD COLUMN organization_name_source_file VARCHAR",
        "organization_name_source_paragraph": "ALTER TABLE document_fields ADD COLUMN organization_name_source_paragraph INTEGER",
        "organization_name_source_text": "ALTER TABLE document_fields ADD COLUMN organization_name_source_text TEXT",

        "phone_source_file": "ALTER TABLE document_fields ADD COLUMN phone_source_file VARCHAR",
        "phone_source_paragraph": "ALTER TABLE document_fields ADD COLUMN phone_source_paragraph INTEGER",
        "phone_source_text": "ALTER TABLE document_fields ADD COLUMN phone_source_text TEXT",
    }

    with engine.begin() as connection:
        for column_name, ddl in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))