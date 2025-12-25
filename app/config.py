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
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_track_started: bool = True
    celery_task_time_limit: int = 300  # 5 minutes
    
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
    
    # Idempotency
    idempotency_cache_ttl: int = 86400  # 24 hours
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


settings = Settings()
