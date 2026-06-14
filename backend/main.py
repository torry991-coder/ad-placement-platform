"""FastAPI application entry point.

Start with:  uvicorn backend.main:app --reload
Production:  gunicorn -c gunicorn.conf.py backend.main:app
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.database import close_db, get_db, init_db, get_pool_stats
from backend.cache import get_cache_stats
from backend.tasks.scheduler import start_scheduler, stop_scheduler, get_scheduler_status

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown hooks."""
    await init_db()
    # Create default admin user if none exists
    from backend.auth import ensure_default_admin

    async for session in get_db():
        await ensure_default_admin(session)
        break

    # Start background task scheduler
    await start_scheduler()

    yield

    # Stop background task scheduler
    await stop_scheduler()
    await close_db()


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="智能广告投放系统 — Ad Placement Platform",
    description="Enterprise-grade smart ad bidding & management system. Supports 100K concurrent users.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting (tuned for 100K concurrency) ───────────────────────────────
from backend.middleware import RateLimitMiddleware
from backend.middleware.metrics import MetricsMiddleware, _generate_metrics_text, get_metrics_summary

_rate_max = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", 10000))
_rate_window = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", 60))
app.add_middleware(RateLimitMiddleware, max_requests=_rate_max, window_seconds=_rate_window)

# ── Prometheus metrics middleware (after rate limiter, before routes) ─────────
app.add_middleware(MetricsMiddleware)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["system"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "llm_providers": settings.available_llm_providers,
        "database": "connected",
    }


@app.get("/api/health/detailed", tags=["system"])
async def detailed_health_check() -> dict:
    """Detailed health check with pool stats, cache, scheduler, and metrics."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "llm_providers": settings.available_llm_providers,
        "database_pool": get_pool_stats(),
        "cache": get_cache_stats(),
        "scheduler": get_scheduler_status(),
        "metrics": get_metrics_summary(),
    }


@app.get("/api/metrics", tags=["system"])
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=_generate_metrics_text(), media_type="text/plain")


# ── Exception handlers ───────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    from loguru import logger

    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# ── Register routers ─────────────────────────────────────────────────────────
from backend.routes.campaigns import router as campaigns_router
from backend.routes.bidding import router as bidding_router
from backend.routes.analytics import router as analytics_router
from backend.routes.experiments import router as experiments_router
from backend.routes.audiences import router as audiences_router
from backend.routes.alerts import router as alerts_router
from backend.routes.reports import router as reports_router
from backend.routes.agent import router as agent_router
from backend.routes.creatives import router as creatives_router
from backend.routes.events import router as events_router
from backend.routes.rag import router as rag_router
from backend.routes.websocket import router as websocket_router

app.include_router(campaigns_router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(bidding_router, tags=["bidding"])
app.include_router(analytics_router, tags=["analytics"])
app.include_router(experiments_router, tags=["experiments"])
app.include_router(audiences_router, tags=["audiences"])
app.include_router(alerts_router, tags=["alerts"])
app.include_router(reports_router, tags=["reports"])
app.include_router(agent_router, tags=["agent"])
app.include_router(creatives_router, tags=["creatives"])
app.include_router(events_router, tags=["events"])
app.include_router(rag_router, tags=["rag"])
app.include_router(websocket_router, tags=["websocket"])

# ── Auth router ──────────────────────────────────────────────────────────────
from backend.auth import router as auth_router

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# ── LLM Settings ──────────────────────────────────────────────────────────────
from backend.routes.llm_settings import router as llm_settings_router

app.include_router(llm_settings_router)
