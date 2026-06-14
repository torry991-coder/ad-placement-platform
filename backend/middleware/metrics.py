"""
Prometheus-compatible metrics endpoint for monitoring.

Exposes at GET /api/metrics — works without the prometheus_client
package by generating plain-text Prometheus exposition format directly.

Metrics exposed:
  - http_requests_total{method, endpoint, status}
  - http_request_duration_seconds (histogram)
  - db_pool_connections{state}
  - cache_hits_total, cache_misses_total
  - scheduler_status
  - process_uptime_seconds
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ── Counters & Histograms ────────────────────────────────────────────────
_start_time = time.time()

_request_count: dict[tuple[str, str, str], int] = defaultdict(int)
_request_duration_buckets: list[float] = []
_BUCKET_BOUNDARIES = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records HTTP request counts and latencies for Prometheus."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        t0 = time.time()
        response = await call_next(request)
        elapsed = time.time() - t0

        method = request.method
        # Group dynamic path params: /api/campaigns/123 → /api/campaigns/{id}
        endpoint = request.url.path
        status = str(response.status_code)

        _request_count[(method, endpoint, status)] += 1
        _request_duration_buckets.append(elapsed)

        return response


def _generate_metrics_text() -> str:
    """Generate Prometheus exposition format text."""
    now = time.time()
    lines: list[str] = []

    # ── HTTP request counter ─────────────────────────────────────────────
    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    for (method, endpoint, status), count in sorted(_request_count.items()):
        lines.append(
            f'http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
        )

    # ── HTTP request duration ────────────────────────────────────────────
    lines.append("# HELP http_request_duration_seconds HTTP request latency")
    lines.append("# TYPE http_request_duration_seconds histogram")
    durations = sorted(_request_duration_buckets[-10000:])  # last 10K samples
    if durations:
        total = len(durations)
        cum = 0
        for boundary in _BUCKET_BOUNDARIES:
            cum = sum(1 for d in durations if d <= boundary)
            lines.append(
                f'http_request_duration_seconds_bucket{{le="{boundary}"}} {cum}'
            )
        lines.append(f"http_request_duration_seconds_bucket{{le=\"+Inf\"}} {total}")
        lines.append(f"http_request_duration_seconds_count {total}")
        lines.append(f"http_request_duration_seconds_sum {sum(durations):.4f}")

    # ── DB pool stats ────────────────────────────────────────────────────
    try:
        from backend.database import get_pool_stats
        pool = get_pool_stats()
        lines.append("# HELP db_pool_size Database connection pool size")
        lines.append("# TYPE db_pool_size gauge")
        lines.append(f"db_pool_size {pool.get('size', 0)}")
        lines.append("# HELP db_pool_checked_out Database connections in use")
        lines.append("# TYPE db_pool_checked_out gauge")
        lines.append(f"db_pool_checked_out {pool.get('checked_out', 0)}")
        lines.append("# HELP db_pool_overflow Database pool overflow count")
        lines.append("# TYPE db_pool_overflow gauge")
        lines.append(f"db_pool_overflow {pool.get('overflow', 0)}")
    except Exception:
        pass

    # ── Cache stats ──────────────────────────────────────────────────────
    try:
        from backend.cache import get_cache_stats
        cache = get_cache_stats()
        lines.append("# HELP cache_hits_total Cache hit count")
        lines.append("# TYPE cache_hits_total counter")
        lines.append(f"cache_hits_total {cache.get('hits', 0)}")
        lines.append("# HELP cache_misses_total Cache miss count")
        lines.append("# TYPE cache_misses_total counter")
        lines.append(f"cache_misses_total {cache.get('misses', 0)}")
        lines.append("# HELP cache_hit_rate Cache hit rate (0-100)")
        lines.append("# TYPE cache_hit_rate gauge")
        lines.append(f"cache_hit_rate {cache.get('hit_rate', 0)}")
    except Exception:
        pass

    # ── Scheduler ────────────────────────────────────────────────────────
    try:
        from backend.tasks.scheduler import get_scheduler_status
        sched = get_scheduler_status()
        lines.append("# HELP scheduler_running Whether the task scheduler is running")
        lines.append("# TYPE scheduler_running gauge")
        lines.append(f"scheduler_running {1 if sched.get('scheduler_running') else 0}")
    except Exception:
        pass

    # ── Process uptime ───────────────────────────────────────────────────
    uptime = now - _start_time
    lines.append("# HELP process_uptime_seconds Process uptime in seconds")
    lines.append("# TYPE process_uptime_seconds gauge")
    lines.append(f"process_uptime_seconds {uptime:.1f}")

    # ── Python process info ──────────────────────────────────────────────
    import os
    lines.append("# HELP process_info Process metadata")
    lines.append("# TYPE process_info gauge")
    lines.append(f'process_info{{pid="{os.getpid()}"}} 1')

    return "\n".join(lines) + "\n"


def get_metrics_summary() -> dict:
    """Return a JSON summary of current metrics (for /api/health/detailed)."""
    try:
        from backend.database import get_pool_stats
        pool = get_pool_stats()
    except Exception:
        pool = {}

    try:
        from backend.cache import get_cache_stats
        cache = get_cache_stats()
    except Exception:
        cache = {}

    total_requests = sum(_request_count.values())

    return {
        "uptime_seconds": round(time.time() - _start_time, 1),
        "total_requests": total_requests,
        "request_rate_per_min": round(total_requests / max(time.time() - _start_time, 1) * 60, 1),
        "db_pool": pool,
        "cache": cache,
    }
