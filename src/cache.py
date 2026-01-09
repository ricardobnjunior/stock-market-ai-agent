"""
Simple in-memory cache with TTL support.
Reduces redundant API calls to yfinance.
"""

import time
from typing import Any, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class TTLCache:
    """Time-based expiring cache."""

    def __init__(self, default_ttl: int = 60):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 60)
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                logger.debug(f"Cache hit: {key}")
                return value
            else:
                del self._cache[key]
                logger.debug(f"Cache expired: {key}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self._default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def cleanup(self) -> int:
        """Remove expired entries. Returns count of removed items."""
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
        for key in expired:
            del self._cache[key]
        if expired:
            logger.debug(f"Cache cleanup: removed {len(expired)} expired entries")
        return len(expired)

    @property
    def size(self) -> int:
        """Current number of cached items."""
        return len(self._cache)


# Global cache instance
price_cache = TTLCache(default_ttl=30)  # 30 seconds for price data
historical_cache = TTLCache(default_ttl=300)  # 5 minutes for historical data


def cached(cache: TTLCache, key_func=None, ttl: Optional[int] = None):
    """
    Decorator to cache function results.

    Args:
        cache: TTLCache instance to use
        key_func: Function to generate cache key from args/kwargs
        ttl: Optional TTL override
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{args}:{kwargs}"

            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)

            # Only cache successful results
            if isinstance(result, dict) and "error" not in result:
                cache.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator
