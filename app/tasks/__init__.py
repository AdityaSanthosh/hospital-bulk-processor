"""Celery infrastructure"""

from .celery_app import celery_app
from .tasks import process_bulk_hospitals_task

__all__ = ["celery_app", "process_bulk_hospitals_task"]
