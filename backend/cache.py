"""
Cache layer — in-memory dict cache with TTL, optional Redis backend.

Usage:
    from backend.cache import cache_get, cache_set, cache_delete, get_cache_stats

    cache_set("my_key", some_value, ttl_seconds=60)
    val = cache_get("my_key")  # returns None if missing/expired
    cache_delete("my_key")
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)

# ── In-memory storage ────────────────────────────────────────────────────
_mem_cache: dict[str, tuple[float, Any]] = {}  # key -> (expiry_ts, value)

# ── Counters ─────────────────────────────────────────────────────────────
_hit_count: int = 0
_miss_count: int = 0

# ── Optional Redis ───────────────────────────────────────────────────────
_redis_client: Optional[Any] = None
_redis_available: Optional[bool] = None  # tri-state: None=unchecked, True/False=Cached


def _init_redis() -> Any:
    """Lazily initialise and return a Redis client, or None."""
    global _redis_client, _redis_available

    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client

    try:
        settings = get_settings()
        redis_url = settings.redis_url
    except Exception:
        redis_url = None

    if not redis_url:
        _redis_available = False
        logger.debug("No redis_url configured; using in-memory cache.")
        return None

    try:
        import redis as _redis
        _redis_client = _redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis cache backend connected: %s", redis_url)
    except ImportError:
        _redis_available = False
        logger.debug("redis-py not installed; falling back to in-memory cache.")
    except Exception as exc:
        _redis_available = False
        logger.warning("Redis connection failed (%s); falling back to in-memory.", exc)
        _redis_client = None

    return _redis_client


# ── Public API ───────────────────────────────────────────────────────────

def cache_get(key: str) -> Optional[Any]:
    """Retrieve a value from cache.  Returns None on miss or expiry."""
    global _hit_count, _miss_count

    r = _init_redis()
    if r is not None:
        try:
            val = r.get(key)
            if val is not None:
                _hit_count += 1
                # Attempt to deserialise JSON
                import json
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return val
            _miss_count += 1
            return None
        except Exception:
            pass  # fall through to in-memory

    # In-memory path
    entry = _mem_cache.get(key)
    if entry is None:
        _miss_count += 1
        return None

    expiry, value = entry
    if time.time() > expiry:
        del _mem_cache[key]
        _miss_count += 1
        return None

    _hit_count += 1
    return value


def cache_set(key: str, value: Any, ttl_seconds: float = 300) -> None:
    """Store a value with a time-to-live (default 5 minutes)."""
    r = _init_redis()
    if r is not None:
        try:
            import json as _json
            payload = _json.dumps(value, default=str)
            r.setex(key, int(ttl_seconds), payload)
            return
        except Exception:
            pass  # fall through to in-memory

    _mem_cache[key] = (time.time() + ttl_seconds, value)


def cache_delete(key: str) -> None:
    """Remove a key from the cache."""
    r = _init_redis()
    if r is not None:
        try:
            r.delete(key)
        except Exception:
            pass

    _mem_cache.pop(key, None)


def get_cache_stats() -> dict[str, Any]:
    """Return cache hit/miss counters and approximate size."""
    r = _init_redis()
    backend = "redis" if r is not None else "memory"

    # Clean expired in-memory entries for accurate count
    _clean_mem_cache()

    stats: dict[str, Any] = {
        "backend": backend,
        "hits": _hit_count,
        "misses": _miss_count,
        "total_requests": _hit_count + _miss_count,
        "mem_entries": len(_mem_cache),
    }
    if _hit_count + _miss_count > 0:
        stats["hit_rate"] = round(_hit_count / (_hit_count + _miss_count) * 100, 2)
    else:
        stats["hit_rate"] = 0.0
    return stats


def reset_cache_stats() -> None:
    """Reset hit/miss counters (useful for testing)."""
    global _hit_count, _miss_count
    _hit_count = 0
    _miss_count = 0


def clear_cache() -> None:
    """Flush the in-memory cache.  Does not touch Redis."""
    _mem_cache.clear()


# ── Internal ─────────────────────────────────────────────────────────────

def _clean_mem_cache() -> None:
    """Remove expired entries from the in-memory dict."""
    now = time.time()
    expired = [k for k, (exp, _) in _mem_cache.items() if now > exp]
    for k in expired:
        del _mem_cache[k]
