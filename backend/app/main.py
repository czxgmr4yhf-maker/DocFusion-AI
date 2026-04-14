from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, upload, tasks, parse, extract, fields,match,trace
from app.core.logger import logger
from app.db.database import init_db
from app.db import models

app = FastAPI(title="A23 Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(trace.router, tags=["trace"])

init_db()

app.include_router(health.router)
app.include_router(upload.router)
app.include_router(tasks.router)
app.include_router(parse.router)
app.include_router(extract.router)
app.include_router(fields.router)
app.include_router(match.router)

@app.get("/")
def root():
    logger.info("访问根接口 /")
    return {"msg": "backend is running"}