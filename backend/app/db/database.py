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
    ensure_document_fields_columns()


def ensure_document_fields_columns():
    inspector = inspect(engine)
    if "document_fields" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("document_fields")}
    required_columns = {
        "category": "ALTER TABLE document_fields ADD COLUMN category VARCHAR",
        "indicator": "ALTER TABLE document_fields ADD COLUMN indicator VARCHAR",
        "value": "ALTER TABLE document_fields ADD COLUMN value VARCHAR",
    }

    with engine.begin() as connection:
        for column_name, ddl in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))
