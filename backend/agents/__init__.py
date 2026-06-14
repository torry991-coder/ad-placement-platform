"""Agents package — specialized AI agents for ad platform operations.

Agents:
- AuditAgent: comprehensive campaign health audit
- StrategyAgent: bid and budget strategy recommendations
- CreativeAgent: ad creative copy generation
- AudienceAgent: audience segment expansion
- BudgetAgent: pacing and redistribution analysis
- ReportAgent: executive summary report generation

Pipeline:
- run_full_pipeline: 6-agent sequential pipeline with SSE streaming
"""

from backend.agents.auditor import AuditAgent
from backend.agents.strategist import StrategyAgent
from backend.agents.copywriter import CreativeAgent
from backend.agents.audience_agent import AudienceAgent
from backend.agents.budget_agent import BudgetAgent
from backend.agents.report_agent import ReportAgent
from backend.agents.pipeline import (
    run_pipeline,
    run_pipeline_stream,
    run_full_pipeline,
)

__all__ = [
    "AuditAgent",
    "StrategyAgent",
    "CreativeAgent",
    "AudienceAgent",
    "BudgetAgent",
    "ReportAgent",
    "run_pipeline",
    "run_pipeline_stream",
    "run_full_pipeline",
]
