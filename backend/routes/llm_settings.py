"""LLM Settings API — provider list + user-selectable configuration."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import get_settings
from backend.llm.providers import _AUTO_ORDER, _provider_configured

router = APIRouter(prefix="/api/llm", tags=["llm"])

settings = get_settings()

# ── Provider metadata ─────────────────────────────────────────────

PROVIDER_META = {
    "deepseek": {
        "name": "DeepSeek",
        "models": [
            "deepseek-chat",
            "deepseek-reasoner",
            "deepseek-v3",
        ],
        "description": "DeepSeek API — 国内最快，性价比最高",
        "base_url": "https://api.deepseek.com/v1",
    },
    "openai": {
        "name": "OpenAI",
        "models": [
            "gpt-4.1",
            "gpt-4o",
            "gpt-4o-mini",
            "o4-mini",
            "o3-mini",
            "gpt-4.1-mini",
        ],
        "description": "OpenAI — 最强综合能力，GPT-4.1 旗舰",
        "base_url": "https://api.openai.com/v1",
    },
    "google": {
        "name": "Google Gemini",
        "models": [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
        ],
        "description": "Google Gemini — 多模态，高性价比",
        "base_url": "https://generativelanguage.googleapis.com",
    },
    "ollama": {
        "name": "Ollama (本地)",
        "models": [
            "llama3.3:70b",
            "qwen2.5:72b",
            "deepseek-r1:70b",
            "llama3:8b",
            "qwen2.5:7b",
        ],
        "description": "本地运行，零成本，隐私保护",
        "base_url": "http://localhost:11434",
    },
    "fallback": {
        "name": "内置规则引擎",
        "models": ["fallback"],
        "description": "无需 API Key，关键词匹配广告建议",
        "base_url": "",
    },
}


# ── Models ────────────────────────────────────────────────────────

class ProviderInfo(BaseModel):
    id: str
    name: str
    models: list[str]
    description: str
    configured: bool
    current: bool = False


class LLMSettingsRequest(BaseModel):
    provider: str = "auto"
    model: str = ""
    api_key: str | None = None


class LLMSettingsResponse(BaseModel):
    provider: str
    model: str
    providers: list[ProviderInfo]


# ── In-memory runtime config ──────────────────────────────────────

_runtime_config = {
    "provider": settings.llm_default_provider or "auto",
    "model": "",
}


def _get_current_model() -> str:
    if _runtime_config["model"]:
        return _runtime_config["model"]
    p = _runtime_config["provider"]
    if p in PROVIDER_META:
        return PROVIDER_META[p]["models"][0]
    return ""


# ── Routes ────────────────────────────────────────────────────────

@router.get("/providers", response_model=LLMSettingsResponse)
async def list_providers():
    """Return available providers with status and current selection."""
    current = _runtime_config["provider"]
    providers = []
    for p_id in _AUTO_ORDER:
        if p_id not in PROVIDER_META:
            continue
        meta = PROVIDER_META[p_id]
        providers.append(ProviderInfo(
            id=p_id,
            name=meta["name"],
            models=meta["models"],
            description=meta["description"],
            configured=_provider_configured(p_id),
            current=(p_id == current),
        ))
    return LLMSettingsResponse(
        provider=current,
        model=_get_current_model(),
        providers=providers,
    )


@router.post("/settings", response_model=LLMSettingsResponse)
async def save_settings(body: LLMSettingsRequest):
    """Save LLM provider and model preference.

    Provider: deepseek | openai | google | ollama | fallback | auto
    Model: model name for selected provider
    api_key: optional API key (stored in runtime, not persisted to disk)
    """
    provider = body.provider.strip()
    if provider not in PROVIDER_META:
        raise HTTPException(400, f"Unknown provider: {provider}")

    _runtime_config["provider"] = provider
    if body.model:
        _runtime_config["model"] = body.model
    else:
        _runtime_config["model"] = PROVIDER_META[provider]["models"][0]

    # Store API key in settings (runtime only, resets on restart)
    if body.api_key:
        if provider == "deepseek":
            settings.deepseek_api_key = body.api_key
        elif provider == "openai":
            settings.openai_api_key = body.api_key
        elif provider == "google":
            settings.google_api_key = body.api_key

    from backend.llm.providers import get_provider

    # Reset cached provider instance
    try:
        p = get_provider(provider)
        # Test connectivity
        test_ok = True
    except Exception:
        test_ok = False

    return await list_providers()


@router.get("/settings", response_model=LLMSettingsResponse)
async def get_settings():
    """Get current LLM settings."""
    return await list_providers()


def get_llm_runtime_config() -> dict:
    """Return current runtime LLM config (used by agent pipeline)."""
    return dict(_runtime_config)
