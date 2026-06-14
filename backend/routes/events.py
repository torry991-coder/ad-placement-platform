"""Event tracking endpoint — records impressions, clicks, conversions.

GET /api/event/track?type=impression&campaign_id=1&creative_id=5&request_id=xxx
GET /api/event/track?type=click&campaign_id=1&creative_id=5&request_id=xxx

Used for:
- Recording real ad impressions and clicks from the bidding engine
- Building training data for CTR/CVR models
- Attribution analysis
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.performance import PerformanceMetric
from backend.models.campaign import Campaign
from fastapi import Depends

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/event", tags=["events"])

# In-memory event buffer for batch writes (reduces DB load under high concurrency)
_buffer: list[dict] = []
MAX_BUFFER = 100


@router.get("/track", response_model=None)
async def track_event(
    type: str = Query(..., description="impression | click | conversion"),
    campaign_id: int = Query(..., description="Campaign ID"),
    creative_id: int | None = Query(None),
    request_id: str | None = Query(None),
    value: float | None = Query(None, description="Revenue value for conversions"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Track an ad event (impression, click, or conversion).

    This is the pixel/beacon endpoint that would be called by the ad client.
    In production, this would be a 1x1 GIF with query params, or a POST endpoint.
    """
    event = {
        "type": type,
        "campaign_id": campaign_id,
        "creative_id": creative_id,
        "request_id": request_id,
        "value": value or 0.0,
        "timestamp": datetime.now(timezone.utc),
    }

    # Quick response first (fire-and-forget pattern)
    # In production, events go to a message queue (Kafka/Redis Streams)
    # for async processing. Here we buffer and flush to DB.

    global _buffer
    _buffer.append(event)

    if len(_buffer) >= MAX_BUFFER:
        await _flush_buffer(db)

    return {"status": "recorded", "event_type": type, "buffered": len(_buffer)}


async def _flush_buffer(db: AsyncSession) -> None:
    """Flush buffered events to the performance_metrics table."""
    global _buffer
    if not _buffer:
        return

    events = _buffer.copy()
    _buffer = []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    current_hour = datetime.now(timezone.utc).hour

    # Aggregate by campaign_id for today/hour
    aggregates: dict[int, dict[str, int | float]] = {}
    for evt in events:
        cid = evt["campaign_id"]
        if cid not in aggregates:
            aggregates[cid] = {
                "impressions": 0, "clicks": 0, "conversions": 0,
                "spend": 0.0, "revenue": 0.0,
            }
        agg = aggregates[cid]
        if evt["type"] == "impression":
            agg["impressions"] += 1
            agg["spend"] += _estimate_cost(cid, evt)
        elif evt["type"] == "click":
            agg["clicks"] += 1
        elif evt["type"] == "conversion":
            agg["conversions"] += 1
            agg["revenue"] += float(evt.get("value", 0))

    # Update or create PerformanceMetric rows
    for cid, agg in aggregates.items():
        # Check if row exists for today/hour
        result = await db.execute(
            select(PerformanceMetric).where(
                PerformanceMetric.campaign_id == cid,
                PerformanceMetric.date == today,
                PerformanceMetric.hour == current_hour,
            )
        )
        row = result.scalar_one_or_none()

        if row:
            row.impressions = (row.impressions or 0) + int(agg["impressions"])
            row.clicks = (row.clicks or 0) + int(agg["clicks"])
            row.conversions = (row.conversions or 0) + int(agg["conversions"])
            row.spend = float(row.spend or 0) + float(agg["spend"])
            row.revenue = float(row.revenue or 0) + float(agg["revenue"])
            # Recompute derived metrics
            imp = row.impressions
            clk = row.clicks
            conv = row.conversions
            sp = row.spend
            rev = row.revenue
            row.ctr = round(clk / imp * 100, 4) if imp > 0 else 0.0
            row.cvr = round(conv / clk * 100, 4) if clk > 0 else 0.0
            row.cpc = round(sp / clk, 4) if clk > 0 else 0.0
            row.cpa = round(sp / conv, 4) if conv > 0 else 0.0
            row.roas = round(rev / sp, 4) if sp > 0 else 0.0
        else:
            imp = int(agg["impressions"])
            clk = int(agg["clicks"])
            conv = int(agg["conversions"])
            sp = float(agg["spend"])
            rev = float(agg["revenue"])
            row = PerformanceMetric(
                campaign_id=cid,
                date=today,
                hour=current_hour,
                platform="direct",
                impressions=imp,
                clicks=clk,
                conversions=conv,
                spend=round(sp, 2),
                revenue=round(rev, 2),
                ctr=round(clk / imp * 100, 4) if imp > 0 else 0.0,
                cvr=round(conv / clk * 100, 4) if clk > 0 else 0.0,
                cpc=round(sp / clk, 4) if clk > 0 else 0.0,
                cpa=round(sp / conv, 4) if conv > 0 else 0.0,
                roas=round(rev / sp, 4) if sp > 0 else 0.0,
            )
            db.add(row)

    await db.flush()
    logger.info("Flushed %d events aggregated into %d campaign metrics", len(events), len(aggregates))


def _estimate_cost(campaign_id: int, event: dict) -> float:
    """Estimate cost per impression based on typical CPM rates."""
    # CPM ~= 5-15 RMB per 1000 impressions
    return 0.008  # ~8 RMB CPM


async def force_flush(db: AsyncSession) -> dict:
    """Manually flush the event buffer (useful for shutdown/health checks)."""
    await _flush_buffer(db)
    return {"flushed": True}


@router.get("/stats", response_model=None)
async def event_stats() -> dict:
    """Get current event buffer statistics."""
    return {
        "buffered_events": len(_buffer),
        "max_buffer": MAX_BUFFER,
    }
