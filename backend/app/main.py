from fastapi import FastAPI
from app.api import health, upload, tasks, parse,extract
from app.db.database import engine, Base
from app.core.logger import logger

Base.metadata.create_all(bind=engine)

app = FastAPI(title="A23 Backend", version="0.1.0")

app.include_router(health.router)
app.include_router(upload.router)
app.include_router(tasks.router)
app.include_router(parse.router)
app.include_router(extract.router)


@app.get("/")
def root():
    logger.info("访问根接口 /")
    return {"msg": "backend is running"}