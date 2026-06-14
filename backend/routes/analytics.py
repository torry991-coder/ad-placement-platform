"""Analytics REST API — dashboards, trends, platform breakdowns."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.campaign import Campaign
from backend.models.enums import CampaignStatus
from backend.models.performance import PerformanceMetric
from backend.models.alert import AlertRule
from backend.schemas import (
    AnalyticsDashboard,
    PlatformBreakdown,
    TrendPoint,
    TrendsResponse,
)
from backend.services import campaign_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Rich analytics dashboard with KPIs, platform breakdown, and daily trends.

    Aggregates data from campaigns, performance metrics, and alert rules.
    """
    # Active campaigns count
    active_result = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.status == CampaignStatus.ACTIVE)
    )
    active_campaigns = active_result.scalar() or 0

    # Aggregate performance metrics (last 30 days)
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    perf_result = await db.execute(
        select(
            func.coalesce(func.sum(PerformanceMetric.impressions), 0),
            func.coalesce(func.sum(PerformanceMetric.clicks), 0),
            func.coalesce(func.sum(PerformanceMetric.conversions), 0),
            func.coalesce(func.sum(PerformanceMetric.spend), 0),
            func.coalesce(func.sum(PerformanceMetric.revenue), 0),
        ).where(PerformanceMetric.date >= thirty_days_ago)
    )
    imp, clicks, conv, spend, rev = perf_result.one()

    # Derived metrics
    ctr = (clicks / imp * 100) if imp > 0 else 0.0
    cvr = (conv / clicks * 100) if clicks > 0 else 0.0
    cpc = (spend / clicks) if clicks > 0 else 0.0
    cpa = (spend / conv) if conv > 0 else 0.0
    roas = (rev / spend) if spend > 0 else 0.0

    # Budget utilization (spend vs. total daily budgets)
    budget_result = await db.execute(
        select(
            func.coalesce(func.sum(Campaign.daily_budget), 0)
        ).where(Campaign.status == CampaignStatus.ACTIVE)
    )
    total_daily_budget = budget_result.scalar() or 0
    budget_utilization = (float(spend) / 30 / total_daily_budget * 100) if total_daily_budget > 0 else 0.0

    # Alert count
    alert_result = await db.execute(
        select(func.count(AlertRule.id)).where(AlertRule.is_enabled == True)
    )
    alert_count = alert_result.scalar() or 0

    # Platform breakdown
    platform_result = await db.execute(
        select(
            PerformanceMetric.platform,
            func.coalesce(func.sum(PerformanceMetric.impressions), 0),
            func.coalesce(func.sum(PerformanceMetric.clicks), 0),
            func.coalesce(func.sum(PerformanceMetric.conversions), 0),
            func.coalesce(func.sum(PerformanceMetric.spend), 0),
            func.coalesce(func.sum(PerformanceMetric.revenue), 0),
        )
        .where(PerformanceMetric.date >= thirty_days_ago)
        .group_by(PerformanceMetric.platform)
        .order_by(func.sum(PerformanceMetric.spend).desc())
    )
    platform_rows = platform_result.all()
    platform_breakdown = []
    for row in platform_rows:
        plat, p_imp, p_clk, p_conv, p_spd, p_rev = row
        platform_breakdown.append(PlatformBreakdown(
            platform=plat or "unknown",
            impressions=int(p_imp),
            clicks=int(p_clk),
            conversions=int(p_conv),
            spend=float(p_spd),
            revenue=float(p_rev),
            ctr=round(float(p_clk / p_imp * 100) if p_imp > 0 else 0.0, 4),
            cvr=round(float(p_conv / p_clk * 100) if p_clk > 0 else 0.0, 4),
            roas=round(float(p_rev / p_spd) if p_spd > 0 else 0.0, 4),
        ))

    # Daily trend (last 7 days)
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    trend_result = await db.execute(
        select(
            PerformanceMetric.date,
            func.coalesce(func.sum(PerformanceMetric.impressions), 0),
            func.coalesce(func.sum(PerformanceMetric.clicks), 0),
            func.coalesce(func.sum(PerformanceMetric.conversions), 0),
            func.coalesce(func.sum(PerformanceMetric.spend), 0),
            func.coalesce(func.sum(PerformanceMetric.revenue), 0),
        )
        .where(PerformanceMetric.date >= seven_days_ago)
        .group_by(PerformanceMetric.date)
        .order_by(PerformanceMetric.date.asc())
    )
    trend_rows = trend_result.all()
    daily_trend = []
    for row in trend_rows:
        d, t_imp, t_clk, t_conv, t_spd, t_rev = row
        daily_trend.append(TrendPoint(
            date=d,
            impressions=int(t_imp),
            clicks=int(t_clk),
            conversions=int(t_conv),
            spend=float(t_spd),
            revenue=float(t_rev),
            ctr=round(float(t_clk / t_imp * 100) if t_imp > 0 else 0.0, 4),
            cvr=round(float(t_conv / t_clk * 100) if t_clk > 0 else 0.0, 4),
            cpc=round(float(t_spd / t_clk) if t_clk > 0 else 0.0, 4),
            roas=round(float(t_rev / t_spd) if t_spd > 0 else 0.0, 4),
        ))

    return AnalyticsDashboard(
        active_campaigns=active_campaigns,
        total_impressions=int(imp),
        total_clicks=int(clicks),
        total_conversions=int(conv),
        total_spend=float(spend),
        total_revenue=float(rev),
        avg_ctr=round(ctr, 4),
        avg_cvr=round(cvr, 4),
        avg_cpc=round(cpc, 4),
        avg_cpa=round(cpa, 4),
        avg_roas=round(roas, 4),
        budget_utilization=round(budget_utilization, 2),
        platform_breakdown=platform_breakdown,
        daily_trend=daily_trend,
    )


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    campaign_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    granularity: str = Query("daily", pattern="^(hourly|daily)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get performance time series data.

    Supports hourly and daily granularity for a specific campaign or all campaigns.
    Default date range: last 30 days.
    """
    if not date_from:
        date_from = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    if not date_to:
        date_to = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if granularity == "hourly":
        group_cols = [PerformanceMetric.date, PerformanceMetric.hour]
        order_cols = [PerformanceMetric.date.asc(), PerformanceMetric.hour.asc()]
    else:
        group_cols = [PerformanceMetric.date]
        order_cols = [PerformanceMetric.date.asc()]

    query = select(
        PerformanceMetric.date,
        PerformanceMetric.hour if granularity == "hourly" else func.null(),
        func.coalesce(func.sum(PerformanceMetric.impressions), 0),
        func.coalesce(func.sum(PerformanceMetric.clicks), 0),
        func.coalesce(func.sum(PerformanceMetric.conversions), 0),
        func.coalesce(func.sum(PerformanceMetric.spend), 0),
        func.coalesce(func.sum(PerformanceMetric.revenue), 0),
    ).where(
        PerformanceMetric.date >= date_from,
        PerformanceMetric.date <= date_to,
    )

    if campaign_id:
        query = query.where(PerformanceMetric.campaign_id == campaign_id)

    query = query.group_by(*group_cols)

    # Build order_by
    for col in order_cols:
        query = query.order_by(col)

    rows = (await db.execute(query)).all()

    data: list[TrendPoint] = []
    for row in rows:
        if granularity == "hourly":
            d, h, t_imp, t_clk, t_conv, t_spd, t_rev = row
            label = f"{d} {h:02d}:00" if h is not None else d
        else:
            d, _, t_imp, t_clk, t_conv, t_spd, t_rev = row
            label = d

        data.append(TrendPoint(
            date=label,
            impressions=int(t_imp),
            clicks=int(t_clk),
            conversions=int(t_conv),
            spend=float(t_spd),
            revenue=float(t_rev),
            ctr=round(float(t_clk / t_imp * 100) if t_imp > 0 else 0.0, 4),
            cvr=round(float(t_conv / t_clk * 100) if t_clk > 0 else 0.0, 4),
            cpc=round(float(t_spd / t_clk) if t_clk > 0 else 0.0, 4),
            roas=round(float(t_rev / t_spd) if t_spd > 0 else 0.0, 4),
        ))

    return TrendsResponse(
        campaign_id=campaign_id,
        granularity=granularity,
        data=data,
    )


@router.get("/platforms", response_model=list[PlatformBreakdown])
async def get_platform_breakdown(
    db: AsyncSession = Depends(get_db),
):
    """Get performance breakdown by advertising platform.

    Returns metrics aggregated by platform (simulated, google, meta, tiktok).
    """
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    result = await db.execute(
        select(
            PerformanceMetric.platform,
            func.coalesce(func.sum(PerformanceMetric.impressions), 0),
            func.coalesce(func.sum(PerformanceMetric.clicks), 0),
            func.coalesce(func.sum(PerformanceMetric.conversions), 0),
            func.coalesce(func.sum(PerformanceMetric.spend), 0),
            func.coalesce(func.sum(PerformanceMetric.revenue), 0),
        )
        .where(PerformanceMetric.date >= thirty_days_ago)
        .group_by(PerformanceMetric.platform)
        .order_by(func.sum(PerformanceMetric.spend).desc())
    )

    platforms: list[PlatformBreakdown] = []
    for row in result.all():
        plat, p_imp, p_clk, p_conv, p_spd, p_rev = row
        platforms.append(PlatformBreakdown(
            platform=plat or "unknown",
            impressions=int(p_imp),
            clicks=int(p_clk),
            conversions=int(p_conv),
            spend=float(p_spd),
            revenue=float(p_rev),
            ctr=round(float(p_clk / p_imp * 100) if p_imp > 0 else 0.0, 4),
            cvr=round(float(p_conv / p_clk * 100) if p_clk > 0 else 0.0, 4),
            roas=round(float(p_rev / p_spd) if p_spd > 0 else 0.0, 4),
        ))

    return platforms
