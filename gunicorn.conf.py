"""
Gunicorn configuration for 100K concurrent users.

Usage:
    gunicorn -c gunicorn.conf.py backend.main:app

Key design decisions for 100K concurrency:
  - workers = (2 * CPU_CORES) + 1  → 17 workers on 8-core
  - threads = 4 per worker          → 68 concurrent request handlers
  - backlog = 2048                  → large connection queue
  - keepalive = 5                   → HTTP keep-alive for connection reuse
  - worker_connections = 1000       → max connections per worker
  - timeout = 30                    → aggressive timeout
  - max_requests = 100000            → worker recycling for memory safety
  - max_requests_jitter = 5000      → stagger restarts
"""

import multiprocessing
import os

# ── Server socket ────────────────────────────────────────────────────────────
bind = f"{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', '8000')}"
backlog = 2048

# ── Worker processes ─────────────────────────────────────────────────────────
# For 100K concurrent users on an 8-core server:
workers = int(os.environ.get("WEB_CONCURRENCY", (multiprocessing.cpu_count() * 2) + 1))
worker_class = os.environ.get("WORKER_CLASS", "uvicorn.workers.UvicornWorker")
threads = int(os.environ.get("WORKER_THREADS", 4))
worker_connections = 1000

# ── Worker lifecycle ─────────────────────────────────────────────────────────
max_requests = 100000       # Recycle workers after 100K requests to prevent memory leaks
max_requests_jitter = 5000  # Random variance in max_requests to stagger restarts
preload_app = True          # Preload application code for faster worker startup

# ── Timeouts ─────────────────────────────────────────────────────────────────
timeout = 30                # Request timeout (seconds)
graceful_timeout = 30       # Graceful shutdown timeout
keepalive = 5               # Keep-alive connection timeout

# ── Logging ──────────────────────────────────────────────────────────────────
accesslog = "-"             # Log to stdout
errorlog = "-"              # Log to stderr
loglevel = "warning"        # Only warnings and errors in production
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# ── Process naming ───────────────────────────────────────────────────────────
proc_name = "ad-platform"

# ── Server mechanics ─────────────────────────────────────────────────────────
daemon = False
pidfile = None
umask = 0o022
user = None
group = None
tmp_upload_dir = None

# ── SSL (enable for production) ──────────────────────────────────────────────
# keyfile = "/etc/ssl/private/ad-platform.key"
# certfile = "/etc/ssl/certs/ad-platform.crt"
