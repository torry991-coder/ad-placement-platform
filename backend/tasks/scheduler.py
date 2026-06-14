"""
Async task scheduler — asyncio-based, no Celery dependency.

Tasks:
  - hourly_budget_reset: Reset daily budget counters at midnight (UTC).
  - performance_snapshot: Take hourly snapshots of campaign performance.
  - alert_check: Run all alert rules evaluation every 5 minutes.
  - report_generation: Generate daily summary reports at 6 AM UTC.

Start / stop via:
    from backend.tasks.scheduler import start_scheduler, stop_scheduler
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_

from backend.database import async_session_factory
from backend.config import get_settings

logger = logging.getLogger(__name__)

# Use loguru if available
try:
    from loguru import logger as loguru_logger
    logger = loguru_logger  # type: ignore[assignment]
except ImportError:
    pass

# ── Track running tasks ──────────────────────────────────────────────────
_tasks: dict[str, asyncio.Task] = {}
_stop_event: asyncio.Event | None = None

# ── Settings ─────────────────────────────────────────────────────────────
settings = get_settings()


# =========================================================================
# Task implementations
# =========================================================================

async def hourly_budget_reset() -> None:
    """Reset daily budget spent counters at midnight UTC.

    Iterates all active campaigns and resets the daily budget tracker.
    In a real system this would happen per-campaign based on local midnight;
    here we use a simplified UTC-midnight approach.
    """
    try:
        async with async_session_factory() as db:
            from backend.models.campaign import Campaign
            from backend.models.enums import CampaignStatus

            result = await db.execute(
                select(Campaign).where(Campaign.status.in_([CampaignStatus.ACTIVE, CampaignStatus.LEARNING]))
            )
            campaigns = result.scalars().all()

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            for campaign in campaigns:
                # Reset the daily budget spent tracker by recording a zero-spend
                # budget log entry for the new day if not already present.
                from backend.models.budget import BudgetLog

                existing = await db.execute(
                    select(func.count(BudgetLog.id)).where(
                        and_(
                            BudgetLog.campaign_id == campaign.id,
                            BudgetLog.date == today,
                        )
                    )
                )
                if existing.scalar() == 0:
                    # Create a new budget log entry for hour 0
                    log_entry = BudgetLog(
                        campaign_id=int(campaign.id),
                        date=today,
                        hour=0,
                        spend=0.0,
                        impressions=0,
                        clicks=0,
                        conversions=0,
                    )
                    db.add(log_entry)

                logger.debug(
                    "Budget reset for campaign %d (%s)", campaign.id, campaign.name
                )

            await db.commit()
            logger.info(
                "hourly_budget_reset: reset %d campaign(s) at midnight.", len(campaigns)
            )

    except Exception:
        logger.exception("hourly_budget_reset failed")


async def performance_snapshot() -> None:
    """Take hourly snapshots of campaign performance.

    Aggregates performance metrics for the current hour and writes
    a PerformanceMetric record if one doesn't already exist.
    """
    try:
        async with async_session_factory() as db:
            from backend.models.performance import PerformanceMetric
            from backend.models.campaign import Campaign
            from backend.models.enums import CampaignStatus

            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")
            current_hour = now.hour

            result = await db.execute(
                select(Campaign).where(Campaign.status.in_([CampaignStatus.ACTIVE, CampaignStatus.LEARNING]))
            )
            campaigns = result.scalars().all()

            snapshot_count = 0
            for campaign in campaigns:
                # Check if snapshot already exists for this campaign + hour
                existing = await db.execute(
                    select(func.count(PerformanceMetric.id)).where(
                        and_(
                            PerformanceMetric.campaign_id == campaign.id,
                            PerformanceMetric.date == today,
                            PerformanceMetric.hour == current_hour,
                        )
                    )
                )
                if existing.scalar() > 0:
                    continue

                # Aggregate from budget logs for this hour
                from backend.models.budget import BudgetLog

                agg_result = await db.execute(
                    select(
                        func.coalesce(func.sum(BudgetLog.impressions), 0),
                        func.coalesce(func.sum(BudgetLog.clicks), 0),
                        func.coalesce(func.sum(BudgetLog.conversions), 0),
                        func.coalesce(func.sum(BudgetLog.spend), 0.0),
                    ).where(
                        and_(
                            BudgetLog.campaign_id == campaign.id,
                            BudgetLog.date == today,
                            BudgetLog.hour == current_hour,
                        )
                    )
                )
                row = agg_result.one()
                impressions = int(row[0])
                clicks = int(row[1])
                conversions = int(row[2])
                spend = float(row[3])

                # Compute derived metrics
                ctr = (clicks / impressions * 100.0) if impressions > 0 else 0.0
                cvr = (conversions / clicks * 100.0) if clicks > 0 else 0.0
                cpc = spend / clicks if clicks > 0 else 0.0
                cpa = spend / conversions if conversions > 0 else 0.0
                # Revenue estimation — simplified
                revenue = spend * 2.5  # assume 2.5x ROAS baseline
                roas = revenue / spend if spend > 0 else 0.0

                snapshot = PerformanceMetric(
                    campaign_id=int(campaign.id),
                    date=today,
                    hour=current_hour,
                    platform="simulated",
                    impressions=impressions,
                    clicks=clicks,
                    conversions=conversions,
                    spend=round(spend, 2),
                    revenue=round(revenue, 2),
                    ctr=round(ctr, 4),
                    cvr=round(cvr, 4),
                    cpc=round(cpc, 4),
                    cpa=round(cpa, 4),
                    roas=round(roas, 4),
                    quality_score=6.0,
                )
                db.add(snapshot)
                snapshot_count += 1

            await db.commit()
            logger.info(
                "performance_snapshot: wrote %d snapshot(s) for hour %d.",
                snapshot_count, current_hour,
            )

    except Exception:
        logger.exception("performance_snapshot failed")


async def alert_check() -> None:
    """Run all alert rules evaluation.

    Uses the rule_engine.evaluate_all_rules to check every enabled alert.
    """
    try:
        async with async_session_factory() as db:
            from backend.services.rule_engine import evaluate_all_rules

            result = await evaluate_all_rules(db)
            await db.commit()

            triggered = result.get("triggered_count", 0)
            if triggered > 0:
                logger.warning(
                    "alert_check: %d alert(s) triggered out of %d evaluated.",
                    triggered, result.get("total_rules", 0),
                )
            else:
                logger.debug(
                    "alert_check: %d rule(s) evaluated, none triggered.",
                    result.get("total_rules", 0),
                )

    except Exception:
        logger.exception("alert_check failed")


async def report_generation() -> None:
    """Generate daily summary reports at 6 AM UTC.

    Generates a report for the previous day across all campaigns.
    """
    try:
        from datetime import timedelta

        async with async_session_factory() as db:
            from backend.services.report_generator import generate_report

            now = datetime.now(timezone.utc)
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

            report = await generate_report(
                db=db,
                report_type="daily",
                campaign_id=None,
                date_from=yesterday,
                date_to=yesterday,
                metrics=[
                    "impressions", "clicks", "conversions",
                    "spend", "revenue", "ctr", "cvr", "cpc", "cpa", "roas",
                ],
            )

            await db.commit()

            summary = report.get("summary", {})
            logger.info(
                "report_generation: daily report %s generated. "
                "Impressions=%s, Clicks=%s, Conversions=%s, Spend=¥%s, Revenue=¥%s",
                report.get("report_id", "unknown"),
                summary.get("impressions", 0),
                summary.get("clicks", 0),
                summary.get("conversions", 0),
                summary.get("spend", 0),
                summary.get("revenue", 0),
            )

    except Exception:
        logger.exception("report_generation failed")


# =========================================================================
# Loop runners (each spins forever, sleeping until next window)
# =========================================================================

async def _run_hourly_budget_reset(stop: asyncio.Event) -> None:
    """Run budget reset at midnight UTC each day."""
    while not stop.is_set():
        now = datetime.now(timezone.utc)
        # Compute seconds until next midnight
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        next_midnight += timedelta(days=1)  # type: ignore
        sleep_seconds = max(1, (next_midnight - now).total_seconds())

        try:
            await asyncio.wait_for(stop.wait(), timeout=sleep_seconds)
            return  # stop was set
        except asyncio.TimeoutError:
            pass  # time to run the task

        await hourly_budget_reset()


async def _run_performance_snapshot(stop: asyncio.Event) -> None:
    """Run performance snapshot once per hour at the top of the hour."""
    while not stop.is_set():
        now = datetime.now(timezone.utc)
        # Seconds until next hour
        next_hour = now.replace(minute=0, second=0, microsecond=0)
        next_hour += timedelta(hours=1)  # type: ignore
        sleep_seconds = max(1, (next_hour - now).total_seconds())

        try:
            await asyncio.wait_for(stop.wait(), timeout=sleep_seconds)
            return
        except asyncio.TimeoutError:
            pass

        await performance_snapshot()


async def _run_alert_check(stop: asyncio.Event) -> None:
    """Run alert rule evaluation every 5 minutes."""
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=300)
            return
        except asyncio.TimeoutError:
            pass

        await alert_check()


async def _run_report_generation(stop: asyncio.Event) -> None:
    """Run daily report generation at 6 AM UTC."""
    while not stop.is_set():
        now = datetime.now(timezone.utc)
        # Compute seconds until next 6:00 AM
        next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)  # type: ignore
        sleep_seconds = max(1, (next_run - now).total_seconds())

        try:
            await asyncio.wait_for(stop.wait(), timeout=sleep_seconds)
            return
        except asyncio.TimeoutError:
            pass

        await report_generation()


# =========================================================================
# Public start / stop
# =========================================================================

async def start_scheduler() -> None:
    """Start all background scheduler tasks.

    Call this from your FastAPI lifespan startup handler.
    """
    global _stop_event, _tasks

    if _stop_event is not None and not _stop_event.is_set():
        logger.warning("Scheduler is already running.")
        return

    _stop_event = asyncio.Event()

    _tasks["hourly_budget_reset"] = asyncio.create_task(
        _run_hourly_budget_reset(_stop_event),
        name="hourly_budget_reset",
    )
    _tasks["performance_snapshot"] = asyncio.create_task(
        _run_performance_snapshot(_stop_event),
        name="performance_snapshot",
    )
    _tasks["alert_check"] = asyncio.create_task(
        _run_alert_check(_stop_event),
        name="alert_check",
    )
    _tasks["report_generation"] = asyncio.create_task(
        _run_report_generation(_stop_event),
        name="report_generation",
    )

    logger.info(
        "Task scheduler started with %d tasks: %s",
        len(_tasks), ", ".join(_tasks.keys()),
    )


async def stop_scheduler() -> None:
    """Stop all background scheduler tasks gracefully.

    Call this from your FastAPI lifespan shutdown handler.
    """
    global _stop_event, _tasks

    if _stop_event is None:
        return

    logger.info("Stopping task scheduler...")
    _stop_event.set()

    for name, task in _tasks.items():
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug("Task %s cancelled.", name)
            except Exception:
                logger.exception("Task %s raised exception during shutdown.", name)

    _tasks.clear()
    _stop_event = None
    logger.info("Task scheduler stopped.")


def get_scheduler_status() -> dict:
    """Return current status of the scheduler for health checks."""
    running = _stop_event is not None and not _stop_event.is_set()
    task_status = {}
    for name, task in _tasks.items():
        task_status[name] = {
            "running": not task.done(),
            "cancelled": task.cancelled(),
            "exception": task.exception().__class__.__name__ if task.done() and task.exception() else None,
        }
    return {
        "scheduler_running": running,
        "task_count": len(_tasks),
        "tasks": task_status,
    }
