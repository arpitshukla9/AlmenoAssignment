"""
RQ worker process. Run with: python worker.py
(or `rq worker transactions --url redis://redis:6379/0`)
"""
import logging

from rq import Worker

from app.queue import redis_conn, job_queue
from app.config import settings

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    worker = Worker([job_queue], connection=redis_conn)
    worker.work(with_scheduler=False)
