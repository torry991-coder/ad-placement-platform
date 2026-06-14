"""ReportAgent — generates executive summary reports in Markdown.

Produces a campaign performance report with KPIs, trends, anomalies,
and recommendations. Falls back to a template-based report when no LLM
is available.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.performance import PerformanceMetric
from backend.models.alert import AlertRule
from backend.llm.providers import get_provider, FallbackProvider, LLMProvider


class ReportAgent:
    """Agent that generates executive-summary Markdown reports."""

    def __init__(self, llm: LLMProvider | None = None):
        self.llm = llm or get_provider("auto")

    async def summarize(
        self,
        campaign_id: int,
        db: AsyncSession,
        date_range: tuple[str, str] | None = None,
    ) -> str:
        """Generate a Markdown executive summary of campaign performance.

        Args:
            campaign_id: Campaign to report on.
            db: Async DB session.
            date_range: Optional (date_from, date_to) tuple; defaults to last 30 days.

        Returns:
            Markdown string with the full report.
        """
        try:
            # Resolve date range
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if date_range is None:
                date_from = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
                date_to = today
            else:
                date_from, date_to = date_range

            # Fetch data
            campaign = await self._get_campaign(campaign_id, db)
            metrics = await self._gather_metrics(campaign_id, db, date_from, date_to)
            trends = await self._compute_trends(campaign_id, db, date_from, date_to)
            anomalies = await self._detect_anomalies(campaign_id, db, date_from, date_to)
            alerts = await self._get_alerts(campaign_id, db)

            context = {
                "campaign": {
                    "id": campaign.id if campaign else campaign_id,
                    "name": campaign.name if campaign else f"Campaign #{campaign_id}",
                    "status": campaign.status.value if campaign and campaign.status else "unknown",
                    "daily_budget": campaign.daily_budget if campaign else 0,
                    "bid_strategy": campaign.bid_strategy.value if campaign and campaign.bid_strategy else "unknown",
                    "target_cpa": campaign.target_cpa if campaign else None,
                    "target_roas": campaign.target_roas if campaign else None,
                },
                "date_range": {"from": date_from, "to": date_to},
                "metrics": metrics,
                "trends": trends,
                "anomalies": anomalies,
                "alerts": alerts,
            }

            # Try LLM
            if not isinstance(self.llm, FallbackProvider):
                try:
                    report = await self._llm_report(context)
                    if report and len(report) > 100:
                        return report
                except Exception:
                    pass

            # Fallback to template
            return self._template_report(context)

        except Exception as exc:
            return self._error_report(campaign_id, date_range, str(exc))

    # ── data gathering ─────────────────────────────────────────────────

    async def _get_campaign(self, cid: int, db: AsyncSession) -> Campaign | None:
        result = await db.execute(select(Campaign).where(Campaign.id == cid))
        return result.scalar_one_or_none()

    async def _gather_metrics(
        self, cid: int, db: AsyncSession, date_from: str, date_to: str
    ) -> dict[str, Any]:
        """Aggregate all KPIs for the date range."""
        row = (
            await db.execute(
                select(
                    func.coalesce(func.sum(PerformanceMetric.impressions), 0),
                    func.coalesce(func.sum(PerformanceMetric.clicks), 0),
                    func.coalesce(func.sum(PerformanceMetric.conversions), 0),
                    func.coalesce(func.sum(PerformanceMetric.spend), 0.0),
                    func.coalesce(func.sum(PerformanceMetric.revenue), 0.0),
                ).where(
                    and_(
                        PerformanceMetric.campaign_id == cid,
                        PerformanceMetric.date >= date_from,
                        PerformanceMetric.date <= date_to,
                    )
                )
            )
        ).one_or_none()

        if row is None or (int(row[0] or 0) == 0 and float(row[3] or 0) == 0):
            return {
                "impressions": 0, "clicks": 0, "conversions": 0,
                "spend": 0.0, "revenue": 0.0,
                "ctr": 0.0, "cvr": 0.0, "cpc": 0.0, "cpa": 0.0, "roas": 0.0,
            }

        imp = int(row[0])
        clk = int(row[1])
        conv = int(row[2])
        sp = float(row[3])
        rev = float(row[4])

        return {
            "impressions": imp,
            "clicks": clk,
            "conversions": conv,
            "spend": round(sp, 2),
            "revenue": round(rev, 2),
            "ctr": round(clk / imp * 100.0, 4) if imp > 0 else 0.0,
            "cvr": round(conv / clk * 100.0, 4) if clk > 0 else 0.0,
            "cpc": round(sp / clk, 4) if clk > 0 else 0.0,
            "cpa": round(sp / conv, 4) if conv > 0 else 0.0,
            "roas": round(rev / sp, 4) if sp > 0 else 0.0,
        }

    async def _compute_trends(
        self, cid: int, db: AsyncSession, date_from: str, date_to: str
    ) -> dict[str, Any]:
        """Compute week-over-week trends for key metrics."""
        # Split the range in half for trend comparison
        from datetime import datetime as dt
        try:
            start = dt.strptime(date_from, "%Y-%m-%d")
            end = dt.strptime(date_to, "%Y-%m-%d")
            mid = start + (end - start) / 2
            mid_str = mid.strftime("%Y-%m-%d")
        except Exception:
            mid_str = date_from

        # Use separate async queries for each half
        first_half = await self._gather_metrics(cid, db, date_from, mid_str)
        second_half = await self._gather_metrics(cid, db, mid_str, date_to)

        def _pct_change(old: float, new: float) -> float:
            if old == 0:
                return 0.0 if new == 0 else 100.0
            return round((new - old) / abs(old) * 100.0, 1)

        return {
            "ctr": {
                "first_half": first_half.get("ctr", 0),
                "second_half": second_half.get("ctr", 0),
                "change_pct": _pct_change(first_half.get("ctr", 0), second_half.get("ctr", 0)),
            },
            "cvr": {
                "first_half": first_half.get("cvr", 0),
                "second_half": second_half.get("cvr", 0),
                "change_pct": _pct_change(first_half.get("cvr", 0), second_half.get("cvr", 0)),
            },
            "roas": {
                "first_half": first_half.get("roas", 0),
                "second_half": second_half.get("roas", 0),
                "change_pct": _pct_change(first_half.get("roas", 0), second_half.get("roas", 0)),
            },
            "spend": {
                "first_half": first_half.get("spend", 0),
                "second_half": second_half.get("spend", 0),
                "change_pct": _pct_change(first_half.get("spend", 0), second_half.get("spend", 0)),
            },
        }

    async def _detect_anomalies(
        self, cid: int, db: AsyncSession, date_from: str, date_to: str
    ) -> list[dict[str, Any]]:
        """Detect anomalous metric values in the date range."""
        # Fetch daily aggregates
        rows = (
            await db.execute(
                select(
                    PerformanceMetric.date,
                    func.sum(PerformanceMetric.impressions),
                    func.sum(PerformanceMetric.clicks),
                    func.sum(PerformanceMetric.conversions),
                    func.sum(PerformanceMetric.spend),
                    func.sum(PerformanceMetric.revenue),
                )
                .where(
                    and_(
                        PerformanceMetric.campaign_id == cid,
                        PerformanceMetric.date >= date_from,
                        PerformanceMetric.date <= date_to,
                    )
                )
                .group_by(PerformanceMetric.date)
                .order_by(PerformanceMetric.date.asc())
            )
        ).all()

        if len(rows) < 3:
            return []

        # Compute daily-derived metrics
        daily: list[dict[str, Any]] = []
        for row in rows:
            imp = int(row[1] or 0)
            clk = int(row[2] or 0)
            conv = int(row[3] or 0)
            sp = float(row[4] or 0.0)
            rev = float(row[5] or 0.0)
            daily.append({
                "date": row[0],
                "impressions": imp,
                "clicks": clk,
                "conversions": conv,
                "spend": round(sp, 2),
                "revenue": round(rev, 2),
                "ctr": round(clk / imp * 100.0, 4) if imp > 0 else 0.0,
                "cvr": round(conv / clk * 100.0, 4) if clk > 0 else 0.0,
                "roas": round(rev / sp, 4) if sp > 0 else 0.0,
            })

        # Compute mean and std for key metrics
        metrics_to_check = ["ctr", "cvr", "roas", "spend"]
        anomalies: list[dict[str, Any]] = []

        for metric in metrics_to_check:
            values = [d[metric] for d in daily]
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = variance ** 0.5

            if std == 0:
                continue

            for d in daily:
                val = d[metric]
                z_score = (val - mean) / std
                if abs(z_score) > 2.0:  # 2-sigma threshold
                    anomalies.append({
                        "date": d["date"],
                        "metric": metric,
                        "value": val,
                        "expected": round(mean, 4),
                        "z_score": round(z_score, 2),
                        "direction": "spike" if z_score > 0 else "drop",
                    })

        # Deduplicate and limit
        seen_pairs = set()
        deduped = []
        for a in anomalies:
            pair = (a["date"], a["metric"])
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                deduped.append(a)

        return sorted(deduped, key=lambda a: abs(a["z_score"]), reverse=True)[:10]

    async def _get_alerts(self, cid: int, db: AsyncSession) -> list[dict[str, Any]]:
        """Fetch recent alerts."""
        try:
            result = await db.execute(
                select(AlertRule).where(
                    and_(
                        AlertRule.scope_id == cid,
                        AlertRule.scope_type == "campaign",
                        AlertRule.trigger_count > 0,
                    )
                ).limit(5)
            )
            alerts = result.scalars().all()
            return [
                {
                    "name": a.name,
                    "severity": a.severity.value if a.severity else "info",
                    "trigger_count": a.trigger_count or 0,
                }
                for a in alerts
            ]
        except Exception:
            return []

    # ── template-based report ──────────────────────────────────────────

    def _template_report(self, context: dict[str, Any]) -> str:
        """Generate a structured Markdown report from data."""
        c = context["campaign"]
        m = context["metrics"]
        t = context["trends"]
        a = context["anomalies"]
        alerts = context["alerts"]
        dr = context["date_range"]

        # Trend emojis
        def trend_icon(change: float) -> str:
            if change > 10:
                return "🟢 ↑"
            if change > 0:
                return "🟢 ↗"
            if change == 0:
                return "⚪ →"
            if change > -10:
                return "🟡 ↘"
            return "🔴 ↓"

        def severity_emoji(sev: str) -> str:
            return {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(sev, "⚪")

        # Build report sections
        lines: list[str] = []

        # ── Header ──
        lines.append(f"# 📊 Campaign Performance Report")
        lines.append(f"")
        lines.append(f"**Campaign:** {c['name']} (ID: {c['id']})  ")
        lines.append(f"**Period:** {dr['from']} → {dr['to']}  ")
        lines.append(f"**Status:** {c['status']} | **Bid Strategy:** {c['bid_strategy']}  ")
        lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ── Executive Summary ──
        lines.append("## 📋 Executive Summary")
        lines.append("")

        roas = m.get("roas", 0)
        if roas >= 3.0:
            roas_note = "Excellent performance — strongly profitable."
        elif roas >= 1.5:
            roas_note = "Good performance — profitable with room to grow."
        elif roas >= 1.0:
            roas_note = "Breakeven performance — optimization needed to reach profitability."
        else:
            roas_note = "⚠️ Below breakeven — urgent optimization required."

        cpa = m.get("cpa", 0)
        target_cpa = c.get("target_cpa") or 0
        if target_cpa > 0:
            if cpa > target_cpa * 1.2:
                cpa_note = f"CPA (¥{cpa:.2f}) exceeds target (¥{target_cpa:.2f}) — cost controls needed."
            elif cpa < target_cpa * 0.8:
                cpa_note = f"CPA (¥{cpa:.2f}) is well below target (¥{target_cpa:.2f}) — room to scale."
            else:
                cpa_note = f"CPA (¥{cpa:.2f}) is on target (¥{target_cpa:.2f})."
        else:
            cpa_note = f"CPA: ¥{cpa:.2f}"

        lines.append(f"During the reporting period, this campaign generated **{m.get('impressions', 0):,}** impressions, "
                     f"**{m.get('clicks', 0):,}** clicks, and **{m.get('conversions', 0):,}** conversions. ")
        lines.append(f"Total spend was **¥{m.get('spend', 0):,.2f}** with revenue of **¥{m.get('revenue', 0):,.2f}** "
                     f"(ROAS: **{roas:.2f}x**).")
        lines.append("")
        lines.append(f"{roas_note} {cpa_note}")
        lines.append("")

        # ── KPI Table ──
        lines.append("## 📈 Key Performance Indicators")
        lines.append("")
        lines.append("| Metric | Value | 1st Half | 2nd Half | Change |")
        lines.append("|--------|-------|----------|----------|--------|")
        for label, key in [("Impressions", "impressions"), ("Clicks", "clicks"),
                           ("Conversions", "conversions"), ("Spend", "spend"),
                           ("Revenue", "revenue")]:
            val = m.get(key, 0)
            if key in ("spend", "revenue"):
                lines.append(f"| {label} | ¥{val:,.2f} | - | - | - |")
            else:
                lines.append(f"| {label} | {val:,} | - | - | - |")

        # Derived metrics with trends
        for label, key in [("CTR", "ctr"), ("CVR", "cvr"), ("CPC", "cpc"),
                           ("CPA", "cpa"), ("ROAS", "roas")]:
            val = m.get(key, 0)
            trend = t.get(key, {})
            if key in ("ctr", "cvr"):
                lines.append(
                    f"| {label} | {val:.2f}% | {trend.get('first_half', 0):.2f}% | "
                    f"{trend.get('second_half', 0):.2f}% | "
                    f"{trend_icon(trend.get('change_pct', 0))} {trend.get('change_pct', 0):+.1f}% |"
                )
            elif key in ("cpc", "cpa", "roas"):
                suffix = "x" if key == "roas" else ""
                lines.append(
                    f"| {label} | {val:.2f}{suffix} | {trend.get('first_half', 0):.2f}{suffix} | "
                    f"{trend.get('second_half', 0):.2f}{suffix} | "
                    f"{trend_icon(trend.get('change_pct', 0))} {trend.get('change_pct', 0):+.1f}% |"
                )
        lines.append("")

        # ── Anomalies ──
        lines.append("## 🔍 Detected Anomalies")
        lines.append("")
        if a:
            lines.append("| Date | Metric | Value | Expected | Z-Score | Direction |")
            lines.append("|------|--------|-------|----------|---------|-----------|")
            for anom in a[:8]:
                lines.append(
                    f"| {anom['date']} | {anom['metric']} | {anom['value']} | "
                    f"{anom['expected']} | {anom['z_score']:+.2f} | "
                    f"{'⚠️ Spike' if anom['direction'] == 'spike' else '📉 Drop'} |"
                )
            lines.append("")
            # Summary
            spikes = sum(1 for x in a if x["direction"] == "spike")
            drops = sum(1 for x in a if x["direction"] == "drop")
            lines.append(f"**Summary:** {spikes} spike(s), {drops} drop(s) detected across the reporting period.")
        else:
            lines.append("No significant anomalies detected during this period. ✅")
        lines.append("")

        # ── Alerts ──
        lines.append("## 🚨 Active Alerts")
        lines.append("")
        if alerts:
            for alert in alerts:
                lines.append(
                    f"- {severity_emoji(alert['severity'])} **{alert['name']}** "
                    f"(triggered {alert['trigger_count']}×) — {alert['severity']}"
                )
        else:
            lines.append("No active alerts. ✅")
        lines.append("")

        # ── Recommendations ──
        lines.append("## 💡 Recommendations")
        lines.append("")

        recs = self._generate_template_recommendations(c, m, t, a)

        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. **{rec['title']}**  ")
            lines.append(f"   {rec['detail']}")
            lines.append("")

        lines.append("---")
        lines.append(f"*Report generated by Ad Platform Agent at "
                     f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC*")
        lines.append("")

        return "\n".join(lines)

    def _generate_template_recommendations(
        self,
        campaign: dict[str, Any],
        metrics: dict[str, Any],
        trends: dict[str, Any],
        anomalies: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        """Generate rule-based recommendations for the template report."""
        recs: list[dict[str, str]] = []

        roas = metrics.get("roas", 0)
        ctr = metrics.get("ctr", 0)
        cvr = metrics.get("cvr", 0)
        cpa = metrics.get("cpa", 0)
        target_cpa = campaign.get("target_cpa") or 0
        roas_change = trends.get("roas", {}).get("change_pct", 0)

        if roas < 1.0 and metrics.get("spend", 0) > 0:
            recs.append({
                "title": "Urgent: ROAS below 1.0",
                "detail": (
                    f"Campaign ROAS is {roas:.2f}x — you're losing money on every ad dollar. "
                    "Pause the campaign or switch to Target ROAS bidding with a minimum target of 1.5x. "
                    "Review audience quality, creative messaging, and landing page conversion rate."
                ),
            })

        if roas_change < -20:
            recs.append({
                "title": "Declining ROAS Trend",
                "detail": (
                    f"ROAS dropped {abs(roas_change):.0f}% compared to the first half. "
                    "Investigate: audience saturation? creative fatigue? increased competition? "
                    "Refresh creatives and test new audience segments."
                ),
            })

        if ctr < 1.0:
            recs.append({
                "title": "Low CTR — Creative Refresh Needed",
                "detail": (
                    f"CTR is only {ctr:.2f}%. Rotate underperforming creatives and A/B test "
                    "3-5 new headline/CTA combinations. Target high-CTR audience segments."
                ),
            })

        if cvr < 3.0 and metrics.get("clicks", 0) > 100:
            recs.append({
                "title": "CVR Improvement Opportunity",
                "detail": (
                    f"CVR is {cvr:.2f}% — below the typical 3-5% benchmark. "
                    "Optimize landing page load time, message match from ad to landing page, "
                    "and consider simplifying the conversion form."
                ),
            })

        if target_cpa > 0 and cpa > target_cpa * 1.3:
            recs.append({
                "title": "CPA Exceeds Target",
                "detail": (
                    f"CPA (¥{cpa:.2f}) is {((cpa / target_cpa) - 1) * 100:.0f}% above target "
                    f"(¥{target_cpa:.2f}). Tighten audience targeting, lower max CPC bid, "
                    "or switch to Target CPA bidding strategy."
                ),
            })

        if anomalies:
            anomaly_metrics = list(set(a["metric"] for a in anomalies))
            recs.append({
                "title": "Anomaly Investigation Recommended",
                "detail": (
                    f"Anomalies detected in: {', '.join(anomaly_metrics)}. "
                    "Review the specific dates flagged and correlate with campaign changes "
                    "(bid adjustments, creative swaps, audience changes)."
                ),
            })

        if not recs:
            recs.append({
                "title": "Campaign Performing Well",
                "detail": (
                    "All KPIs are within acceptable ranges. Continue monitoring and consider "
                    "testing one variable at a time (bid, audience, creative) to find incremental gains."
                ),
            })

        return recs

    # ── LLM-based report ───────────────────────────────────────────────

    async def _llm_report(self, context: dict[str, Any]) -> str:
        """Generate a report via LLM."""
        prompt = f"""You are an advertising campaign analyst. Generate an executive summary report in Markdown format for the following campaign data.

