"""Async SQLAlchemy engine + session factory.

Supports both SQLite (dev) and PostgreSQL (prod) via DATABASE_URL env var.

Connection pool tuned for 100K concurrent users:
  - PostgreSQL: pool_size=50, max_overflow=100, pool_recycle=3600
  - SQLite:     pool_size=10, max_overflow=20 (single-writer by design)
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings

settings = get_settings()

# ── Connection pool sizing ────────────────────────────────────────────────────
# Read from env vars with sensible defaults for 100K concurrency
_db_pool_size = int(os.environ.get("DB_POOL_SIZE", 50))
_db_max_overflow = int(os.environ.get("DB_MAX_OVERFLOW", 100))
_db_pool_recycle = int(os.environ.get("DB_POOL_RECYCLE", 3600))
_db_pool_pre_ping = os.environ.get("DB_POOL_PRE_PING", "true").lower() in ("1", "true", "yes")

# For SQLite, limit pool size to avoid contention
_is_sqlite = "sqlite" in settings.database_url.lower()
if _is_sqlite:
    _db_pool_size = min(_db_pool_size, 10)
    _db_max_overflow = min(_db_max_overflow, 20)

# ── Engine ───────────────────────────────────────────────────────────────────
_engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=_db_pool_size,
    max_overflow=_db_max_overflow,
    pool_recycle=_db_pool_recycle,
    pool_pre_ping=_db_pool_pre_ping,
    # PostgreSQL-specific optimizations
    connect_args={"server_settings": {"application_name": "ad_platform"}}
    if "postgresql" in settings.database_url
    else {},
)

# ── Session factory ──────────────────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency: yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables (for dev / first-run)."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close all connections in the pool."""
    await _engine.dispose()


def get_pool_stats() -> dict:
    """Return connection pool statistics for monitoring."""
    pool = _engine.pool
    return {
        "size": getattr(pool, "size", lambda: 0)(),
        "checked_in": getattr(pool, "_checked_in", 0),
        "overflow": getattr(pool, "_overflow", 0),
        "total": getattr(pool, "_total", 0),
    }
