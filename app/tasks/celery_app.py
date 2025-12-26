"""Celery application configuration"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "hospital_processor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
    or None,  # Empty string or None = disabled (we use job_repository)
    include=["app.tasks.tasks"],
)

celery_app.conf.update(
    # ======================
    # GENERAL TASK SETTINGS
    # ======================
    task_track_started=settings.celery_task_track_started,
    task_time_limit=settings.celery_task_time_limit,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # ======================
    # BROKER CONNECTION (STARTUP & RUNTIME)
    # ======================
    broker_connection_retry=settings.celery_broker_connection_retry,
    broker_connection_retry_on_startup=settings.celery_broker_connection_retry_on_startup,
    broker_connection_max_retries=settings.celery_broker_connection_max_retries,
    broker_connection_timeout=settings.celery_broker_connection_timeout,
    broker_pool_limit=settings.celery_broker_pool_limit,
    # ======================
    # TASK PUBLISHING (FAIL FAST)
    # ======================
    # Disable automatic retry on publish - fail immediately if Redis is down
    task_publish_retry=settings.celery_task_publish_retry,
    task_publish_retry_policy={
        "max_retries": settings.celery_task_publish_max_retries,
        "interval_start": 0,
        "interval_step": 0.1,
        "interval_max": 0.2,
    },
    # ======================
    # BROKER TRANSPORT OPTIONS
    # ======================
    broker_transport_options={
        "socket_connect_timeout": settings.celery_redis_socket_connect_timeout,
        "socket_timeout": settings.celery_redis_socket_timeout,
        "socket_keepalive": False,
        "retry_on_timeout": settings.celery_redis_retry_on_timeout,
        "max_connections": settings.celery_broker_pool_limit,
        "health_check_interval": 30,
        "visibility_timeout": 43200,  # 12 hours
    },
    # ======================
    # RESULT BACKEND OPTIONS (FAIL FAST)
    # ======================
    # Note: result_backend can be None (disabled) since we use job_repository
    result_backend_transport_options={
        "max_retries": settings.celery_result_backend_max_retries,
        "socket_connect_timeout": settings.celery_redis_socket_connect_timeout,
        "socket_timeout": settings.celery_redis_socket_timeout,
        "retry_on_timeout": settings.celery_redis_retry_on_timeout,
        "visibility_timeout": 43200,
    },
    # ======================
    # REDIS BACKEND SETTINGS (FAIL FAST)
    # ======================
    redis_backend_use_ssl=False,
    redis_max_connections=settings.celery_broker_pool_limit,
    redis_socket_connect_timeout=settings.celery_redis_socket_connect_timeout,
    redis_socket_timeout=settings.celery_redis_socket_timeout,
    redis_socket_keepalive=False,
    redis_retry_on_timeout=settings.celery_redis_retry_on_timeout,
    # CRITICAL: This limits result backend retries to prevent 20 retry cycles
    result_backend_max_retries=settings.celery_result_backend_max_retries,
)