Campaign: {context['campaign']['name']} (ID: {context['campaign']['id']})
Date Range: {context['date_range']['from']} → {context['date_range']['to']}
Status: {context['campaign']['status']}
Daily Budget: ¥{context['campaign']['daily_budget']}
Bid Strategy: {context['campaign']['bid_strategy']}

Metrics:
- Impressions: {context['metrics'].get('impressions', 0):,}
- Clicks: {context['metrics'].get('clicks', 0):,}
- Conversions: {context['metrics'].get('conversions', 0):,}
- Spend: ¥{context['metrics'].get('spend', 0):,.2f}
- Revenue: ¥{context['metrics'].get('revenue', 0):,.2f}
- CTR: {context['metrics'].get('ctr', 0):.2f}%
- CVR: {context['metrics'].get('cvr', 0):.2f}%
- CPC: ¥{context['metrics'].get('cpc', 0):.4f}
- CPA: ¥{context['metrics'].get('cpa', 0):.2f}
- ROAS: {context['metrics'].get('roas', 0):.2f}x

Trends (period-over-period changes):
{chr(10).join(f"- {k}: {v.get('change_pct', 0):+.1f}% (first: {v.get('first_half', 0):.2f}, second: {v.get('second_half', 0):.2f})" for k, v in context.get('trends', {}).items())}

