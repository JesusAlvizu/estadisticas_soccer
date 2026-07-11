"""Celery configuration."""
import os
from celery import Celery
from kombu import Exchange, Queue

# Get environment
rabbitmq_url = os.getenv(
    "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"
)

# Create Celery app
app = Celery(
    "estadisticas_soccer",
    broker=rabbitmq_url,
    backend="redis://localhost:6379/0",
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

# Auto-discover tasks
app.autodiscover_tasks(["app.tasks"])
