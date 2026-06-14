"""Budget pacing engine — hourly allocation, overspend protection, cross-channel redistribution.

Computes current pacing status, allocates hourly budget slices, and redistributes
budget across platforms based on real-time performance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.budget import BudgetLog
from backend.models.performance import PerformanceMetric


# ── helpers ──────────────────────────────────────────────────────────────
def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _current_hour() -> int:
    return datetime.now(timezone.utc).hour


def _hours_elapsed_today() -> int:
    return max(_current_hour(), 0)


def _hours_remaining_today() -> int:
    return max(23 - _current_hour(), 0)


# ── public API ───────────────────────────────────────────────────────────
async def get_pacing_status(campaign_id: int, db: AsyncSession) -> dict[str, Any]:
    """Return pacing status for a single campaign.

    Returns:
        Dict with keys: campaign_id, daily_budget, spend_today, spend_today_pct,
        budget_remaining, expected_spend_by_now, pacing_delta,
        pacing_status, hourly_allocation, hours_elapsed, hours_remaining.
    """
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return {"error": f"Campaign {campaign_id} not found", "campaign_id": campaign_id}

    daily_budget = float(campaign.daily_budget or 0.0)

    today = _today_str()
    spend_result = await db.execute(
        select(func.coalesce(func.sum(BudgetLog.spend), 0.0)).where(
            and_(BudgetLog.campaign_id == campaign_id, BudgetLog.date == today)
        )
    )
    spend_today = float(spend_result.scalar() or 0.0)

    hours_elapsed = _hours_elapsed_today()
    hours_remaining = _hours_remaining_today()
    total_hours = max(hours_elapsed + hours_remaining, 24)

    expected_spend = daily_budget * (hours_elapsed / 24.0) if daily_budget > 0 else 0.0
    pacing_delta = spend_today - expected_spend
    spend_pct = (spend_today / daily_budget * 100.0) if daily_budget > 0 else 0.0

    if daily_budget <= 0:
        pacing_status = "no_budget"
    elif pacing_delta > daily_budget * 0.10:
        pacing_status = "overspending"
    elif pacing_delta < -daily_budget * 0.10:
        pacing_status = "underspending"
    else:
        pacing_status = "on_track"

    remaining_budget = max(daily_budget - spend_today, 0.0)
    hourly_alloc = remaining_budget / hours_remaining if hours_remaining > 0 else remaining_budget

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "daily_budget": round(daily_budget, 2),
        "spend_today": round(spend_today, 2),
        "spend_today_pct": round(spend_pct, 2),
        "budget_remaining": round(remaining_budget, 2),
        "expected_spend_by_now": round(expected_spend, 2),
        "pacing_delta": round(pacing_delta, 2),
        "pacing_status": pacing_status,
        "hourly_allocation": round(hourly_alloc, 2),
        "hours_elapsed": hours_elapsed,
        "hours_remaining": hours_remaining,
    }


async def allocate_hourly_budget(campaign_id: int, db: AsyncSession) -> dict[str, Any]:
    """Compute the recommended hourly budget for the next N hours.

    Uses a weighted schedule: prime hours (8-22) get 1.5x weight.
    Returns an array of per-hour allocations for remaining hours today.
    """
    today = _today_str()
    current_hour = _current_hour()

    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return {"error": f"Campaign {campaign_id} not found", "campaign_id": campaign_id}

    daily_budget = float(campaign.daily_budget or 0.0)

    spend_result = await db.execute(
        select(func.coalesce(func.sum(BudgetLog.spend), 0.0)).where(
            and_(BudgetLog.campaign_id == campaign_id, BudgetLog.date == today)
        )
    )
    spend_today = float(spend_result.scalar() or 0.0)
    remaining = max(daily_budget - spend_today, 0.0)

    hours_ahead = list(range(current_hour, 24))
    if not hours_ahead:
        return {
            "campaign_id": campaign_id,
            "remaining_budget": round(remaining, 2),
            "allocations": [],
            "note": "No remaining hours today",
        }

    weights = [1.5 if 8 <= h <= 22 else 1.0 for h in hours_ahead]
    weight_sum = sum(weights)
    if weight_sum == 0:
        weight_sum = 1.0

    allocations = [
        {
            "hour": h,
            "budget": round(remaining * (w / weight_sum), 2),
            "weight": round(w, 2),
        }
        for h, w in zip(hours_ahead, weights)
    ]

    uniform_slice = remaining / len(hours_ahead) if hours_ahead else 0.0
    for alloc in allocations:
        alloc["capped"] = round(min(alloc["budget"], uniform_slice * 2.0), 2)

    return {
        "campaign_id": campaign_id,
        "daily_budget": round(daily_budget, 2),
        "spend_today": round(spend_today, 2),
        "remaining_budget": round(remaining, 2),
        "allocations": allocations,
    }


async def redistribute_budget(
    platform_performance: list[dict[str, Any]], db: AsyncSession
) -> dict[str, Any]:
    """Redistribute budget across platforms based on recent ROAS or CPA.

    Args:
        platform_performance: List of dicts, each with keys:
            campaign_id, platform, spend, revenue, roas, cpa, impressions, clicks.
        db: Async DB session.

    Returns:
        Dict with keys: campaigns (per-campaign redistribution), summary.
    """
    if not platform_performance:
        return {"error": "No platform performance data provided", "campaigns": []}

    campaigns_out: list[dict[str, Any]] = []

    for entry in platform_performance:
        campaign_id = entry.get("campaign_id")
        if campaign_id is None:
            continue

        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            continue

        daily = float(campaign.daily_budget or 0.0)
        platform = entry.get("platform", "unknown")
        spend = float(entry.get("spend", 0))
        revenue = float(entry.get("revenue", 0))
        roas = float(entry.get("roas", 0)) or (revenue / spend if spend > 0 else 0)
        cpa = float(entry.get("cpa", 0)) or (
            spend / float(entry.get("conversions", 1)) if entry.get("conversions", 0) > 0 else 0
        )

        campaigns_out.append({
            "campaign_id": campaign_id,
            "platform": platform,
            "current_spend": round(spend, 2),
            "revenue": round(revenue, 2),
            "roas": round(roas, 4),
            "cpa": round(cpa, 4),
            "daily_budget": round(daily, 2),
        })

    if not campaigns_out:
        return {"error": "No valid campaigns found", "campaigns": []}

    by_campaign: dict[int, list[dict[str, Any]]] = {}
    for c in campaigns_out:
        by_campaign.setdefault(c["campaign_id"], []).append(c)

    redistribution: list[dict[str, Any]] = []
    for cid, entries in by_campaign.items():
        total_daily = entries[0]["daily_budget"]

        roas_values = [e["roas"] for e in entries]
        if sum(roas_values) <= 0:
            weights_arr = [1.0] * len(entries)
        else:
            roas_values = [max(x, 0.0) for x in roas_values]
            roas_sum = sum(roas_values)
            if roas_sum == 0:
                weights_arr = [1.0] * len(entries)
            else:
                weights_arr = [x / roas_sum for x in roas_values]

        for i, entry in enumerate(entries):
            recommended_spend = total_daily * float(weights_arr[i])
            entry["recommended_spend"] = round(recommended_spend, 2)
            entry["weight"] = round(float(weights_arr[i]), 4)
            entry["delta"] = round(recommended_spend - entry["current_spend"], 2)

        redistribution.extend(entries)

    return {
        "campaigns": redistribution,
        "summary": {
            "total_campaigns": len(by_campaign),
            "total_platforms": len(redistribution),
            "strategy": "roas_weighted",
        },
    }
