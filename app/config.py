"""
Centralised configuration. All values are overridable via environment
variables / .env so the same image works in dev, CI, and (eventually) prod.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres
    database_url: str = "postgresql://postgres:postgres@db:5432/transactions"

    # Redis / RQ
    redis_url: str = "redis://redis:6379/0"
    rq_queue_name: str = "transactions"

    # LLM
    gemini_api_key: str = ""
    llm_provider: str = "gemini"  # "gemini" | "mock"
    llm_model: str = "gemini-1.5-flash"
    llm_batch_size: int = 20
    llm_max_retries: int = 3
    llm_backoff_base_seconds: float = 2.0

    # Anomaly detection
    outlier_median_multiplier: float = 3.0
    domestic_only_merchants: list[str] = ["Swiggy", "Ola", "IRCTC"]

    # Uploads
    max_upload_mb: int = 10


settings = Settings()
