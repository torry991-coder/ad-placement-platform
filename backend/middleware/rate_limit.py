"""Rate limiter middleware with optional Redis backend for distributed deployments.

In-memory sliding-window rate limiter (single process).
When Redis is available, uses Redis for cross-process rate limiting (production).

Default: 10000 requests per 60 seconds per IP (tuned for 100K concurrency).
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter with optional Redis backend.

    Reads client IP from ``X-Forwarded-For`` or ``request.client.host``.
    Returns 429 with ``{"detail": "Too many requests", "retry_after": <seconds>}``
    and adds ``X-RateLimit-*`` headers on every response.

    When a Redis URL is configured via ``REDIS_URL`` env var, uses Redis sorted-set
    sliding window for distributed rate limiting across multiple Gunicorn workers.
    """

    def __init__(
        self,
        app,
        max_requests: int = 10000,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # IP → list of Unix timestamps (in-memory fallback)
        self._hits: dict[str, list[float]] = defaultdict(list)
        # Lazy Redis connection
        self._redis: Optional[object] = None
        self._redis_checked: bool = False

    def _get_redis(self) -> Optional[object]:
        """Lazily initialize Redis client for distributed rate limiting."""
        if self._redis_checked:
            return self._redis
        self._redis_checked = True

        redis_url = os.environ.get("REDIS_URL", "")
        if not redis_url:
            return None

        try:
            import redis
            self._redis = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            self._redis.ping()
            return self._redis
        except Exception:
            self._redis = None
            return None

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from X-Forwarded-For or request.client.host."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        ip = self._get_client_ip(request)
        now = time.time()
        window_start = now - self.window_seconds

        # ── Redis-backed distributed rate limiting ────────────────────────────
        redis = self._get_redis()
        if redis is not None:
            try:
                key = f"ratelimit:{ip}"
                # Use Redis sorted set: add current request, remove stale entries
                pipe = redis.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, self.window_seconds + 1)
                _, _, current_count, _ = pipe.execute()

                remaining = max(0, self.max_requests - int(current_count))
                retry_after = self.window_seconds

                if int(current_count) > self.max_requests:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests", "retry_after": retry_after},
                        headers={
                            "X-RateLimit-Limit": str(self.max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(now + self.window_seconds)),
                        },
                    )

                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = str(self.max_requests)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(int(now + self.window_seconds))
                return response
            except Exception:
                pass  # Redis failed — fall through to in-memory

        # ── In-memory fallback ────────────────────────────────────────────────
        hits = self._hits[ip]
        self._hits[ip] = [t for t in hits if t > window_start]

        current_count = len(self._hits[ip])
        remaining = max(0, self.max_requests - current_count - 1)

        if current_count >= self.max_requests:
            oldest = min(self._hits[ip]) if self._hits[ip] else now
            retry_after = int(oldest + self.window_seconds - now) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests", "retry_after": retry_after},
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(oldest + self.window_seconds)),
                },
            )

        self._hits[ip].append(now)

        # Periodic cleanup to prevent memory leak
        if len(self._hits) > 100000:
            self._cleanup_memory()

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.window_seconds))
        return response

    def _cleanup_memory(self) -> None:
        """Remove stale IP entries from in-memory store."""
        now = time.time()
        window_start = now - self.window_seconds
        stale_ips = [
            ip for ip, hits in self._hits.items()
            if not any(t > window_start for t in hits)
        ]
        for ip in stale_ips:
            del self._hits[ip]
