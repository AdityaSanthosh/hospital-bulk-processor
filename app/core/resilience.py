"""Resilience: Retry, Circuit Breaker, Rate Limiting"""

import logging
from functools import wraps
from typing import Callable, Optional

from aiolimiter import AsyncLimiter
from pybreaker import (
    STATE_CLOSED,
    CircuitBreaker,
    CircuitBreakerError,
    CircuitRedisStorage,
)
from redis import Redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Async rate limiter for API calls"""

    def __init__(
        self, max_rate: Optional[int] = None, time_period: Optional[float] = None
    ):
        self.max_rate = max_rate or settings.rate_limit_requests
        self.time_period = time_period or settings.rate_limit_period
        self.limiter = AsyncLimiter(self.max_rate, self.time_period)
        logger.info(
            f"Rate limiter initialized: {self.max_rate} requests per {self.time_period}s"
        )

    async def acquire(self):
        """Acquire rate limit token"""
        await self.limiter.acquire()

    def __call__(self, func: Callable) -> Callable:
        """Decorator for rate limiting"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            await self.acquire()
            return await func(*args, **kwargs)

        return wrapper


def _create_redis_circuit_breaker_storage() -> CircuitRedisStorage:
    """
    Create Redis-backed circuit breaker storage (shared across all workers)

    Fails hard if Redis is unavailable (consistent with fail-fast philosophy).
    If Redis is down, Celery workers can't receive tasks anyway.

    Returns:
        CircuitRedisStorage with shared state

    Raises:
        RedisError: If Redis connection fails
    """
    try:
        # Create Redis client (reuses Celery broker URL)
        redis_client = Redis.from_url(
            settings.celery_broker_url,
            decode_responses=False,  # pybreaker expects bytes, not strings
            socket_connect_timeout=1,
            socket_timeout=2,
            retry_on_timeout=False,
        )

        # Test connection (fail fast if Redis is down)
        redis_client.ping()
        logger.info("Redis connection established for circuit breaker")

        # Create Redis-backed storage
        storage = CircuitRedisStorage(STATE_CLOSED, redis_client)
        logger.info(
            "Circuit breaker using Redis-backed storage (shared across all workers)"
        )

        return storage

    except RedisError as e:
        logger.error(
            f"FATAL: Cannot connect to Redis for circuit breaker: {e}. "
            f"Redis is required (Celery won't work without it either)."
        )
        raise
    except Exception as e:
        logger.error(f"FATAL: Unexpected error creating circuit breaker storage: {e}")
        raise


class APICircuitBreaker:
    """
    Circuit breaker for external API calls with Redis-backed state

    Uses Redis to share circuit breaker state across ALL Celery workers.
    Fails hard if Redis is unavailable (consistent with fail-fast philosophy).
    """

    def __init__(self, name: str):
        self.name = name

        # Create Redis-backed storage (fails hard if Redis unavailable)
        storage = _create_redis_circuit_breaker_storage()

        self.breaker = CircuitBreaker(
            fail_max=settings.circuit_breaker_failure_threshold,
            reset_timeout=settings.circuit_breaker_recovery_timeout,
            name=name,
            state_storage=storage,
        )
        self.breaker.add_listener(self._on_state_change)  # type: ignore[arg-type]

        logger.info(
            f"Circuit breaker '{name}' initialized "
            f"(fail_max={settings.circuit_breaker_failure_threshold}, "
            f"reset_timeout={settings.circuit_breaker_recovery_timeout}s)"
        )

    def _on_state_change(self, breaker, old_state, new_state):
        """Log circuit breaker state changes"""
        logger.warning(
            f"Circuit breaker '{self.name}' state changed: {old_state} -> {new_state}"
        )

    def __call__(self, func: Callable) -> Callable:
        """Decorator for circuit breaker"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await self.breaker.call_async(func, *args, **kwargs)  # type: ignore[misc]
            except CircuitBreakerError:
                logger.error(
                    f"Circuit breaker '{self.name}' is OPEN for {func.__name__}"
                )
                raise

        return wrapper


# Global instances
rate_limiter = RateLimiter()
hospital_api_circuit_breaker = APICircuitBreaker("hospital_api")
