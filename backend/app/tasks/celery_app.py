"""Celery configuration."""
import os

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.core.config.settings import get_settings


settings = get_settings()

# Get environment
rabbitmq_url = os.getenv(
    "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"
)
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create Celery app
app = Celery(
    "estadisticas_soccer",
    broker=rabbitmq_url,
    backend=redis_url,
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_max_retries=3,
    task_default_retry_delay=60,
    imports=(
        "app.tasks.sync_tasks",
        "app.tasks.prediction_tasks",
        "app.tasks.ml_tasks",
    ),
)

# Define queues
app.conf.task_queues = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("sync_data", Exchange("sync_data"), routing_key="sync_data"),
    Queue("predictions", Exchange("predictions"), routing_key="predictions"),
    Queue("ml_training", Exchange("ml_training"), routing_key="ml_training"),
)

# Configure task routes
app.conf.task_routes = {
    "app.tasks.sync_tasks.*": {"queue": "sync_data"},
    "app.tasks.prediction_tasks.*": {"queue": "predictions"},
    "app.tasks.ml_tasks.*": {"queue": "ml_training"},
}

# Periodic tasks (Liga MX focused)
app.conf.beat_schedule = {
    "liga-mx-daily-sync-pipeline": {
        "task": "app.tasks.sync_tasks.sync_liga_mx_pipeline",
        "schedule": crontab(
            hour=settings.DAILY_SYNC_HOUR_UTC,
            minute=settings.DAILY_SYNC_MINUTE_UTC,
        ),
    },
    "liga-mx-models-evaluation": {
        "task": "app.tasks.ml_tasks.evaluate_models",
        "schedule": crontab(hour=settings.DAILY_SYNC_HOUR_UTC, minute=30),
    },
    "liga-mx-daily-generate-predictions": {
        "task": "app.tasks.prediction_tasks.generate_liga_mx_predictions",
        "schedule": crontab(
            hour=settings.DAILY_PREDICTIONS_HOUR_UTC,
            minute=settings.DAILY_PREDICTIONS_MINUTE_UTC,
        ),
    },
    "liga-mx-daily-historical-backfill": {
        "task": "app.tasks.sync_tasks.sync_historical_10_tournaments",
        "schedule": crontab(hour=settings.DAILY_SYNC_HOUR_UTC, minute=45),
    },
    "liga-mx-daily-usage-report": {
        "task": "app.tasks.sync_tasks.report_api_football_usage",
        "schedule": crontab(hour=23, minute=55),
    },
    "sportmonks-daily-usage-report": {
        "task": "app.tasks.sync_tasks.report_sportmonks_usage",
        "schedule": crontab(hour=23, minute=50),
    },
}

# Auto-discover tasks
app.autodiscover_tasks(["app.tasks"])
