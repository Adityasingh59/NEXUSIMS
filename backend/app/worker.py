"""NEXUS IMS — Celery worker configuration."""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "nexus_ims",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_max_retries=3,
    task_routes={
        "app.tasks.*": {"queue": "default"},
    },
)

# Celery Beat schedule (add tasks here)
celery_app.conf.beat_schedule = {}
