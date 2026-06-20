import uuid
import logging

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Job, Transaction, JobStatus
from app.schemas import UploadResponse, JobOut, JobStatusOut, JobResultsOut, TransactionOut
from app.queue import job_queue
from app.pipeline.orchestrator import process_job
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_mb}MB limit")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    job = Job(filename=file.filename, status=JobStatus.pending)
    db.add(job)
    db.commit()
    db.refresh(job)

    job_queue.enqueue(process_job, str(job.id), contents, job_timeout="10m")

    return UploadResponse(job_id=job.id, status=job.status.value)


@router.get("/{job_id}/status", response_model=JobStatusOut)
def get_job_status(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/results", response_model=JobResultsOut)
def get_job_results(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=409, detail=f"Job is '{job.status.value}', not yet completed")

    transactions = db.query(Transaction).filter(Transaction.job_id == job_id).all()
    anomalies = [t for t in transactions if t.is_anomaly]

    category_breakdown = job.summary.category_breakdown if job.summary else {}

    return JobResultsOut(
        job_id=job.id,
        status=job.status.value,
        transactions=[TransactionOut.model_validate(t) for t in transactions],
        anomalies=[TransactionOut.model_validate(t) for t in anomalies],
        category_breakdown=category_breakdown,
        summary=job.summary,
    )


@router.get("", response_model=list[JobOut])
def list_jobs(
    status: JobStatus | None = Query(default=None, description="Filter by job status"),
    db: Session = Depends(get_db),
):
    query = db.query(Job).order_by(desc(Job.created_at))
    if status is not None:
        query = query.filter(Job.status == status)
    return query.all()
