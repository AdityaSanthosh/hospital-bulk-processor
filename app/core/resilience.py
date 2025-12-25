"""Resilience: Retry, Circuit Breaker, Rate Limiting"""
import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar

from aiolimiter import AsyncLimiter
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RateLimiter:
    """Async rate limiter for API calls"""
    
    def __init__(self, max_rate: int = None, time_period: float = None):
        self.max_rate = max_rate or settings.rate_limit_requests
        self.time_period = time_period or settings.rate_limit_period
        self.limiter = AsyncLimiter(self.max_rate, self.time_period)
        logger.info(f"Rate limiter initialized: {self.max_rate} requests per {self.time_period}s")
    
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


class APICircuitBreaker:
    """Circuit breaker for external API calls"""
    
    def __init__(self, name: str):
        self.name = name
        self.breaker = CircuitBreaker(
            fail_max=settings.circuit_breaker_failure_threshold,
            reset_timeout=settings.circuit_breaker_recovery_timeout,
            name=name
        )
        self.breaker.add_listener(self._on_state_change)
        logger.info(f"Circuit breaker '{name}' initialized")
    
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
                return await self.breaker.call_async(func, *args, **kwargs)
            except CircuitBreakerError:
                logger.error(f"Circuit breaker '{self.name}' is OPEN for {func.__name__}")
                raise
        return wrapper


class RetryPolicy:
    """Retry policy with exponential backoff"""
    
    @staticmethod
    def get_retryer(
        max_attempts: int = None,
        min_wait: int = None,
        max_wait: int = None,
        retry_exceptions: tuple = (Exception,)
    ):
        """Get configured retry async context manager"""
        return AsyncRetrying(
            stop=stop_after_attempt(max_attempts or settings.retry_max_attempts),
            wait=wait_exponential(
                min=min_wait or settings.retry_min_wait,
                max=max_wait or settings.retry_max_wait
            ),
            retry=retry_if_exception_type(retry_exceptions),
            reraise=True
        )
    
    @staticmethod
    def with_retry(
        max_attempts: int = None,
        retry_exceptions: tuple = (Exception,)
    ):
        """Decorator for retry logic"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                retryer = RetryPolicy.get_retryer(
                    max_attempts=max_attempts,
                    retry_exceptions=retry_exceptions
                )
                attempt_num = 0
                async for attempt in retryer:
                    with attempt:
                        attempt_num += 1
                        if attempt_num > 1:
                            logger.info(
                                f"Retry attempt {attempt_num} for {func.__name__}"
                            )
                        return await func(*args, **kwargs)
            return wrapper
        return decorator


# Global instances
rate_limiter = RateLimiter()
hospital_api_circuit_breaker = APICircuitBreaker("hospital_api")
