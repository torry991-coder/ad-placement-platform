"""Application configuration via pydantic-settings.

All settings can be overridden by environment variables (or a .env file).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./ad_platform.db"
    database_echo: bool = False

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── LLM Providers ─────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"
    ollama_base_url: str = ""
    ollama_model: str = "llama3"

    # ── Server ────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    secret_key: str = "dev-secret-change-in-production"
    jwt_secret_key: str = ""  # set via env JWT_SECRET_KEY or auto-generated at startup

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: str = (
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1,http://120.79.28.109"
    )

    # ── LLM ───────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    google_api_key: str = ""
    google_model: str = "gemini-2.5-flash"
    ollama_base_url: str = ""
    ollama_model: str = "llama3"
    llm_default_provider: str = "auto"  # auto = first configured, or "deepseek" / "openai" / etc
    llm_retry_max: int = 2
    llm_timeout_seconds: int = 30

    # ── Simulation ────────────────────────────────────────────
    simulated_auction_qps: int = 1000
    simulated_campaigns: int = 50
    simulated_daily_impressions: int = 100000

    # ── Connection Pool (tuned for 100K concurrent) ───────────
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def available_llm_providers(self) -> list[str]:
        """Return names of providers that have credentials configured."""
        providers: list[str] = []
        if self.deepseek_api_key:
            providers.append("deepseek")
        if self.openai_api_key:
            providers.append("openai")
        if self.google_api_key:
            providers.append("google")
        if self.ollama_base_url:
            providers.append("ollama")
        providers.append("fallback")  # always available
        return providers


@lru_cache
def get_settings() -> Settings:
    return Settings()
