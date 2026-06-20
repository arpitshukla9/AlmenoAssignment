"""
The RQ task entrypoint. Enqueued by POST /jobs/upload, executed by the
worker process. Runs pipeline steps (a) through (d) in order, persists
results, and updates Job status throughout.

Step (e) "retry logic" is implemented inside llm_client.call_llm (retry +
backoff) and surfaces here as llm_failed flags rather than exceptions, so a
single bad batch never aborts the whole job.
"""
from __future__ import annotations

import io
import logging
import datetime as dt

import pandas as pd

from app.database import SessionLocal
from app.models import Job, Transaction, JobSummary, JobStatus
from app.pipeline.cleaning import clean_transactions
from app.pipeline.anomaly import detect_anomalies
from app.pipeline.classification import classify_uncategorised
from app.pipeline.narrative import generate_narrative_summary

logger = logging.getLogger(__name__)


def process_job(job_id: str, csv_bytes: bytes) -> None:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            logger.error("Job %s not found when worker picked it up", job_id)
            return

        job.status = JobStatus.processing
        db.commit()

        df = pd.read_csv(io.BytesIO(csv_bytes), dtype=str)

        # (a) Data Cleaning
        df, row_count_raw, row_count_clean = clean_transactions(df)

        # (b) Anomaly Detection
        df = detect_anomalies(df)

        # (c) LLM Classification (batched)
        df = classify_uncategorised(df)

        # (d) LLM Narrative Summary (single call)
        summary_data = generate_narrative_summary(df)

        # Persist transactions
        for row in df.itertuples():
            txn = Transaction(
                job_id=job.id,
                txn_id=row.txn_id,
                date=row.date,
                merchant=row.merchant,
                amount=row.amount,
                currency=row.currency,
                status=row.status,
                category=row.category,
                account_id=row.account_id,
                notes=row.notes,
                is_anomaly=bool(row.is_anomaly),
                anomaly_reason=row.anomaly_reason or None,
                llm_category=row.llm_category,
                llm_raw_response=row.llm_raw_response,
                llm_failed=bool(row.llm_failed),
            )
            db.add(txn)

        summary = JobSummary(
            job_id=job.id,
            total_spend_inr=summary_data["total_spend_inr"],
            total_spend_usd=summary_data["total_spend_usd"],
            top_merchants=summary_data["top_merchants"],
            anomaly_count=summary_data["anomaly_count"],
            category_breakdown=summary_data["category_breakdown"],
            narrative=summary_data["narrative"],
            risk_level=summary_data["risk_level"],
        )
        db.add(summary)

        job.row_count_raw = row_count_raw
        job.row_count_clean = row_count_clean
        job.status = JobStatus.completed
        job.completed_at = dt.datetime.utcnow()
        db.commit()

    except Exception as exc:  # noqa: BLE001 - last-resort job-level failure handling
        logger.exception("Job %s failed", job_id)
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.failed
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()
