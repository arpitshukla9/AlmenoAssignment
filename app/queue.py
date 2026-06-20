import redis
from rq import Queue

from app.config import settings

redis_conn = redis.from_url(settings.redis_url)
job_queue = Queue(settings.rq_queue_name, connection=redis_conn)
