"""StrategyAgent — bid and budget strategy recommendations.

Analyzes historical performance vs targets and suggests specific bid strategy
changes, target CPA/ROAS adjustments, and budget reallocation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.performance import PerformanceMetric
from backend.models.enums import BidStrategy
from backend.llm.providers import get_provider, FallbackProvider, LLMProvider


class StrategyAgent:
    """Agent that recommends bid and budget strategy changes."""

    def __init__(self, llm: LLMProvider | None = None):
        self.llm = llm or get_provider("auto")

    async def recommend(self, campaign_id: int, db: AsyncSession) -> dict[str, Any]:
        """Generate bid and budget recommendations for the campaign.

        Returns:
            dict with keys: campaign_id, campaign_name, bid_adjustments[],
            budget_recommendations[], strategy_notes, context_used.
        """
        try:
            campaign = await self._get_campaign(campaign_id, db)
            if campaign is None:
                return self._error_result(campaign_id, "Campaign not found")

            # Gather performance data
            metrics = await self._gather_performance(campaign_id, db)
            platform_breakdown = await self._platform_breakdown(campaign_id, db)

            # Rule-based recommendations
            bid_adjustments, budget_recs, notes = self._rule_based_recommend(
                campaign, metrics, platform_breakdown
            )

            # Try LLM enhancement
            context = {
                "metrics": metrics,
                "platform_breakdown": platform_breakdown,
                "bid_adjustments": bid_adjustments,
                "budget_recommendations": budget_recs,
            }
            if not isinstance(self.llm, FallbackProvider):
                try:
                    llm_result = await self._llm_enhance(campaign, context)
                    if llm_result:
                        bid_adjustments = llm_result.get("bid_adjustments", bid_adjustments)
                        budget_recs = llm_result.get("budget_recommendations", budget_recs)
                        notes = llm_result.get("strategy_notes", notes)
                except Exception:
                    pass

            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "bid_adjustments": bid_adjustments,
                "budget_recommendations": budget_recs,
                "strategy_notes": notes,
                "context_used": context,
            }

        except Exception as exc:
            return {
                "campaign_id": campaign_id,
                "campaign_name": None,
                "bid_adjustments": [],
                "budget_recommendations": [],
                "strategy_notes": [f"Error: {exc}"],
                "context_used": None,
                "error": str(exc),
            }

    # ── helpers ────────────────────────────────────────────────────────

    async def _get_campaign(self, cid: int, db: AsyncSession) -> Campaign | None:
        result = await db.execute(select(Campaign).where(Campaign.id == cid))
        return result.scalar_one_or_none()

    async def _gather_performance(self, cid: int, db: AsyncSession) -> dict[str, Any]:
        """Aggregate metrics for the last 30 days and 7 days."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ranges = {
            "last_7_days": (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"),
            "last_30_days": (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
        }

        def _agg(date_from: str) -> dict[str, Any]:
            return select(
                func.coalesce(func.sum(PerformanceMetric.impressions), 0),
                func.coalesce(func.sum(PerformanceMetric.clicks), 0),
                func.coalesce(func.sum(PerformanceMetric.conversions), 0),
                func.coalesce(func.sum(PerformanceMetric.spend), 0.0),
                func.coalesce(func.sum(PerformanceMetric.revenue), 0.0),
            ).where(
                and_(
                    PerformanceMetric.campaign_id == cid,
                    PerformanceMetric.date >= date_from,
                    PerformanceMetric.date <= today,
                )
            )

        result = {}
        for label, date_from in ranges.items():
            row = (await db.execute(_agg(date_from))).one_or_none()
            if row:
                imp = int(row[0])
                clk = int(row[1])
                conv = int(row[2])
                sp = float(row[3])
                rev = float(row[4])
                result[label] = {
                    "impressions": imp, "clicks": clk, "conversions": conv,
                    "spend": round(sp, 2), "revenue": round(rev, 2),
                    "ctr": round(clk / imp * 100.0, 4) if imp > 0 else 0.0,
                    "cvr": round(conv / clk * 100.0, 4) if clk > 0 else 0.0,
                    "cpc": round(sp / clk, 4) if clk > 0 else 0.0,
                    "cpa": round(sp / conv, 4) if conv > 0 else 0.0,
                    "roas": round(rev / sp, 4) if sp > 0 else 0.0,
                }
            else:
                result[label] = {"impressions": 0, "clicks": 0, "conversions": 0,
                                 "spend": 0.0, "revenue": 0.0,
                                 "ctr": 0.0, "cvr": 0.0, "cpc": 0.0, "cpa": 0.0, "roas": 0.0}
        return result

    async def _platform_breakdown(self, cid: int, db: AsyncSession) -> list[dict[str, Any]]:
        """Per-platform performance for the last 30 days."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        thirty_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

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
                        PerformanceMetric.date >= thirty_ago,
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
                "platform": platform,
                "impressions": imp,
                "clicks": clk,
                "conversions": conv,
                "spend": round(sp, 2),
                "revenue": round(rev, 2),
                "ctr": round(clk / imp * 100.0, 4) if imp > 0 else 0.0,
                "cvr": round(conv / clk * 100.0, 4) if clk > 0 else 0.0,
                "cpa": round(sp / conv, 4) if conv > 0 else 0.0,
                "roas": round(rev / sp, 4) if sp > 0 else 0.0,
            })
        return result

    # ── rule-based recommendations ─────────────────────────────────────

    def _rule_based_recommend(
        self,
        campaign: Campaign,
        metrics: dict[str, Any],
        platforms: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        """Generate deterministic bid and budget recommendations."""

        m7 = metrics.get("last_7_days", {})
        m30 = metrics.get("last_30_days", {})

        bid_adjustments: list[dict[str, Any]] = []
        budget_recs: list[dict[str, Any]] = []
        notes: list[str] = []

        current_strategy = campaign.bid_strategy.value if campaign.bid_strategy else "unknown"
        target_cpa = float(campaign.target_cpa or 0)
        target_roas = float(campaign.target_roas or 0)
        actual_cpa = m30.get("cpa", 0)
        actual_roas = m30.get("roas", 0)
        daily_budget = float(campaign.daily_budget or 0)

        # ── Bid strategy recommendations ──
        if actual_roas >= 3.0 and current_strategy != BidStrategy.TARGET_ROAS.value:
            bid_adjustments.append({
                "type": "bid_strategy_change",
                "from": current_strategy,
                "to": BidStrategy.TARGET_ROAS.value,
                "target_roas": round(actual_roas * 0.85, 2),
                "reason": (
                    f"Campaign is delivering strong ROAS ({actual_roas:.2f}x). "
                    "Switching to Target ROAS bidding will scale spend efficiently "
                    "while protecting profitability."
                ),
                "confidence": "high",
            })
            notes.append("Strong ROAS performance supports Target ROAS bidding strategy.")

        elif actual_cpa > 0 and target_cpa > 0 and current_strategy != BidStrategy.TARGET_CPA.value:
            if actual_cpa > target_cpa * 1.2:
                bid_adjustments.append({
                    "type": "bid_strategy_change",
                    "from": current_strategy,
                    "to": BidStrategy.TARGET_CPA.value,
                    "target_cpa": round(target_cpa * 0.9, 2),
                    "reason": (
                        f"CPA (¥{actual_cpa:.2f}) exceeds target (¥{target_cpa:.2f}). "
                        "Switching to Target CPA with a tighter target will enforce cost controls."
                    ),
                    "confidence": "high",
                })
                notes.append("CPA over target — recommend switching to Target CPA bidding.")
            elif actual_cpa < target_cpa * 0.8:
                bid_adjustments.append({
                    "type": "target_adjustment",
                    "parameter": "target_cpa",
                    "from": target_cpa,
                    "to": round(actual_cpa * 1.1, 2),
                    "reason": (
                        f"CPA (¥{actual_cpa:.2f}) is well below target (¥{target_cpa:.2f}). "
                        "Raising target CPA can increase delivery volume."
                    ),
                    "confidence": "medium",
                })

        # CPC-based adjustments
        cpc = m30.get("cpc", 0)
        max_cpc = float(campaign.max_cpc or 0)
        if max_cpc > 0 and cpc > max_cpc * 0.9:
            bid_adjustments.append({
                "type": "max_cpc_adjustment",
                "parameter": "max_cpc",
                "from": max_cpc,
                "to": round(cpc * 1.1, 2),
                "reason": (
                    f"CPC (¥{cpc:.4f}) is near max CPC cap (¥{max_cpc:.4f}), "
                    "limiting delivery. Consider raising the cap."
                ),
                "confidence": "medium",
            })

        # ── Budget recommendations ──
        roas_7 = m7.get("roas", 0)
        roas_30 = m30.get("roas", 0)

        if roas_7 > roas_30 * 1.3:
            budget_recs.append({
                "type": "increase_budget",
                "current": daily_budget,
                "recommended": round(daily_budget * 1.2, 2),
                "reason": (
                    f"7-day ROAS ({roas_7:.2f}x) is trending well above 30-day ({roas_30:.2f}x). "
                    "Increasing budget by 20% can capture additional profitable volume."
                ),
                "urgency": "soon",
            })
            notes.append("Positive ROAS trend supports budget increase.")

        elif roas_7 < roas_30 * 0.7 and roas_30 > 1.0:
            budget_recs.append({
                "type": "decrease_budget",
                "current": daily_budget,
                "recommended": round(daily_budget * 0.8, 2),
                "reason": (
                    f"7-day ROAS ({roas_7:.2f}x) is declining sharply vs 30-day ({roas_30:.2f}x). "
                    "Reduce budget temporarily until performance stabilizes."
                ),
                "urgency": "immediate",
            })
            notes.append("Declining ROAS trend — recommend budget reduction.")

        # Platform redistribution
        if len(platforms) >= 2:
            sorted_platforms = sorted(platforms, key=lambda p: p.get("roas", 0), reverse=True)
            best = sorted_platforms[0]
            worst = sorted_platforms[-1]
            roas_gap = best.get("roas", 0) - worst.get("roas", 0)

            if roas_gap > 1.0:
                budget_recs.append({
                    "type": "redistribute_budget",
                    "from_platform": worst["platform"],
                    "to_platform": best["platform"],
                    "amount": round(daily_budget * 0.15, 2),
                    "reason": (
                        f"ROAS gap of {roas_gap:.2f}x between {best['platform']} "
                        f"({best['roas']:.2f}x) and {worst['platform']} ({worst['roas']:.2f}x). "
                        "Shift 15% of budget to the higher-performing platform."
                    ),
                    "urgency": "soon",
                })
                notes.append(f"Significant ROAS gap between platforms — recommend redistribution.")

        # Default notes if none generated
        if not notes:
            notes = [
                "Campaign performance is stable. No immediate strategy changes required.",
                "Continue monitoring ROAS and CPA trends for early signals.",
            ]

        return bid_adjustments, budget_recs, notes

    # ── LLM enhancement ────────────────────────────────────────────────

    async def _llm_enhance(
        self, campaign: Campaign, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Use LLM to refine recommendations when available."""
        prompt = f"""You are a campaign strategy expert. Refine the following bid and budget recommendations for this campaign. Return a JSON object with:
- "bid_adjustments": list of strategy change objects (same format as input)
- "budget_recommendations": list of budget change objects
- "strategy_notes": list of strategic insights

Campaign: {campaign.name} (ID: {campaign.id})
Bid Strategy: {campaign.bid_strategy.value if campaign.bid_strategy else 'unknown'}
Target CPA: {campaign.target_cpa or 'N/A'}
Target ROAS: {campaign.target_roas or 'N/A'}
Daily Budget: ¥{campaign.daily_budget}

Current context and rule-based recommendations:
{json.dumps(context, indent=2)}

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
            "bid_adjustments": [],
            "budget_recommendations": [],
            "strategy_notes": [f"Error: {message}"],
            "context_used": None,
            "error": message,
        }
