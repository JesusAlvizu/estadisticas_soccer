"""Celery tasks package."""

from app.tasks.celery_app import app

# Ensure modules are imported when package loads.
from app.tasks import ml_tasks, prediction_tasks, sync_tasks

__all__ = ["app", "ml_tasks", "prediction_tasks", "sync_tasks"]
