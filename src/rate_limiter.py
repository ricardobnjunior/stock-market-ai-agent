"""
Rate limiting for API protection.
Prevents excessive requests to external APIs.
"""

import time
from collections import deque
from functools import wraps
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.
    Limits requests to a maximum number within a time window.
    """

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: deque = deque()

    def _cleanup_old_requests(self):
        """Remove requests outside the current window."""
        cutoff = time.time() - self.window_seconds
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    def is_allowed(self) -> bool:
        """Check if a request is allowed."""
        self._cleanup_old_requests()
        return len(self._requests) < self.max_requests

    def record_request(self):
        """Record a new request."""
        self._requests.append(time.time())

    def wait_time(self) -> float:
        """Get seconds to wait before next request is allowed."""
        self._cleanup_old_requests()
        if len(self._requests) < self.max_requests:
            return 0.0

        oldest = self._requests[0]
        wait = (oldest + self.window_seconds) - time.time()
        return max(0.0, wait)

    def try_acquire(self) -> bool:
        """Try to acquire a request slot. Returns True if allowed."""
        if self.is_allowed():
            self.record_request()
            return True
        return False

    @property
    def remaining(self) -> int:
        """Number of remaining requests in current window."""
        self._cleanup_old_requests()
        return max(0, self.max_requests - len(self._requests))


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, wait_time: float):
        self.wait_time = wait_time
        super().__init__(f"Rate limit exceeded. Try again in {wait_time:.1f} seconds.")


# Global rate limiters
yfinance_limiter = RateLimiter(max_requests=30, window_seconds=60)
llm_limiter = RateLimiter(max_requests=20, window_seconds=60)


def rate_limited(limiter: RateLimiter, block: bool = True, timeout: float = 30.0):
    """
    Decorator to apply rate limiting to a function.

    Args:
        limiter: RateLimiter instance to use
        block: If True, wait for rate limit. If False, raise exception.
        timeout: Maximum time to wait if blocking
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_wait = time.time()

            while not limiter.try_acquire():
                if not block:
                    raise RateLimitExceeded(limiter.wait_time())

                wait = limiter.wait_time()
                if time.time() - start_wait + wait > timeout:
                    raise RateLimitExceeded(wait)

                logger.warning(f"Rate limited. Waiting {wait:.1f}s...")
                time.sleep(min(wait, 1.0))  # Check every second

            return func(*args, **kwargs)
        return wrapper
    return decorator
