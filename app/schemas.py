import uuid
import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_spend_inr: float
    total_spend_usd: float
    top_merchants: list
    anomaly_count: int
    category_breakdown: dict
    narrative: Optional[str]
    risk_level: Optional[str]


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: str
    row_count_raw: int
    row_count_clean: int
    created_at: dt.datetime
    completed_at: Optional[dt.datetime]
    error_message: Optional[str]


class JobStatusOut(JobOut):
    summary: Optional[JobSummaryOut] = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    txn_id: Optional[str]
    date: Optional[str]
    merchant: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    status: Optional[str]
    category: Optional[str]
    account_id: Optional[str]
    notes: Optional[str]
    is_anomaly: bool
    anomaly_reason: Optional[str]
    llm_category: Optional[str]
    llm_failed: bool


class JobResultsOut(BaseModel):
    job_id: uuid.UUID
    status: str
    transactions: list[TransactionOut]
    anomalies: list[TransactionOut]
    category_breakdown: dict
    summary: Optional[JobSummaryOut]


class UploadResponse(BaseModel):
    job_id: uuid.UUID
    status: str
