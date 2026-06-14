"""LLM service — provides chat completion interface to configured LLM providers."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Optional

from backend.config import get_settings

settings = get_settings()


async def chat(
    message: str,
    system_prompt: Optional[str] = None,
    context: Optional[dict] = None,
    provider: str = "openai",
) -> dict:
    """Send a chat message to the LLM and return the response."""
    system = system_prompt or (
        "You are an AI advertising assistant for an enterprise ad platform. "
        "Help users optimize campaigns, analyze performance data, and make "
        "data-driven decisions. Be concise and actionable."
    )

    # Try OpenAI
    if provider == "openai" and settings.openai_api_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            messages = [{"role": "system", "content": system}]
            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})
            messages.append({"role": "user", "content": message})
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            return {
                "reply": resp.choices[0].message.content or "",
                "model_used": "gpt-4o",
                "actions": [],
                "suggestions": [],
            }
        except Exception:
            pass  # fall through to fallback

    # Fallback: return a deterministic response
    return {
        "reply": _fallback_reply(message),
        "model_used": "fallback",
        "actions": [],
        "suggestions": _generate_suggestions(message),
    }


async def chat_stream(
    message: str,
    system_prompt: Optional[str] = None,
    context: Optional[dict] = None,
) -> AsyncGenerator[str, None]:
    """Stream chat response via Server-Sent Events."""
    # Yield metadata
    yield f"event: start\ndata: {json.dumps({'model': 'fallback'})}\n\n"

    # Simulate streaming by yielding words of the fallback response
    reply = _fallback_reply(message)
    words = reply.split()
    for i, word in enumerate(words):
        yield f"data: {word + (' ' if i < len(words) - 1 else '')}\n\n"

    # Yield suggestions
    suggestions = _generate_suggestions(message)
    yield f"event: suggestions\ndata: {json.dumps(suggestions)}\n\n"
    yield "event: done\ndata: {}\n\n"


def _fallback_reply(message: str) -> str:
    """Generate a helpful fallback reply without LLM API."""
    msg_lower = message.lower()
    if "budget" in msg_lower:
        return (
            "Based on your campaign performance data, I recommend reviewing your "
            "daily budget allocation. Check campaigns with high spend but low ROAS "
            "first. Consider pausing underperforming campaigns and reallocating budget "
            "to your top performers. Would you like me to show a budget breakdown?"
        )
    if "ctr" in msg_lower or "click" in msg_lower:
        return (
            "CTR optimization involves several levers: creative testing (try A/B testing "
            "different headlines and CTAs), audience refinement (narrow to higher-intent "
            "segments), and placement adjustments. I can help you set up an A/B experiment "
            "or suggest audience segments with historically high CTR."
        )
    if "roas" in msg_lower or "revenue" in msg_lower:
        return (
            "To improve ROAS, focus on conversion-optimized bidding strategies like "
            "Target ROAS or Max Conversions with a target CPA. Also review your "
            "attribution model — using data-driven attribution often surfaces more "
            "accurate ROAS figures. I can analyze your current campaign performance."
        )
    if "overview" in msg_lower or "dashboard" in msg_lower or "summary" in msg_lower:
        return (
            "Here's your campaign overview: your active campaigns are running with "
            "various bid strategies. I recommend checking the analytics dashboard for "
            "KPIs like CTR, CVR, and ROAS trends. The system can alert you on significant "
            "metric changes. What specific aspect would you like to dive into?"
        )
    return (
        "I'm your ad platform assistant. I can help with campaign optimization, "
        "performance analysis, budget recommendations, A/B test setup, and more. "
        "What would you like help with today?"
    )


def _generate_suggestions(message: str) -> list[str]:
    """Generate contextual suggestions based on user message."""
    msg_lower = message.lower()
    suggestions = [
        "Show me campaign performance dashboard",
        "Run an A/B test for my top campaign",
    ]
    if "budget" in msg_lower:
        suggestions = [
            "Show budget utilization by campaign",
            "Pause underperforming campaigns",
            "Set up budget alerts",
        ]
    elif "ctr" in msg_lower:
        suggestions = [
            "Analyze CTR trends over last 7 days",
            "Compare CTR across platforms",
            "Optimize creatives for higher CTR",
        ]
    elif "roas" in msg_lower:
        suggestions = [
            "Switch to Target ROAS bidding",
            "Show ROAS by campaign",
            "Analyze conversion paths",
        ]
    return suggestions
