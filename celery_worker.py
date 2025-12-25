"""Celery worker entrypoint"""
import logging

from app.infrastructure.celery.celery_app import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import tasks to register them
from app.infrastructure.celery import tasks

if __name__ == "__main__":
    celery_app.worker_main()
