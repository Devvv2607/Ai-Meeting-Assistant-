from celery import Celery, Task
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    "ai_meeting",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
)


class CallbackTask(Task):
    """Task base class with callbacks"""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 5}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


celery_app.Task = CallbackTask
