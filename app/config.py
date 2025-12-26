"""Application Configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation"""

    # Application
    app_name: str = "Hospital Bulk Processor API"
    app_version: str = "2.0.0"
    api_v1_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # External API
    hospital_api_base_url: str = "https://hospital-directory.onrender.com"
    hospital_api_timeout: float = 30.0

    # Processing Limits
    max_csv_rows: int = 20
    max_file_size_mb: int = 5

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str | None = (
        None  # Disabled by default (we use job_repository)
    )
    celery_task_track_started: bool = True
    celery_task_time_limit: int = 300  # 5 minutes

    # Broker Connection (Startup & Runtime)
    celery_broker_connection_retry: bool = True
    celery_broker_connection_retry_on_startup: bool = True
    celery_broker_connection_max_retries: int = 3
    celery_broker_connection_timeout: int = 2  # seconds
    celery_broker_pool_limit: int = 10

    # Task Publishing (Fail Fast Configuration)
    celery_task_publish_retry: bool = False  # Fail immediately if Redis down
    celery_task_publish_max_retries: int = 0  # No retries on publish
    celery_task_publish_timeout: int = 2  # 2 second timeout for publishing

    # Redis Socket Settings (Fail Fast)
    celery_redis_socket_connect_timeout: int = 1  # 1 second connection timeout
    celery_redis_socket_timeout: int = 2  # 2 second operation timeout
    celery_redis_retry_on_timeout: bool = False  # Don't retry on timeout

    # Result Backend Retry (Fail Fast)
    celery_result_backend_max_retries: int = 1  # Minimal retries for result backend

    # Rate Limiting (requests per second per API)
    rate_limit_requests: int = 10
    rate_limit_period: float = 1.0

    # Retry Configuration
    retry_max_attempts: int = 3
    retry_min_wait: int = 2
    retry_max_wait: int = 10

    # Circuit Breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60

    # Idempotency (request deduplication only, not business logic)
    idempotency_cache_ttl: int = 300  # 5 minutes - for network retries/double-clicks

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
