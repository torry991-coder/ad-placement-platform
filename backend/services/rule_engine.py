"""Alert rule engine — evaluates alert conditions and triggers actions.

Supports metric comparison rules (>, <, >=, <=) with configurable lookback
windows. Actions include notify, pause_campaign, and reduce_budget.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.alert import AlertRule
from backend.models.performance import PerformanceMetric
from backend.models.campaign import Campaign
from backend.models.enums import CampaignStatus, AlertAction

logger = logging.getLogger(__name__)

_OPS = {
    ">": lambda a, t: a > t,
    "<": lambda a, t: a < t,
    ">=": lambda a, t: a >= t,
    "<=": lambda a, t: a <= t,
    "==": lambda a, t: abs(a - t) < 1e-9,
    "!=": lambda a, t: abs(a - t) >= 1e-9,
}


# ── public API ──────────────────────────────────────────────────────────
async def evaluate_rule(rule_id: int, db: AsyncSession) -> dict[str, Any]:
    """Evaluate a single alert rule and return whether it triggered."""
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        return {"error": f"Rule {rule_id} not found", "triggered": False}

    if not rule.is_enabled:
        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "triggered": False,
            "reason": "Rule is disabled",
        }

    condition = rule.condition or {}
    metric = condition.get("metric", "")
    operator = condition.get("operator", ">")
    threshold = condition.get("threshold", 0)
    window_hours = condition.get("window_hours", 24)

    current_value = await _fetch_metric_value(
        rule.scope_type or "campaign", rule.scope_id, metric, window_hours, db
    )

    op_func = _OPS.get(operator)
    if op_func is None:
        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "triggered": False,
            "error": f"Unknown operator: {operator}",
        }

    triggered = op_func(current_value, threshold)

    message = (
        f"[{rule.severity.value.upper() if rule.severity else 'WARNING'}] {rule.name}: "
        f"{metric} = {current_value:.4f} {operator} {threshold} "
        f"(window: {window_hours}h) -> {'TRIGGERED' if triggered else 'OK'}"
    )

    if triggered:
        now = datetime.now(timezone.utc)
        rule.last_triggered_at = now
        rule.trigger_count = (rule.trigger_count or 0) + 1
        await db.flush()

    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "triggered": triggered,
        "condition": {
            "metric": metric,
            "operator": operator,
            "threshold": threshold,
            "window_hours": window_hours,
        },
        "current_value": round(current_value, 4),
        "scope_type": rule.scope_type,
        "scope_id": rule.scope_id,
        "severity": rule.severity.value if rule.severity else "warning",
        "action": rule.action.value if rule.action else "notify",
        "message": message,
    }


async def evaluate_all_rules(
    db: AsyncSession, severity_filter: str | None = None
) -> dict[str, Any]:
    """Evaluate all enabled alert rules."""
    query = select(AlertRule).where(AlertRule.is_enabled == True)
    if severity_filter:
        query = query.where(AlertRule.severity == severity_filter)

    result = await db.execute(query)
    rules = result.scalars().all()

    triggered_alerts: list[dict[str, Any]] = []
    summary: dict[str, int] = {"info": 0, "warning": 0, "critical": 0, "total": 0}

    for rule in rules:
        eval_result = await evaluate_rule(rule.id, db)
        summary["total"] += 1
        if eval_result.get("triggered"):
            triggered_alerts.append(eval_result)
            sev = eval_result.get("severity", "warning")
            summary[sev] = summary.get(sev, 0) + 1

    return {
        "total_rules": len(rules),
        "evaluated": len(rules),
        "triggered": triggered_alerts,
        "triggered_count": len(triggered_alerts),
        "summary": summary,
    }


async def take_action(rule_id: int, db: AsyncSession) -> dict[str, Any]:
    """Execute the action associated with a triggered alert rule."""
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        return {"error": f"Rule {rule_id} not found", "action_taken": False}

    # Check cooldown
    if rule.last_triggered_at and rule.cooldown_minutes:
        now = datetime.now(timezone.utc)
        cooldown_end = rule.last_triggered_at + timedelta(minutes=rule.cooldown_minutes)
        if now < cooldown_end:
            remaining = (cooldown_end - now).total_seconds()
            return {
                "rule_id": rule.id,
                "action_taken": False,
                "reason": f"Cooldown active ({remaining:.0f}s remaining)",
                "cooldown_minutes": rule.cooldown_minutes,
            }

    action = rule.action
    if action is None:
        return {"rule_id": rule.id, "action_taken": False, "reason": "No action configured"}

    action_value = action.value if hasattr(action, "value") else str(action)

    if action_value == AlertAction.NOTIFY.value:
        return _execute_notify(rule)
    elif action_value == AlertAction.PAUSE_CAMPAIGN.value:
        return await _execute_pause_campaign(rule, db)
    elif action_value == AlertAction.REDUCE_BUDGET.value:
        return await _execute_reduce_budget(rule, db)
    else:
        return {"rule_id": rule.id, "action_taken": False, "reason": f"Unknown action: {action_value}"}


# ── metric fetching ─────────────────────────────────────────────────────
async def _fetch_metric_value(
    scope_type: str,
    scope_id: int | None,
    metric: str,
    window_hours: float,
    db: AsyncSession,
) -> float:
    """Fetch the current value of a metric for a given scope and window."""
    if scope_id is None:
        return 0.0

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=window_hours)

    agg_metrics = {"impressions", "clicks", "conversions", "spend", "revenue"}
    ratio_metrics = {"ctr", "cvr", "cpc", "cpa", "roas"}

    base_query = select(PerformanceMetric).where(
        and_(PerformanceMetric.created_at >= since, PerformanceMetric.created_at <= now)
    )

    if scope_type == "campaign":
        base_query = base_query.where(PerformanceMetric.campaign_id == scope_id)
    elif scope_type == "ad_group":
        base_query = base_query.where(PerformanceMetric.campaign_id == scope_id)
    # account-level: no additional filter

    result = await db.execute(base_query)
    rows = result.scalars().all()

    if not rows:
        return 0.0

    if metric in agg_metrics:
        total = sum(getattr(r, metric, 0) or 0 for r in rows)
        return float(total)

    if metric in ratio_metrics:
        total_impressions = sum(r.impressions or 0 for r in rows)
        total_clicks = sum(r.clicks or 0 for r in rows)
        total_conversions = sum(r.conversions or 0 for r in rows)
        total_spend = sum(float(r.spend or 0) for r in rows)
        total_revenue = sum(float(r.revenue or 0) for r in rows)

        if metric == "ctr":
            return round(total_clicks / total_impressions * 100.0, 4) if total_impressions > 0 else 0.0
        elif metric == "cvr":
            return round(total_conversions / total_clicks * 100.0, 4) if total_clicks > 0 else 0.0
        elif metric == "cpc":
            return round(total_spend / total_clicks, 4) if total_clicks > 0 else 0.0
        elif metric == "cpa":
            return round(total_spend / total_conversions, 4) if total_conversions > 0 else 0.0
        elif metric == "roas":
            return round(total_revenue / total_spend, 4) if total_spend > 0 else 0.0

    return 0.0


# ── action executors ────────────────────────────────────────────────────
def _execute_notify(rule: AlertRule) -> dict[str, Any]:
    logger.info(
        "Alert triggered: rule=%s severity=%s channels=%s",
        rule.name, rule.severity.value if rule.severity else "warning", rule.notify_channels,
    )
    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "action_taken": True,
        "action": "notify",
        "channels": rule.notify_channels or ["ui"],
        "severity": rule.severity.value if rule.severity else "warning",
        "message": f"ALERT: {rule.name} - condition met. Severity: {rule.severity}",
    }


async def _execute_pause_campaign(rule: AlertRule, db: AsyncSession) -> dict[str, Any]:
    scope_id = rule.scope_id
    if not scope_id:
        return {"rule_id": rule.id, "action_taken": False, "reason": "Missing scope_id"}

    result = await db.execute(select(Campaign).where(Campaign.id == scope_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return {"rule_id": rule.id, "action_taken": False, "reason": f"Campaign {scope_id} not found"}

    old_status = campaign.status.value if campaign.status else "unknown"
    campaign.status = CampaignStatus.PAUSED
    await db.flush()

    logger.warning("Campaign %d paused by alert rule %s (was %s)", scope_id, rule.name, old_status)

    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "action_taken": True,
        "action": "pause_campaign",
        "campaign_id": scope_id,
        "previous_status": old_status,
        "new_status": CampaignStatus.PAUSED.value,
    }


async def _execute_reduce_budget(rule: AlertRule, db: AsyncSession) -> dict[str, Any]:
    scope_id = rule.scope_id
    if not scope_id:
        return {"rule_id": rule.id, "action_taken": False, "reason": "Missing scope_id"}

    result = await db.execute(select(Campaign).where(Campaign.id == scope_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return {"rule_id": rule.id, "action_taken": False, "reason": f"Campaign {scope_id} not found"}

    old_budget = float(campaign.daily_budget or 0)
    new_budget = round(old_budget * 0.8, 2)
    campaign.daily_budget = new_budget
    await db.flush()

    logger.warning(
        "Campaign %d budget reduced by alert rule %s: %.2f -> %.2f",
        scope_id, rule.name, old_budget, new_budget,
    )

    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "action_taken": True,
        "action": "reduce_budget",
        "campaign_id": scope_id,
        "previous_budget": old_budget,
        "new_budget": new_budget,
        "reduction_pct": 20.0,
    }


# ── CRUD: Alert Rules ─────────────────────────────────────────────────
async def list_alert_rules(
    db: AsyncSession, offset: int = 0, limit: int = 50
) -> tuple[list, int]:
    """List alert rules with pagination, ordered by created_at desc.

    Returns (list_of_AlertRule_objects, total_count).
    """
    count_result = await db.execute(select(func.count(AlertRule.id)))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(AlertRule)
        .order_by(AlertRule.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rules = list(result.scalars().all())
    return rules, total


async def create_alert_rule(db: AsyncSession, data: dict) -> AlertRule:
    """Create a new AlertRule from a data dict."""
    rule = AlertRule(**data)
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def get_alert_rule(db: AsyncSession, rule_id: int) -> AlertRule | None:
    """Get an alert rule by id, or None if not found."""
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    return result.scalar_one_or_none()


async def update_alert_rule(db: AsyncSession, rule: AlertRule, data: dict) -> AlertRule:
    """Update an alert rule with non-None values from data dict."""
    for key, value in data.items():
        if value is not None:
            setattr(rule, key, value)
    await db.flush()
    await db.refresh(rule)
    return rule


async def delete_alert_rule(db: AsyncSession, rule: AlertRule) -> None:
    """Delete an alert rule."""
    await db.delete(rule)
    await db.flush()
