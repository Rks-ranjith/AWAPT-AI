from celery import Celery
from awap.core.config import settings

celery_app = Celery(
    "awap_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 2,  # Max scan duration config (2 hours)
)

# Autodiscover tasks from engine modules
celery_app.autodiscover_tasks(["awap.engines.worker"])
