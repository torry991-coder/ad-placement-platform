# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install Python dependencies (layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r adplatform && useradd -r -g adplatform adplatform

# Install runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ ./backend/
COPY gunicorn.conf.py .

# Create data directory for SQLite
RUN mkdir -p /app/data && chown -R adplatform:adplatform /app

# Switch to non-root user
USER adplatform

EXPOSE 8000

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# ── Entrypoint: Gunicorn with Uvicorn workers ────────────────────────────────
# For 100K concurrent users: 17 workers × 4 threads = 68 concurrent handlers
# Override WEB_CONCURRENCY and WORKER_THREADS via env vars
CMD ["gunicorn", "-c", "gunicorn.conf.py", "backend.main:app"]
