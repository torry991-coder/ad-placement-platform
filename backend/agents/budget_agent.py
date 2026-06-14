"""BudgetAgent — budget pacing adjustments and cross-platform redistribution.

Uses the budget_pacer service for current pacing status and suggests specific
budget changes per platform based on real-time performance data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.budget import BudgetLog
from backend.models.performance import PerformanceMetric
from backend.llm.providers import get_provider, FallbackProvider, LLMProvider


class BudgetAgent:
    """Agent that recommends budget pacing adjustments and redistribution."""

    def __init__(self, llm: LLMProvider | None = None):
        self.llm = llm or get_provider("auto")

    async def recommend(self, campaign_id: int, db: AsyncSession) -> dict[str, Any]:
        """Analyze pacing and recommend budget changes.

        Returns:
            dict with keys: campaign_id, campaign_name, pacing_adjustments[],
            redistribution[], current_pacing, budget_summary.
        """
        try:
            campaign = await self._get_campaign(campaign_id, db)
            if campaign is None:
                return self._error_result(campaign_id, "Campaign not found")

            # Get pacing status from budget_pacer service
            try:
                from backend.services.budget_pacer import (
                    get_pacing_status,
                    allocate_hourly_budget,
                    redistribute_budget,
                )
                pacing = await get_pacing_status(campaign_id, db)
                hourly = await allocate_hourly_budget(campaign_id, db)

                # Get platform performance for redistribution
                platforms = await self._get_platform_performance(campaign_id, db)
                redistribution = await redistribute_budget(platforms, db) if platforms else {}
            except Exception as exc:
                pacing = {"pacing_status": "unknown", "error": str(exc)}
                hourly = {"allocations": [], "error": str(exc)}
                redistribution = {"campaigns": [], "error": str(exc)}

            # Rule-based analysis
            pacing_adjustments, budget_summary = self._rule_based_pacing(
                campaign, pacing, hourly
            )

            redistribution_items = self._rule_based_redistribution(
                campaign, pacing, redistribution
            )

            # Try LLM enhancement
            if not isinstance(self.llm, FallbackProvider):
                try:
                    context = {
                        "pacing": pacing,
                        "hourly_allocations": hourly,
                        "redistribution": redistribution,
                        "pacing_adjustments": pacing_adjustments,
                        "redistribution_items": redistribution_items,
                    }
                    llm_result = await self._llm_enhance(campaign, context)
                    if llm_result:
                        pacing_adjustments = llm_result.get(
                            "pacing_adjustments", pacing_adjustments
                        )
                        redistribution_items = llm_result.get(
                            "redistribution", redistribution_items
                        )
                except Exception:
                    pass

            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "pacing_adjustments": pacing_adjustments,
                "redistribution": redistribution_items,
                "current_pacing": {
                    "status": pacing.get("pacing_status", "unknown"),
                    "spend_today": pacing.get("spend_today", 0),
                    "spend_today_pct": pacing.get("spend_today_pct", 0),
                    "daily_budget": pacing.get("daily_budget", 0),
                    "budget_remaining": pacing.get("budget_remaining", 0),
                    "pacing_delta": pacing.get("pacing_delta", 0),
                },
                "budget_summary": budget_summary,
            }

        except Exception as exc:
            return {
                "campaign_id": campaign_id,
                "campaign_name": None,
                "pacing_adjustments": [],
                "redistribution": [],
                "current_pacing": {},
                "budget_summary": {},
                "error": str(exc),
            }

    # ── helpers ────────────────────────────────────────────────────────

    async def _get_campaign(self, cid: int, db: AsyncSession) -> Campaign | None:
        result = await db.execute(select(Campaign).where(Campaign.id == cid))
        return result.scalar_one_or_none()

    async def _get_platform_performance(
        self, cid: int, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Get per-platform performance for redistribution."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        seven_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        rows = (
            await db.execute(
                select(
                    PerformanceMetric.platform,
                    func.sum(PerformanceMetric.impressions),
                    func.sum(PerformanceMetric.clicks),
                    func.sum(PerformanceMetric.conversions),
                    func.sum(PerformanceMetric.spend),
                    func.sum(PerformanceMetric.revenue),
                )
                .where(
                    and_(
                        PerformanceMetric.campaign_id == cid,
                        PerformanceMetric.date >= seven_ago,
                        PerformanceMetric.date <= today,
                    )
                )
                .group_by(PerformanceMetric.platform)
            )
        ).all()

        result = []
        for row in rows:
            platform = row[0] or "unknown"
            imp = int(row[1] or 0)
            clk = int(row[2] or 0)
            conv = int(row[3] or 0)
            sp = float(row[4] or 0.0)
            rev = float(row[5] or 0.0)
            result.append({
                "campaign_id": cid,
                "platform": platform,
                "spend": round(sp, 2),
                "revenue": round(rev, 2),
                "impressions": imp,
                "clicks": clk,
                "conversions": conv,
                "roas": round(rev / sp, 4) if sp > 0 else 0.0,
                "cpa": round(sp / conv, 4) if conv > 0 else 0.0,
            })
        return result

    # ── rule-based pacing ──────────────────────────────────────────────

    def _rule_based_pacing(
        self,
        campaign: Campaign,
        pacing: dict[str, Any],
        hourly: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Generate pacing adjustments from pacing data."""

        adjustments: list[dict[str, Any]] = []
        pacing_status = pacing.get("pacing_status", "unknown")
        daily_budget = float(campaign.daily_budget or 0)
        spend_today = float(pacing.get("spend_today", 0))
        spend_pct = float(pacing.get("spend_today_pct", 0))
        pacing_delta = float(pacing.get("pacing_delta", 0))
        hours_elapsed = int(pacing.get("hours_elapsed", 0))
        hours_remaining = int(pacing.get("hours_remaining", 0))
        hourly_alloc = float(pacing.get("hourly_allocation", 0))

        summary = {
            "daily_budget": round(daily_budget, 2),
            "spend_today": round(spend_today, 2),
            "spend_pct": round(spend_pct, 2),
            "pacing_delta": round(pacing_delta, 2),
            "hours_elapsed": hours_elapsed,
            "hours_remaining": hours_remaining,
            "recommended_hourly_spend": round(hourly_alloc, 2),
        }

        # Overspending
        if pacing_status == "overspending":
            overage_pct = (spend_pct - (hours_elapsed / 24.0 * 100.0)) if hours_elapsed > 0 else 0
            adjustments.append({
                "type": "reduce_pacing",
                "action": "cap_hourly_spend",
                "current_hourly": round(hourly_alloc, 2),
                "recommended_hourly": round(daily_budget / 24.0 * 0.8, 2),
                "reason": (
                    f"Campaign is overspending: ¥{spend_today:.2f} spent ({spend_pct:.1f}% of daily) "
                    f"vs expected ¥{pacing.get('expected_spend_by_now', 0):.2f}. "
                    f"Hard-cap hourly spend to prevent budget exhaustion."
                ),
                "urgency": "immediate",
            })
            adjustments.append({
                "type": "alert",
                "action": "set_spend_alert",
                "threshold_pct": 80,
                "reason": "Set alert at 80% daily budget to prevent overspend going undetected.",
                "urgency": "soon",
            })

        # Underspending
        elif pacing_status == "underspending":
            shortfall_pct = ((hours_elapsed / 24.0 * 100.0) - spend_pct) if hours_elapsed > 0 else 0
            if daily_budget > 0:
                adjustments.append({
                    "type": "accelerate_pacing",
                    "action": "increase_bids_or_expand_audience",
                    "reason": (
                        f"Campaign is underspending: only {spend_pct:.1f}% of daily budget used. "
                        f"Consider raising max CPC bid by 15-20% or expanding audience targeting "
                        f"to increase delivery volume. Remaining budget: ¥{pacing.get('budget_remaining', 0):.2f} "
                        f"over {hours_remaining}h."
                    ),
                    "urgency": "soon",
                })
            if hours_remaining <= 4 and float(pacing.get("budget_remaining", 0)) > daily_budget * 0.3:
                adjustments.append({
                    "type": "end_of_day_push",
                    "action": "aggressive_acceleration",
                    "reason": (
                        f"Only {hours_remaining} hours remaining with "
                        f"¥{pacing.get('budget_remaining', 0):.2f} unspent. "
                        "Consider aggressive bid increases (30-50%) for the final hours."
                    ),
                    "urgency": "immediate",
                })

        # On track
        elif pacing_status == "on_track":
            adjustments.append({
                "type": "maintain",
                "action": "no_change",
                "reason": (
                    f"Pacing is on track: {spend_pct:.1f}% of budget used at hour {hours_elapsed}. "
                    f"Continue current hourly allocation of ¥{hourly_alloc:.2f}/h."
                ),
                "urgency": "none",
            })

        # Add hourly allocation recommendations
        allocations = hourly.get("allocations", [])
        if allocations:
            next_hours = allocations[:3]
            adjustments.append({
                "type": "hourly_schedule",
                "action": "follow_allocation_schedule",
                "schedule": next_hours,
                "reason": (
                    f"Recommended hourly budget for the next {len(next_hours)} hours, "
                    f"weighted by time-of-day performance."
                ),
                "urgency": "none",
            })

        return adjustments, summary

    def _rule_based_redistribution(
        self,
        campaign: Campaign,
        pacing: dict[str, Any],
        redistribution: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract redistribution recommendations from budget_pacer output."""

        campaigns = redistribution.get("campaigns", [])
        if not campaigns:
            return []

        items: list[dict[str, Any]] = []
        daily_budget = float(campaign.daily_budget or 0)

        for entry in campaigns:
            platform = entry.get("platform", "unknown")
            current_spend = entry.get("current_spend", 0)
            recommended_spend = entry.get("recommended_spend", 0)
            delta = entry.get("delta", 0)
            roas = entry.get("roas", 0)

            if abs(delta) < daily_budget * 0.02:
                continue  # Insignificant change

            if delta < 0:
                items.append({
                    "platform": platform,
                    "action": "decrease",
                    "current_daily_spend": round(current_spend, 2),
                    "recommended_daily_spend": round(recommended_spend, 2),
                    "adjustment": round(delta, 2),
                    "roas": round(roas, 4),
                    "reason": (
                        f"Decrease {platform} budget by ¥{abs(delta):.2f} "
                        f"(ROAS: {roas:.2f}x). Underperformance relative to other platforms."
                    ),
                    "urgency": "soon" if delta < -daily_budget * 0.1 else "review",
                })
            else:
                items.append({
                    "platform": platform,
                    "action": "increase",
                    "current_daily_spend": round(current_spend, 2),
                    "recommended_daily_spend": round(recommended_spend, 2),
                    "adjustment": round(delta, 2),
                    "roas": round(roas, 4),
                    "reason": (
                        f"Increase {platform} budget by ¥{delta:.2f} "
                        f"(ROAS: {roas:.2f}x). Strong performance warrants higher investment."
                    ),
                    "urgency": "soon" if delta > daily_budget * 0.1 else "review",
                })

        return items

    # ── LLM enhancement ────────────────────────────────────────────────

    async def _llm_enhance(
        self, campaign: Campaign, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Use LLM to refine budget recommendations."""
        prompt = f"""You are a campaign budget optimization expert. Review the following pacing and redistribution analysis and refine the recommendations. Return a JSON object with:
- "pacing_adjustments": list of adjustment objects
- "redistribution": list of platform redistribution objects

Campaign: {campaign.name} (ID: {campaign.id})
Daily Budget: ¥{campaign.daily_budget}

Current analysis:
{json.dumps(context, indent=2, default=str)}

Return ONLY valid JSON, no markdown fences, no additional text."""
        try:
            reply = await self.llm.chat(prompt)
            if "{" in reply and "}" in reply:
                start = reply.index("{")
                end = reply.rindex("}") + 1
                return json.loads(reply[start:end])
        except Exception:
            pass
        return None

    @staticmethod
    def _error_result(campaign_id: int, message: str) -> dict[str, Any]:
        return {
            "campaign_id": campaign_id,
            "campaign_name": None,
            "pacing_adjustments": [],
            "redistribution": [],
            "current_pacing": {},
            "budget_summary": {},
            "error": message,
        }