Anomalies detected: {len(context.get('anomalies', []))}
Alerts: {', '.join(a['name'] for a in context.get('alerts', [])) if context.get('alerts') else 'None'}

Structure the Markdown report with:
1. Executive Summary
2. Key Performance Indicators (with trend indicators)
3. Anomalies section
4. Recommendations (specific and actionable)
5. Summary and next steps

Keep it professional, concise, and data-driven. Use emoji indicators for trends (🟢↑ 🟡↘ 🔴↓). Do not use markdown code fences around the report."""
        try:
            reply = await self.llm.chat(prompt)
            # Clean up any trailing code fences
            reply = reply.strip()
            if reply.startswith("```"):
                lines = reply.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                reply = "\n".join(lines)
            return reply
        except Exception:
            return ""

    @staticmethod
    def _error_report(
        campaign_id: int, date_range: tuple[str, str] | None, error: str
    ) -> str:
        dr = f"{date_range[0]} → {date_range[1]}" if date_range else "N/A"
        return f"""# 📊 Campaign Performance Report — Error

**Campaign ID:** {campaign_id}
**Period:** {dr}
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

## ⚠️ Report Generation Failed

An error occurred while generating the report: **{error}**

Please try again or contact support if the issue persists.

---
*Report generated by Ad Platform Agent*
"""
