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
    include=[
        "app.tasks", 
        "app.tasks.report_tasks",
        "app.tasks.workflow_tasks",
        "app.tasks.webhook_tasks",
        "app.tasks.replenishment_tasks",
        "app.tasks.currency_tasks"
    ],
)

# Celery Beat schedule
celery_app.conf.beat_schedule = {
    "refresh-dashboard-cache-60s": {
        "task": "app.tasks.report_tasks.refresh_dashboard_cache",
        "schedule": 60.0,  # every 60 seconds
    },
    "auto-replenishment-daily": {
        "task": "app.tasks.replenishment_tasks.generate_replenishment_pos",
        "schedule": 86400.0,  # every 24 hours (for test/demo, could use crontab(minute=0, hour=0))
    },
    "fetch-exchange-rates-daily": {
        "task": "app.tasks.currency_tasks.fetch_exchange_rates",
        "schedule": 43200.0,  # every 12 hours
    },
}
