"""Celery worker entrypoint"""

import logging

from app.tasks.celery_app import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Import tasks to register them

if __name__ == "__main__":
    celery_app.worker_main()
