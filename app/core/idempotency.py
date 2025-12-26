"""Idempotency handling with Redis for safe retries"""

import json
import logging
from typing import Optional

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class RedisIdempotencyStore:
    """Redis-backed idempotency store with TTL"""

    def __init__(self, ttl: int = 300):
        """
        Initialize Redis idempotency store

        Args:
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.ttl = ttl
        self._redis_client: Optional[Redis] = None
        logger.info(f"Redis idempotency store initialized with TTL: {ttl}s")

    def _get_client(self) -> Redis:
        """Get or create Redis client"""
        if self._redis_client is None:
            try:
                self._redis_client = Redis.from_url(
                    settings.celery_broker_url,
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=2,
                    retry_on_timeout=False,
                )
                # Test connection
                self._redis_client.ping()
                logger.info("Redis connection established for idempotency store")
            except RedisConnectionError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._redis_client

    def _make_key(self, idempotency_key: str) -> str:
        """Create Redis key with namespace prefix"""
        return f"idempotency:{idempotency_key}"

    def get(self, key: str) -> Optional[dict]:
        """
        Get cached result for idempotency key

        Args:
            key: Idempotency key

        Returns:
            Cached response dict or None if not found/expired
        """
        try:
            client = self._get_client()
            redis_key = self._make_key(key)

            value = client.get(redis_key)
            if value:
                logger.info(f"Idempotency cache HIT for key: {key[:16]}...")
                # value is str because decode_responses=True
                return json.loads(str(value))

            logger.debug(f"Idempotency cache MISS for key: {key[:16]}...")
            return None

        except RedisError as e:
            logger.error(f"Redis error on GET: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode cached value: {e}")
            return None

    def set(self, key: str, value: dict) -> bool:
        """
        Set result for idempotency key with TTL

        Args:
            key: Idempotency key
            value: Response dict to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            redis_key = self._make_key(key)

            # Serialize to JSON
            serialized = json.dumps(value)

            # Set with TTL (EX = seconds)
            client.setex(redis_key, self.ttl, serialized)

            logger.debug(
                f"Idempotency cache SET for key: {key[:16]}... (TTL: {self.ttl}s)"
            )
            return True

        except RedisError as e:
            logger.error(f"Redis error on SET: {e}")
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize value: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete idempotency key

        Args:
            key: Idempotency key

        Returns:
            True if deleted, False otherwise
        """
        try:
            client = self._get_client()
            redis_key = self._make_key(key)

            deleted = client.delete(redis_key)
            if deleted:
                logger.debug(f"Idempotency cache DELETE for key: {key[:16]}...")
                return True
            return False

        except RedisError as e:
            logger.error(f"Redis error on DELETE: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if idempotency key exists

        Args:
            key: Idempotency key

        Returns:
            True if exists, False otherwise
        """
        try:
            client = self._get_client()
            redis_key = self._make_key(key)
            return bool(client.exists(redis_key))
        except RedisError as e:
            logger.error(f"Redis error on EXISTS: {e}")
            return False

    def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for idempotency key

        Args:
            key: Idempotency key

        Returns:
            TTL in seconds, -1 if key exists without TTL, -2 if key doesn't exist
        """
        try:
            client = self._get_client()
            redis_key = self._make_key(key)
            ttl_value = client.ttl(redis_key)
            # TTL returns int directly with decode_responses=True
            if isinstance(ttl_value, int):
                return ttl_value
            return -2
        except RedisError as e:
            logger.error(f"Redis error on TTL: {e}")
            return -2


# Global idempotency store with 5-minute TTL
idempotency_store = RedisIdempotencyStore(ttl=settings.idempotency_cache_ttl)
