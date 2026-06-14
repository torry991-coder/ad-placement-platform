"""Multi-touch attribution models.

Supports six models: last_touch, first_touch, linear, time_decay,
position_based, and data_driven (Shapley-value based).

Uses PerformanceMetric rows (grouped by date + platform) as touchpoints.
"""

from __future__ import annotations

import math
from collections import defaultdict
from itertools import combinations
from typing import Any

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.performance import PerformanceMetric
from backend.models.enums import AttributionModel


# ── public API ──────────────────────────────────────────────────────────
async def calculate_attribution(
    campaign_id: int,
    db: AsyncSession,
    model: str = "last_touch",
) -> list[dict[str, Any]]:
    """Calculate channel-level attribution weights for a campaign.

    Args:
        campaign_id: Target campaign.
        db: Async DB session.
        model: One of last_touch, first_touch, linear, time_decay,
               position_based, data_driven.

    Returns:
        List of dicts with keys: platform, weight (0-1), conversions_attributed,
        revenue_attributed, model.
    """
    rows = await _fetch_touchpoints(campaign_id, db)
    if not rows:
        return [{"error": "No performance data found", "campaign_id": campaign_id}]

    model_lower = model.lower()

    if model_lower == AttributionModel.LAST_TOUCH.value:
        result = _last_touch(rows)
    elif model_lower == AttributionModel.FIRST_TOUCH.value:
        result = _first_touch(rows)
    elif model_lower == AttributionModel.LINEAR.value:
        result = _linear(rows)
    elif model_lower == AttributionModel.TIME_DECAY.value:
        result = _time_decay(rows)
    elif model_lower == AttributionModel.POSITION_BASED.value:
        result = _position_based(rows)
    elif model_lower == AttributionModel.DATA_DRIVEN.value:
        result = _data_driven_shapley(rows)
    else:
        result = _last_touch(rows)

    return result


# ── helpers: fetch & preprocess ────────────────────────────────────────
async def _fetch_touchpoints(
    campaign_id: int, db: AsyncSession
) -> list[dict[str, Any]]:
    """Fetch aggregated touchpoints grouped by platform and date."""
    result = await db.execute(
        select(
            PerformanceMetric.date,
            PerformanceMetric.platform,
            func.sum(PerformanceMetric.conversions).label("conversions"),
            func.sum(PerformanceMetric.revenue).label("revenue"),
            func.sum(PerformanceMetric.clicks).label("clicks"),
            func.sum(PerformanceMetric.impressions).label("impressions"),
        )
        .where(PerformanceMetric.campaign_id == campaign_id)
        .group_by(PerformanceMetric.date, PerformanceMetric.platform)
        .order_by(PerformanceMetric.date.asc(), PerformanceMetric.platform.asc())
    )
    rows = result.all()

    return [
        {
            "date": r.date,
            "platform": r.platform or "unknown",
            "conversions": int(r.conversions or 0),
            "revenue": float(r.revenue or 0.0),
            "clicks": int(r.clicks or 0),
            "impressions": int(r.impressions or 0),
        }
        for r in rows
    ]


def _unique_platforms(rows: list[dict[str, Any]]) -> list[str]:
    seen: dict[str, bool] = {}
    platforms: list[str] = []
    for r in rows:
        p = r["platform"]
        if p not in seen:
            seen[p] = True
            platforms.append(p)
    return platforms


