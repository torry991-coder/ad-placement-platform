"""AuditAgent — comprehensive campaign health audit.

Analyzes budget utilization, CTR/CVR trends, pacing status, and alert history.
Produces a structured audit with an overall score, issues, and recommendations.
Works with or without LLM — the rule-based fallback performs deterministic
metric analysis.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.performance import PerformanceMetric
from backend.models.budget import BudgetLog
from backend.models.alert import AlertRule
from backend.llm.providers import get_provider, FallbackProvider, LLMProvider


class AuditAgent:
    """Agent that performs a full campaign audit and returns a scored report."""

    def __init__(self, llm: LLMProvider | None = None):
        self.llm = llm or get_provider("auto")

    async def audit(self, campaign_id: int, db: AsyncSession) -> dict[str, Any]:
        """Run a full audit on the specified campaign.

        Returns:
            dict with keys: campaign_id, campaign_name, overall_score (0-100),
            issues[], recommendations[], metrics_summary, audit_timestamp.
        """
        try:
            # 1. Fetch campaign
            campaign = await self._get_campaign(campaign_id, db)
            if campaign is None:
                return self._error_result(campaign_id, "Campaign not found")

            # 2. Gather metrics
            metrics = await self._gather_metrics(campaign_id, db)
            pacing = await self._get_pacing_status(campaign_id, db)
            alerts = await self._get_alert_history(campaign_id, db)

            # 3. Rule-based analysis (always performed)
            issues, recommendations, score = self._rule_based_analysis(
                campaign, metrics, pacing, alerts
            )

            # 4. Try LLM enhancement if available (not fallback)
            if not isinstance(self.llm, FallbackProvider):
                try:
                    llm_insights = await self._llm_enhance(
                        campaign, metrics, pacing, alerts
                    )
                    if llm_insights:
                        issues.extend(llm_insights.get("issues", []))
                        recommendations.extend(llm_insights.get("recommendations", []))
                        # Blend LLM score with rule-based (weighted average)
                        llm_score = llm_insights.get("overall_score", score)
                        score = round(score * 0.6 + llm_score * 0.4)
                except Exception:
                    pass  # LLM enhancement failed, keep rule-based result

            # 5. Build final result
            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "overall_score": max(0, min(100, score)),
                "issues": issues,
                "recommendations": recommendations,
                "metrics_summary": metrics,
                "pacing_status": pacing.get("pacing_status", "unknown"),
                "alert_count": len(alerts),
                "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as exc:
            return {
                "campaign_id": campaign_id,
                "campaign_name": None,
                "overall_score": 0,
                "issues": [f"Audit failed: {exc}"],
                "recommendations": [],
                "metrics_summary": {},
                "pacing_status": "error",
                "alert_count": 0,
                "audit_timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            }

    # ── helpers ────────────────────────────────────────────────────────

    async def _get_campaign(self, cid: int, db: AsyncSession) -> Campaign | None:
        result = await db.execute(select(Campaign).where(Campaign.id == cid))
        return result.scalar_one_or_none()

    async def _gather_metrics(self, cid: int, db: AsyncSession) -> dict[str, Any]:
        """Aggregate performance metrics for the last 30 days."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        # Last 30 days aggregate
        row = (
            await db.execute(
                select(
                    func.sum(PerformanceMetric.impressions),
                    func.sum(PerformanceMetric.clicks),
                    func.sum(PerformanceMetric.conversions),
                    func.sum(PerformanceMetric.spend),
                    func.sum(PerformanceMetric.revenue),
                ).where(
                    and_(
                        PerformanceMetric.campaign_id == cid,
                        PerformanceMetric.date >= thirty_days_ago,
                        PerformanceMetric.date <= today,
                    )
                )
            )
        ).one_or_none()

        # Last 7 days for trend
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        row7 = (
            await db.execute(
                select(
                    func.sum(PerformanceMetric.impressions),
                    func.sum(PerformanceMetric.clicks),
                    func.sum(PerformanceMetric.conversions),
                    func.sum(PerformanceMetric.spend),
                    func.sum(PerformanceMetric.revenue),
                ).where(
                    and_(
                        PerformanceMetric.campaign_id == cid,
                        PerformanceMetric.date >= seven_days_ago,
                        PerformanceMetric.date <= today,
                    )
                )
            )
        ).one_or_none()

        def _extract(r) -> dict[str, float]:
            if r is None:
                return {"impressions": 0, "clicks": 0, "conversions": 0, "spend": 0.0, "revenue": 0.0}
            imp = int(r[0] or 0)
            clk = int(r[1] or 0)
            conv = int(r[2] or 0)
            sp = float(r[3] or 0.0)
            rev = float(r[4] or 0.0)
            ctr = round(clk / imp * 100.0, 4) if imp > 0 else 0.0
            cvr = round(conv / clk * 100.0, 4) if clk > 0 else 0.0
            cpc = round(sp / clk, 4) if clk > 0 else 0.0
            cpa = round(sp / conv, 4) if conv > 0 else 0.0
            roas = round(rev / sp, 4) if sp > 0 else 0.0
            return {
                "impressions": imp, "clicks": clk, "conversions": conv,
                "spend": round(sp, 2), "revenue": round(rev, 2),
                "ctr": ctr, "cvr": cvr, "cpc": cpc, "cpa": cpa, "roas": roas,
            }

        m30 = _extract(row)
        m7 = _extract(row7)

        # Compute trends (7-day vs projected 30-day)
        def _trend(m7_val: float, m30_val: float) -> str:
            if m30_val <= 0:
                return "flat"
            ratio = (m7_val * 4.28) / m30_val  # ~30/7
            if ratio > 1.15:
                return "up"
            if ratio < 0.85:
                return "down"
            return "flat"

        return {
            "last_30_days": m30,
            "last_7_days": m7,
            "ctr_trend": _trend(m7["ctr"], m30["ctr"]),
            "cvr_trend": _trend(m7["cvr"], m30["cvr"]),
            "roas_trend": _trend(m7["roas"], m30["roas"]),
            "spend_trend": _trend(m7["spend"], m30["spend"]),
        }

    async def _get_pacing_status(self, cid: int, db: AsyncSession) -> dict[str, Any]:
        """Get pacing status via budget_pacer service."""
        try:
            from backend.services.budget_pacer import get_pacing_status
            return await get_pacing_status(cid, db)
        except Exception:
            return {"pacing_status": "unknown", "error": "budget_pacer unavailable"}

    async def _get_alert_history(self, cid: int, db: AsyncSession) -> list[dict[str, Any]]:
        """Fetch recent alerts for this campaign."""
        try:
            result = await db.execute(
                select(AlertRule).where(
                    and_(
                        AlertRule.scope_id == cid,
                        AlertRule.scope_type == "campaign",
                    )
                ).limit(10)
            )
            alerts = result.scalars().all()
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "severity": a.severity.value if a.severity else "unknown",
                    "trigger_count": a.trigger_count or 0,
                    "last_triggered": a.last_triggered_at.isoformat() if a.last_triggered_at else None,
                }
                for a in alerts
            ]
        except Exception:
            return []

    # ── rule-based analysis ────────────────────────────────────────────

    def _rule_based_analysis(
        self,
        campaign: Campaign,
        metrics: dict[str, Any],
        pacing: dict[str, Any],
        alerts: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        """Deterministic analysis — always works without LLM."""

        m = metrics.get("last_30_days", {})
        ct = metrics.get("ctr_trend", "flat")
        cv = metrics.get("cvr_trend", "flat")
        rs = metrics.get("roas_trend", "flat")

        issues: list[dict[str, Any]] = []
        recommendations: list[dict[str, Any]] = []
        score = 75  # Start from a neutral baseline

        # ── Budget utilization ──
        daily = float(campaign.daily_budget or 0)
        spend_7d = float(metrics.get("last_7_days", {}).get("spend", 0))
        avg_daily_spend = spend_7d / 7.0 if spend_7d > 0 else 0
        utilization = (avg_daily_spend / daily * 100.0) if daily > 0 else 0

        if utilization > 100:
            issues.append({
                "severity": "high",
                "category": "budget",
                "detail": (
                    f"Campaign '{campaign.name}' is overspending: "
                    f"avg daily spend ¥{avg_daily_spend:.2f} exceeds daily budget ¥{daily:.2f} "
                    f"({utilization:.1f}% utilization)."
                ),
                "metric": "budget_utilization",
                "value": round(utilization, 1),
            })
            recommendations.append({
                "category": "budget",
                "action": "reduce_daily_budget",
                "detail": f"Reduce daily budget from ¥{daily:.2f} to ¥{daily * 0.8:.2f} or set hard cap.",
                "urgency": "immediate",
            })
            score -= 20
        elif utilization < 30:
            issues.append({
                "severity": "medium",
                "category": "budget",
                "detail": (
                    f"Campaign '{campaign.name}' is severely underspending: "
                    f"only {utilization:.1f}% of daily budget utilized."
                ),
                "metric": "budget_utilization",
                "value": round(utilization, 1),
            })
            recommendations.append({
                "category": "budget",
                "action": "review_targeting_or_bids",
                "detail": "Daily budget is underutilized. Check audience size, bid floors, or ad approval status.",
                "urgency": "review",
            })
            score -= 10

        # ── Pacing ──
        pacing_status = pacing.get("pacing_status", "unknown")
        if pacing_status == "overspending":
            issues.append({
                "severity": "high",
                "category": "pacing",
                "detail": f"Pacing status is '{pacing_status}' — spend is ahead of schedule.",
                "metric": "pacing_delta",
                "value": pacing.get("pacing_delta", 0),
            })
            recommendations.append({
                "category": "pacing",
                "action": "slow_pacing",
                "detail": "Enable auto-pacing guardrails to smooth hourly spend distribution.",
                "urgency": "immediate",
            })
            score -= 15
        elif pacing_status == "underspending":
            issues.append({
                "severity": "low",
                "category": "pacing",
                "detail": f"Pacing status is '{pacing_status}' — spend is behind schedule.",
                "metric": "pacing_delta",
                "value": pacing.get("pacing_delta", 0),
            })
            recommendations.append({
                "category": "pacing",
                "action": "accelerate_pacing",
                "detail": "Consider relaxing bid constraints or expanding audience to catch up.",
                "urgency": "review",
            })
            score -= 5

        # ── CTR ──
        ctr = m.get("ctr", 0)
        if 0 < ctr < 1.0:
            issues.append({
                "severity": "high",
                "category": "ctr",
                "detail": f"CTR is very low ({ctr:.4f}%). Creative refresh or audience refinement needed.",
                "metric": "ctr",
                "value": ctr,
            })
            recommendations.append({
                "category": "ctr",
                "action": "refresh_creatives",
                "detail": "Rotate creatives with fatigue > 60 and A/B test 3 new headlines.",
                "urgency": "soon",
            })
            score -= 15
        elif 1.0 <= ctr < 2.0:
            issues.append({
                "severity": "medium",
                "category": "ctr",
                "detail": f"CTR is below average ({ctr:.4f}%). Consider headline and audience testing.",
                "metric": "ctr",
                "value": ctr,
            })
            recommendations.append({
                "category": "ctr",
                "action": "ab_test_headlines",
                "detail": "Set up an A/B test with 3 headline variants targeting top-performing audience segments.",
                "urgency": "soon",
            })
            score -= 5
        if ct == "down":
            issues.append({
                "severity": "medium",
                "category": "ctr_trend",
                "detail": "CTR is trending downward over the last 7 days.",
                "metric": "ctr_trend",
                "value": "down",
            })
            score -= 5

        # ── CVR ──
        cvr = m.get("cvr", 0)
        if 0 < cvr < 1.0:
            issues.append({
                "severity": "high",
                "category": "cvr",
                "detail": f"CVR is very low ({cvr:.4f}%). Landing page or offer optimization needed.",
                "metric": "cvr",
                "value": cvr,
            })
            recommendations.append({
                "category": "cvr",
                "action": "optimize_landing_page",
                "detail": "Audit landing page: load time, message match, and conversion flow.",
                "urgency": "soon",
            })
            score -= 15
        if cv == "down":
            issues.append({
                "severity": "medium",
                "category": "cvr_trend",
                "detail": "CVR is trending downward over the last 7 days.",
                "metric": "cvr_trend",
                "value": "down",
            })
            score -= 5

        # ── ROAS ──
        roas = m.get("roas", 0)
        if roas < 1.0 and m.get("spend", 0) > 0:
            issues.append({
                "severity": "critical",
                "category": "roas",
                "detail": f"ROAS is below 1.0 ({roas:.4f}) — campaign is losing money.",
                "metric": "roas",
                "value": roas,
            })
            recommendations.append({
                "category": "roas",
                "action": "pause_or_restructure",
                "detail": "Pause campaign or switch to Target ROAS bidding with target ≥ 1.5.",
                "urgency": "immediate",
            })
            score -= 25
        elif 1.0 <= roas < 2.0:
            issues.append({
                "severity": "medium",
                "category": "roas",
                "detail": f"ROAS is marginal ({roas:.4f}). Optimization needed to reach profitability.",
                "metric": "roas",
                "value": roas,
            })
            score -= 5
        if rs == "down":
            issues.append({
                "severity": "medium",
                "category": "roas_trend",
                "detail": "ROAS is trending downward over the last 7 days.",
                "metric": "roas_trend",
                "value": "down",
            })
            score -= 5

        # ── Alerts ──
        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        if critical_alerts:
            issues.append({
                "severity": "critical",
                "category": "alerts",
                "detail": f"{len(critical_alerts)} critical alert(s) have been triggered for this campaign.",
                "metric": "critical_alert_count",
                "value": len(critical_alerts),
            })
            score -= 10 * len(critical_alerts)

        # ── CPA ──
        cpa = m.get("cpa", 0)
        target_cpa = float(campaign.target_cpa or 0)
        if target_cpa > 0 and cpa > target_cpa * 1.3:
            issues.append({
                "severity": "high",
                "category": "cpa",
                "detail": f"CPA (¥{cpa:.2f}) exceeds target CPA (¥{target_cpa:.2f}) by {((cpa/target_cpa)-1)*100:.0f}%.",
                "metric": "cpa",
                "value": cpa,
            })
            recommendations.append({
                "category": "cpa",
                "action": "tighten_targeting_or_bids",
                "detail": f"CPA is {((cpa/target_cpa)-1)*100:.0f}% above target. Review audience quality and bid strategy.",
                "urgency": "soon",
            })
            score -= 10

        # Clamp score
        score = max(0, min(100, score))

        return issues, recommendations, score

    # ── LLM enhancement ────────────────────────────────────────────────

    async def _llm_enhance(
        self,
        campaign: Campaign,
        metrics: dict[str, Any],
        pacing: dict[str, Any],
        alerts: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Use LLM to generate additional insights when available."""
        prompt = f"""You are an advertising campaign auditor. Analyze the following campaign data and return a JSON object with:
- "overall_score": integer 0-100
- "issues": list of {{severity, category, detail}} objects
- "recommendations": list of {{category, action, detail, urgency}} objects

Campaign: {campaign.name} (ID: {campaign.id})
Status: {campaign.status.value if campaign.status else 'unknown'}
Daily Budget: ¥{campaign.daily_budget}
Bid Strategy: {campaign.bid_strategy.value if campaign.bid_strategy else 'unknown'}
Target CPA: {campaign.target_cpa or 'N/A'}
Target ROAS: {campaign.target_roas or 'N/A'}

30-day Metrics: {json.dumps(metrics.get('last_30_days', {}))}
7-day Metrics: {json.dumps(metrics.get('last_7_days', {}))}
CTR Trend: {metrics.get('ctr_trend')}
CVR Trend: {metrics.get('cvr_trend')}
ROAS Trend: {metrics.get('roas_trend')}

Pacing: {json.dumps(pacing)}
Active Alerts: {json.dumps(alerts)}

Return ONLY valid JSON, no markdown fences, no additional text."""
        try:
            reply = await self.llm.chat(prompt)
            # Extract JSON from reply
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
            "overall_score": 0,
            "issues": [{"severity": "error", "category": "system", "detail": message}],
            "recommendations": [],
            "metrics_summary": {},
            "pacing_status": "error",
            "alert_count": 0,
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "error": message,
        }
