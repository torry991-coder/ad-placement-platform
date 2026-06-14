"""LLM Provider abstraction layer — pluggable backends for agent reasoning.

Supports OpenAI, Google Gemini, Ollama (local), and a deterministic fallback
that requires no API keys. Each provider implements a uniform chat() interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    name: str = "base"

    @abstractmethod
    async def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """Send a message and return the model's reply as a string."""
        ...


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    """Chat via OpenAI-compatible API (gpt-4o, gpt-4o-mini, etc.)."""

    name: str = "openai"

    async def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key is not configured (set OPENAI_API_KEY).")

        model = getattr(settings, "openai_model", "gpt-4o") or "gpt-4o"

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key)
            messages: list[dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": message})

            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2048,
                temperature=0.4,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            raise RuntimeError(f"OpenAIProvider.chat failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Google Gemini provider
# ---------------------------------------------------------------------------

class GoogleProvider(LLMProvider):
    """Chat via Google Generative AI (Gemini models)."""

    name: str = "google"

    async def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        api_key = settings.google_api_key
        if not api_key:
            raise ValueError("Google API key is not configured (set GOOGLE_API_KEY).")

        model_name = getattr(settings, "google_model", "gemini-2.5-flash") or "gemini-2.5-flash"

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name=model_name)

            # Gemini has no native system prompt — prepend it to the user message
            prompt = f"{system_prompt}\n\n---\n\n{message}" if system_prompt else message

            response = await model.generate_content_async(prompt)
            if hasattr(response, "text"):
                return response.text or ""
            # Fallback for multi-candidate responses
            if response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content:
                    parts = getattr(candidate.content, "parts", [])
                    if parts:
                        return str(parts[0]) if hasattr(parts[0], "text") else "".join(str(p) for p in parts)
            return ""

        except Exception as exc:
            raise RuntimeError(f"GoogleProvider.chat failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Ollama provider (local models)
# ---------------------------------------------------------------------------

class OllamaProvider(LLMProvider):
    """Chat via a local Ollama server."""

    name: str = "ollama"

    async def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        base_url = settings.ollama_base_url
        if not base_url:
            raise ValueError("Ollama base URL is not configured (set OLLAMA_BASE_URL).")

        model_name = getattr(settings, "ollama_model", "llama3") or "llama3"

        try:
            import ollama

            # ollama-python is sync-only; wrap in asyncio thread
            import asyncio

            options = {}
            if system_prompt:
                options["system"] = system_prompt

            resp = await asyncio.to_thread(
                lambda: ollama.chat(
                    model=model_name,
                    messages=[{"role": "user", "content": message}],
                    options=options,
                )
            )
            return resp.get("message", {}).get("content", "")

        except Exception as exc:
            raise RuntimeError(f"OllamaProvider.chat failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Deterministic / rule-based fallback (no API key required)
# ---------------------------------------------------------------------------

class FallbackProvider(LLMProvider):
    """Deterministic provider that uses keyword matching for ad-platform responses.

    Always available. No network calls, no API keys. Returns structured,
    actionable advice based on the message content.
    """

    name: str = "fallback"

    async def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """Return a deterministic response based on keyword analysis."""
        # system_prompt is acknowledged but the fallback does its own thing
        return _fallback_reply(message)


# ---------------------------------------------------------------------------
# Keyword-based fallback logic
# ---------------------------------------------------------------------------

def _fallback_reply(message: str) -> str:
    """Generate structured, actionable fallback advice from keywords."""
    msg = message.lower()

    # ── Budget / spend ──
    if any(kw in msg for kw in ("budget", "spend", "spending", "成本", "预算")):
        if "overspending" in msg or "超" in msg:
            return (
                "**Budget Alert:** Campaign is overspending vs planned pacing.\n"
                "- Reduce daily budget by 15-25% immediately.\n"
                "- Shift unspent allocation to the top-ROAS platform.\n"
                "- Enable auto-pacing guardrails to prevent recurrence."
            )
        return (
            "**Budget Analysis:** Review your budget allocation by platform ROAS.\n"
            "- Top performers (ROAS > 2.0) should receive 60-70% of the budget.\n"
            "- Underperformers (ROAS < 1.0) should be paused or capped at 10%.\n"
            "- Set up automated budget redistribution rules for real-time optimization."
        )

    # ── CTR / clicks ──
    if any(kw in msg for kw in ("ctr", "click", "点击率", "点击")):
        return (
            "**CTR Optimization Plan:**\n"
            "1. A/B test 3-5 new headline variants per ad group.\n"
            "2. Refresh creatives with fatigue score > 60.\n"
            "3. Narrow audience targeting to high-CTR segments (top 20%).\n"
            "4. Add urgency-driven CTAs: 'Limited Time', 'Shop Now'.\n"
            "5. Review placement performance — pause low-CTR placements."
        )

    # ── CVR / conversions ──
    if any(kw in msg for kw in ("cvr", "conversion", "转化率", "转化")):
        return (
            "**Conversion Rate (CVR) Improvement:**\n"
            "- Align landing page messaging with ad creative (message match).\n"
            "- Reduce page load time below 2.5s (target 1.5s).\n"
            "- Add social proof elements: reviews, trust badges.\n"
            "- Test single vs multi-step forms in the conversion flow.\n"
            "- Implement retargeting for users who clicked but didn't convert."
        )

    # ── ROAS / revenue ──
    if any(kw in msg for kw in ("roas", "revenue", "收入")):
        return (
            "**ROAS Improvement Strategy:**\n"
            "- Switch to Target ROAS bidding with a target of 200-300%.\n"
            "- Pause campaigns with ROAS < 0.8 for > 7 days.\n"
            "- Increase budget on campaigns with ROAS > 3.0 by 20-30%.\n"
            "- Review attribution model — use data-driven attribution.\n"
            "- Optimize audience segments toward high-LTV customer profiles."
        )

    # ── Creative / creative fatigue ──
    if any(kw in msg for kw in ("creative", "ad", "创意", "素材", "fatigue", "疲劳")):
        return (
            "**Creative Rotation Analysis:**\n"
            "- Creatives with fatigue score > 70: pause immediately.\n"
            "- Creatives with fatigue 40-60: prepare replacements.\n"
            "- Best-performing creative elements: keep headline structure, test images.\n"
            "- Recommend 3 fresh variants per ad group every 14 days.\n"
            "- Use dynamic creative optimization (DCO) for auto-assembly."
        )

    # ── Audience / targeting ──
    if any(kw in msg for kw in ("audience", "target", "segment", "受众", "定向")):
        return (
            "**Audience Expansion Strategy:**\n"
            "- Identify top-performing audience segments (CTR > 2%, CVR > 5%).\n"
            "- Create 1-2% lookalike audiences from each top segment.\n"
            "- Expand age ranges by ±5 years for strong segments.\n"
            "- Add interest-based layering: cross-sell to adjacent categories.\n"
            "- Test broad targeting with automated bidding as a control group."
        )

    # ── Pacing / campaign status ──
    if any(kw in msg for kw in ("pace", "pacing", "campaign status", "状态")):
        return (
            "**Campaign Pacing Review:**\n"
            "- Check spend-vs-expected for the current hour.\n"
            "- Overspending: cap hourly budget to prevent front-loading.\n"
            "- Underspending: check bid floors and audience size.\n"
            "- End-date approaching: accelerate spend if budget remaining > 30%.\n"
            "- Set up automated pacing alerts at 80%, 100%, and 120% of daily budget."
        )

    # ── Report / summary / overview ──
    if any(kw in msg for kw in ("report", "summary", "overview", "dashboard", "报告", "总结", "概览")):
        return (
            "**Campaign Performance Overview:**\n"
            "- Review the top 5 KPIs: CTR, CVR, ROAS, CPA, Spend.\n"
            "- Compare week-over-week trends for each KPI.\n"
            "- Identify top and bottom 3 campaigns by ROAS.\n"
            "- Check for anomalies: sudden spend spikes or conversion drops.\n"
            "- Generate a full executive summary report for stakeholders."
        )

    # ── Generic / catch-all ──
    return (
        "**Ad Platform Agent Analysis:**\n"
        "I can help with the following areas:\n"
        "- Budget optimization and pacing analysis\n"
        "- CTR and CVR improvement strategies\n"
        "- ROAS maximization and bid adjustments\n"
        "- Creative rotation and fatigue management\n"
        "- Audience expansion and lookalike targeting\n"
        "- Full campaign performance reports\n\n"
        "Please specify which aspect you'd like me to analyze, "
        "or provide a campaign ID for a full audit."
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_provider(name: str = "auto") -> LLMProvider:
    """Return an LLM provider instance.

    ``name`` is one of: ``"openai"``, ``"google"``, ``"ollama"``, ``"fallback"``,
    or ``"auto"`` (try the first configured provider, fall back to fallback).
    """
    if name == "auto":
        if settings.openai_api_key:
            return OpenAIProvider()
        if settings.google_api_key:
            return GoogleProvider()
        if settings.ollama_base_url:
            return OllamaProvider()
        return FallbackProvider()

    providers: dict[str, type[LLMProvider]] = {
        "openai": OpenAIProvider,
        "google": GoogleProvider,
        "ollama": OllamaProvider,
        "fallback": FallbackProvider,
    }

    cls = providers.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {', '.join(providers.keys())}"
        )
    return cls()
