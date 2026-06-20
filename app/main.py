import logging

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import jobs

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI-Powered Transaction Processing Pipeline",
    description="Uploads dirty transaction CSVs, processes them async via RQ, "
                 "classifies and flags anomalies with an LLM, and serves a structured report.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


app.include_router(jobs.router)
