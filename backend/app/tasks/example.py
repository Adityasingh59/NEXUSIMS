"""NEXUS IMS — Example Celery task for verification."""
from app.worker import celery_app


@celery_app.task(bind=True, max_retries=3)
def example_task(self, message: str) -> str:
    """Test task: echoes message. Verify workers process tasks."""
    return f"Processed: {message}"