def _group_by_date(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_date[r["date"]].append(r)
    return by_date


# ── last touch ──────────────────────────────────────────────────────────
def _last_touch(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """100% credit to the last touchpoint per conversion path."""
    platforms = _unique_platforms(rows)
    conv_attr: dict[str, int] = {p: 0 for p in platforms}
    rev_attr: dict[str, float] = {p: 0.0 for p in platforms}

    for date_touches in _group_by_date(rows).values():
        if not date_touches:
            continue
        last = date_touches[-1]
        p = last["platform"]
        conv_attr[p] += last["conversions"]
        rev_attr[p] += last["revenue"]

    weights = _normalize_weights(platforms, conv_attr)
    return _format_output(platforms, weights, conv_attr, rev_attr, "last_touch")


# ── first touch ─────────────────────────────────────────────────────────
def _first_touch(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """100% credit to the first touchpoint."""
    platforms = _unique_platforms(rows)
    conv_attr: dict[str, int] = {p: 0 for p in platforms}
    rev_attr: dict[str, float] = {p: 0.0 for p in platforms}

    for date_touches in _group_by_date(rows).values():
        if not date_touches:
            continue
        first = date_touches[0]
        p = first["platform"]
        conv_attr[p] += first["conversions"]
        rev_attr[p] += first["revenue"]

    weights = _normalize_weights(platforms, conv_attr)
    return _format_output(platforms, weights, conv_attr, rev_attr, "first_touch")


# ── linear ──────────────────────────────────────────────────────────────
def _linear(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Equal credit across all touchpoints. Each touchpoint in a journey
    gets 1/N of the conversions and revenue."""
    platforms = _unique_platforms(rows)
    conv_attr: dict[str, int] = {p: 0 for p in platforms}
    rev_attr: dict[str, float] = {p: 0.0 for p in platforms}

    for date_touches in _group_by_date(rows).values():
        n = len(date_touches)
        if n == 0:
            continue
        for touch in date_touches:
            p = touch["platform"]
            conv_attr[p] += int(round(touch["conversions"] / n))
            rev_attr[p] += touch["revenue"] / n

    weights = _normalize_weights(platforms, conv_attr)
    return _format_output(platforms, weights, conv_attr, rev_attr, "linear")


# ── time decay ──────────────────────────────────────────────────────────
def _time_decay(rows: list[dict[str, Any]], half_life_days: float = 7.0) -> list[dict[str, Any]]:
    """Exponential time-decay: recent touchpoints get more credit."""
    from datetime import datetime

    platforms = _unique_platforms(rows)
    by_date = _group_by_date(rows)
    sorted_dates = sorted(by_date.keys())

    if not sorted_dates:
        return _format_output(platforms, {p: 0.0 for p in platforms},
                              {p: 0 for p in platforms}, {p: 0.0 for p in platforms}, "time_decay")

    max_dt = datetime.strptime(sorted_dates[-1], "%Y-%m-%d")

    conv_attr: dict[str, float] = {p: 0.0 for p in platforms}
    rev_attr: dict[str, float] = {p: 0.0 for p in platforms}

    for date_str in sorted_dates:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        days_diff = (max_dt - dt).days
        decay = 0.5 ** (days_diff / half_life_days)

        for touch in by_date[date_str]:
            p = touch["platform"]
            conv_attr[p] += touch["conversions"] * decay
            rev_attr[p] += touch["revenue"] * decay

    weights = _normalize_weights_float(platforms, rev_attr)
    conv_int = {p: int(round(conv_attr[p])) for p in platforms}
    return _format_output(platforms, weights, conv_int, rev_attr, "time_decay")


# ── position based (U-shaped) ───────────────────────────────────────────
def _position_based(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """40% first touch, 40% last touch, 20% spread across middle."""
    platforms = _unique_platforms(rows)
    conv_attr: dict[str, float] = {p: 0.0 for p in platforms}
    rev_attr: dict[str, float] = {p: 0.0 for p in platforms}

    for date_touches in _group_by_date(rows).values():
        n = len(date_touches)
        if n == 0:
            continue

        total_conv = sum(t["conversions"] for t in date_touches)
        total_rev = sum(t["revenue"] for t in date_touches)

        if n == 1:
            p = date_touches[0]["platform"]
            conv_attr[p] += total_conv
            rev_attr[p] += total_rev
        elif n == 2:
            for touch in date_touches:
                p = touch["platform"]
                conv_attr[p] += touch["conversions"] * 0.5
                rev_attr[p] += touch["revenue"] * 0.5
        else:
            first = date_touches[0]
            last = date_touches[-1]
            middle = date_touches[1:-1]

            conv_attr[first["platform"]] += first["conversions"] * 0.4
            rev_attr[first["platform"]] += first["revenue"] * 0.4

            conv_attr[last["platform"]] += last["conversions"] * 0.4
            rev_attr[last["platform"]] += last["revenue"] * 0.4

            if middle:
                mid_weight = 0.20 / len(middle)
                for touch in middle:
                    conv_attr[touch["platform"]] += touch["conversions"] * mid_weight
                    rev_attr[touch["platform"]] += touch["revenue"] * mid_weight

    weights = _normalize_weights_float(platforms, rev_attr)
    conv_int = {p: int(round(conv_attr[p])) for p in platforms}
    return _format_output(platforms, weights, conv_int, rev_attr, "position_based")


# ── data-driven (Shapley value) ─────────────────────────────────────────
def _data_driven_shapley(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shapley-value based attribution.

    Treats each platform as a coalition player. Uses summed conversions
    as the characteristic function value.
    """
    platforms = _unique_platforms(rows)
    if not platforms:
        return []

    platform_conv: dict[str, int] = defaultdict(int)
    platform_rev: dict[str, float] = defaultdict(float)
    for r in rows:
        platform_conv[r["platform"]] += r["conversions"]
        platform_rev[r["platform"]] += r["revenue"]

    n = len(platforms)

    if n == 1:
        p = platforms[0]
        return _format_output(
            platforms, {p: 1.0},
            {p: platform_conv[p]}, {p: platform_rev[p]}, "data_driven",
        )

    shapley_conv: dict[str, float] = {p: 0.0 for p in platforms}
    shapley_rev: dict[str, float] = {p: 0.0 for p in platforms}

    for player in platforms:
        other_players = [p for p in platforms if p != player]

        for k in range(len(other_players) + 1):
            for subset in combinations(other_players, k):
                subset_set = set(subset)
                s = len(subset)

                v_s = sum(platform_conv[p] for p in subset_set)
                rev_s = sum(platform_rev[p] for p in subset_set)

                v_s_with = v_s + platform_conv[player]
                rev_s_with = rev_s + platform_rev[player]

                marginal_conv = v_s_with - v_s
                marginal_rev = rev_s_with - rev_s

                weight = math.factorial(s) * math.factorial(n - s - 1) / math.factorial(n)

                shapley_conv[player] += marginal_conv * weight
                shapley_rev[player] += marginal_rev * weight

    weights = _normalize_weights_float(platforms, shapley_conv)
    conv_int = {p: int(round(shapley_conv[p])) for p in platforms}
    return _format_output(platforms, weights, conv_int, shapley_rev, "data_driven")


# ── output helpers ──────────────────────────────────────────────────────
def _normalize_weights(platforms: list[str], conv_attr: dict[str, int]) -> dict[str, float]:
    total = sum(conv_attr.values())
    if total == 0:
        return {p: 0.0 for p in platforms}
    return {p: round(conv_attr[p] / total, 4) for p in platforms}


def _normalize_weights_float(platforms: list[str], values: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    if total == 0:
        return {p: 0.0 for p in platforms}
    return {p: round(values[p] / total, 4) for p in platforms}


def _format_output(
    platforms: list[str],
    weights: dict[str, float],
    conv_attr: dict[str, int],
    rev_attr: dict[str, float],
    model: str,
) -> list[dict[str, Any]]:
    return [
        {
            "platform": p,
            "weight": weights.get(p, 0.0),
            "conversions_attributed": conv_attr.get(p, 0),
            "revenue_attributed": round(rev_attr.get(p, 0.0), 2),
            "model": model,
        }
        for p in sorted(platforms)
    ]
