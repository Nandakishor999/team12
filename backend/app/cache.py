"""
cache.py — Production-grade caching and rate limiting for TechNovance HR Chatbot.

Features:
  - LRU cache for query responses (time-boxed)
  - Sliding window rate limiter (per-IP)
  - Thread-safe implementations
"""

import hashlib
import logging
import time
from collections import defaultdict, OrderedDict
from threading import Lock
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class TimeboxedCache:
    """
    Simple LRU cache with TTL (time-to-live) support.
    
    Thread-safe. Useful for caching AI responses with automatic expiration.
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.lock = Lock()

    def _hash_key(self, key: str) -> str:
        """Generate a short hash key for consistent storage."""
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[Any]:
        """Get value if key exists and hasn't expired."""
        with self.lock:
            if key not in self.cache:
                return None
            
            value, timestamp = self.cache[key]
            if time.time() - timestamp > self.ttl_seconds:
                del self.cache[key]
                return None
            
            # Move to end (LRU)
            self.cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """Store a value with current timestamp."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            
            self.cache[key] = (value, time.time())
            
            # Evict oldest if over capacity
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
                logger.debug("Cache eviction triggered (size: %d)", self.max_size)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self.lock:
            self.cache.clear()

    @property
    def size(self) -> int:
        """Return current cache size."""
        with self.lock:
            return len(self.cache)


class SlidingWindowRateLimiter:
    """
    Per-IP rate limiter using a sliding window approach.
    
    Tracks requests over two time windows:
      - Per-minute: allows burst handling
      - Per-hour: prevents sustained abuse
    
    Thread-safe.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour
        self.windows: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        """Check if client_id is within rate limits."""
        with self.lock:
            now = time.time()
            minute_ago = now - 60
            hour_ago = now - 3600
            
            # Clean old timestamps
            self.windows[client_id] = [
                ts for ts in self.windows[client_id]
                if ts > hour_ago
            ]
            
            # Check per-minute limit
            recent_minute = [ts for ts in self.windows[client_id] if ts > minute_ago]
            if len(recent_minute) >= self.rpm_limit:
                logger.warning("Rate limit (per-minute) exceeded for client: %s", client_id)
                return False
            
            # Check per-hour limit
            if len(self.windows[client_id]) >= self.rph_limit:
                logger.warning("Rate limit (per-hour) exceeded for client: %s", client_id)
                return False
            
            # Record request
            self.windows[client_id].append(now)
            return True

    def get_remaining_requests(self, client_id: str) -> dict[str, int]:
        """Return remaining request count for this client."""
        with self.lock:
            now = time.time()
            minute_ago = now - 60
            hour_ago = now - 3600
            
            recent_minute = len([
                ts for ts in self.windows.get(client_id, [])
                if ts > minute_ago
            ])
            recent_hour = len([
                ts for ts in self.windows.get(client_id, [])
                if ts > hour_ago
            ])
            
            return {
                "remaining_per_minute": max(0, self.rpm_limit - recent_minute),
                "remaining_per_hour": max(0, self.rph_limit - recent_hour),
            }


# Global instances
response_cache = TimeboxedCache(
    max_size=100,
    ttl_seconds=settings.CACHE_TTL_SECONDS,
)
rate_limiter = SlidingWindowRateLimiter(
    requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
    requests_per_hour=settings.RATE_LIMIT_REQUESTS_PER_HOUR,
)


def cache_key_for_query(message: str, history_len: int) -> str:
    """Generate a cache key for a query + history length."""
    key_parts = [message.strip().lower(), str(history_len)]
    combined = "|".join(key_parts)
    return hashlib.md5(combined.encode()).hexdigest()
