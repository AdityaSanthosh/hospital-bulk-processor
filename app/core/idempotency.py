"""Idempotency handling for safe retries"""
import hashlib
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class IdempotencyStore:
    """In-memory idempotency store with TTL"""
    
    def __init__(self, ttl: int = 86400):
        self.ttl = ttl
        self._store: Dict[str, tuple[Any, float]] = {}
        logger.info(f"Idempotency store initialized with TTL: {ttl}s")
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._store.items()
            if current_time - timestamp > self.ttl
        ]
        if expired_keys:
            for key in expired_keys:
                del self._store[key]
            logger.debug(f"Cleaned up {len(expired_keys)} expired idempotency keys")
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result for idempotency key"""
        self._cleanup_expired()
        
        if key in self._store:
            result, timestamp = self._store[key]
            if time.time() - timestamp <= self.ttl:
                logger.info(f"Idempotency cache HIT for key: {key[:16]}...")
                return result
            else:
                del self._store[key]
        
        logger.debug(f"Idempotency cache MISS for key: {key[:16]}...")
        return None
    
    def set(self, key: str, value: Any):
        """Set result for idempotency key"""
        self._store[key] = (value, time.time())
        logger.debug(f"Idempotency cache SET for key: {key[:16]}...")
    
    def delete(self, key: str):
        """Delete idempotency key"""
        if key in self._store:
            del self._store[key]
            logger.debug(f"Idempotency cache DELETE for key: {key[:16]}...")


# Global idempotency store
idempotency_store = IdempotencyStore()


def generate_idempotency_key(data: str) -> str:
    """Generate idempotency key from data"""
    return hashlib.sha256(data.encode()).hexdigest()
