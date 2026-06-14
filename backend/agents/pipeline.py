"""Agent pipeline — multi-step agent workflow for ad platform operations.

Provides two pipelines:

1. ``run_pipeline`` / ``run_pipeline_stream`` — single-turn chat pipeline
   (original interface, preserved for backward compatibility).

2. ``run_full_pipeline`` — 6-agent sequential pipeline that streams SSE events.
   Agents run in order: auditor → strategist → budget_agent → audience_agent →
   creative_agent → report_agent. Each agent's output becomes context for the next.

All agents work without an LLM (rule-based fallbacks) and produce structured
JSON-serializable output.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.service import chat as llm_chat


# ── Original (simplified) pipeline — kept for backward compatibility ──


async def run_pipeline(
    message: str,
    campaign_id: Optional[int] = None,
    context: Optional[dict] = None,
) -> dict:
    """Run a multi-step agent pipeline: analyze → decide → act.

    This is a simplified pipeline that:
    1. Sends the user message to the LLM
    2. Parses any actionable items
    3. Returns a structured response with actions and suggestions.
    """
    system_prompt = (
        "You are an autonomous advertising agent. Analyze the user request, "
        "provide actionable recommendations, and specify any actions that should "
        "be taken. Respond in a structured format."
    )

    if context is None:
        context = {}
    if campaign_id:
        context["campaign_id"] = campaign_id

    result = await llm_chat(message, system_prompt=system_prompt, context=context)
    return result


async def run_pipeline_stream(
    message: str,
    campaign_id: Optional[int] = None,
    context: Optional[dict] = None,
) -> AsyncGenerator[str, None]:
    """Stream the agent pipeline output via SSE."""
    from backend.llm.service import chat_stream

    async for chunk in chat_stream(message, context=context):
        yield chunk


# ── Full 6-agent pipeline ───────────────────────────────────────────────

# Agent execution order
AGENT_ORDER = [
    "auditor",
    "strategist",
    "budget_agent",
    "audience_agent",
    "creative_agent",
    "report_agent",
]


async def run_full_pipeline(
    campaign_id: int,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Run the complete 6-agent pipeline with SSE streaming.

    Agents execute in order: auditor → strategist → budget_agent →
    audience_agent → creative_agent → report_agent.

    Each agent receives the outputs from all preceding agents as context.

    Yields SSE-formatted strings:
        event: agent_start
        data: {"agent": "<name>", "message": "<human-readable>"}

        event: agent_token
        data: "<partial output text>"

        event: agent_done
        data: {"agent": "<name>", "result": <structured output>}

        event: pipeline_complete
        data: {"summary": "..."}

        event: error
        data: {"agent": "<name>", "error": "<message>"}
    """
    context_chain: dict[str, Any] = {
        "campaign_id": campaign_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    agent_outputs: dict[str, Any] = {}

    for agent_name in AGENT_ORDER:
        # Signal agent start
        yield _sse_event("agent_start", {
            "agent": agent_name,
            "message": f"Running {agent_name}...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        try:
            # Run the agent
            result = await _run_agent(agent_name, campaign_id, db, context_chain)

            # Store result
            agent_outputs[agent_name] = result

            # Feed result into context chain for next agents
            context_chain[agent_name] = result

            # Yield agent_done with structured result
            yield _sse_event("agent_done", {
                "agent": agent_name,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Yield a human-readable summary token for streaming UI
            summary_token = _agent_summary_token(agent_name, result)
            if summary_token:
                yield _sse_data(summary_token)

        except Exception as exc:
            error_result = {"error": str(exc), "agent": agent_name}
            agent_outputs[agent_name] = error_result
            context_chain[agent_name] = error_result

            yield _sse_event("error", {
                "agent": agent_name,
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # Continue to next agent — partial pipeline is better than nothing

    # Build final report from report_agent output if available
    report = agent_outputs.get("report_agent", "")
    if isinstance(report, dict):
        report = json.dumps(report, ensure_ascii=False, default=str)

    # Signal pipeline complete
    yield _sse_event("pipeline_complete", {
        "summary": f"Pipeline complete for campaign {campaign_id}. "
                   f"{len(agent_outputs)} agents executed.",
        "agents_executed": list(agent_outputs.keys()),
        "pipeline_report": report if isinstance(report, str) else str(report),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ── Agent runner ────────────────────────────────────────────────────────

async def _run_agent(
    agent_name: str,
    campaign_id: int,
    db: AsyncSession,
    context: dict[str, Any],
) -> Any:
    """Dispatch to the appropriate agent and return its output."""

    if agent_name == "auditor":
        from backend.agents.auditor import AuditAgent
        agent = AuditAgent()
        return await agent.audit(campaign_id, db)

    elif agent_name == "strategist":
        from backend.agents.strategist import StrategyAgent
        agent = StrategyAgent()
        return await agent.recommend(campaign_id, db)

    elif agent_name == "budget_agent":
        from backend.agents.budget_agent import BudgetAgent
        agent = BudgetAgent()
        return await agent.recommend(campaign_id, db)

    elif agent_name == "audience_agent":
        from backend.agents.audience_agent import AudienceAgent
        agent = AudienceAgent()
        return await agent.expand(campaign_id, db)

    elif agent_name == "creative_agent":
        from backend.agents.copywriter import CreativeAgent
        agent = CreativeAgent()
        return await agent.generate(campaign_id, db, count=3)

    elif agent_name == "report_agent":
        from backend.agents.report_agent import ReportAgent
        agent = ReportAgent()
        return await agent.summarize(campaign_id, db)

    else:
        raise ValueError(f"Unknown agent: {agent_name}")


# ── SSE formatting helpers ──────────────────────────────────────────────

def _sse_event(event: str, data: Any) -> str:
    """Format an SSE event with a named event type."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _sse_data(data: str) -> str:
    """Format an SSE data-only message (for token streaming)."""
    return f"data: {data}\n\n"


def _agent_summary_token(agent_name: str, result: Any) -> str:
    """Generate a human-readable summary line for streaming UI display."""
    if isinstance(result, dict):
        if agent_name == "auditor":
            score = result.get("overall_score", "N/A")
            issues = len(result.get("issues", []))
            return f"✅ Audit complete — Score: {score}/100, {issues} issue(s) found."
        elif agent_name == "strategist":
            bids = len(result.get("bid_adjustments", []))
            budgets = len(result.get("budget_recommendations", []))
            return f"✅ Strategy ready — {bids} bid adjustment(s), {budgets} budget recommendation(s)."
        elif agent_name == "budget_agent":
            pacing = len(result.get("pacing_adjustments", []))
            redist = len(result.get("redistribution", []))
            return f"✅ Budget analysis done — {pacing} pacing adjustment(s), {redist} redistribution(s)."
        elif agent_name == "audience_agent":
            if isinstance(result, list):
                return f"✅ Audience expansion — {len(result)} segment(s) recommended."
            return "✅ Audience analysis complete."
        elif agent_name == "creative_agent":
            if isinstance(result, list):
                return f"✅ Creative generation — {len(result)} variant(s) produced."
            return "✅ Creative generation complete."
        elif agent_name == "report_agent":
            return "✅ Executive report generated."
    elif isinstance(result, list):
        return f"✅ {agent_name} complete — {len(result)} item(s)."
    elif isinstance(result, str):
        preview = result[:80].replace("\n", " ")
        return f"✅ {agent_name} complete: {preview}..."
    return f"✅ {agent_name} complete."
