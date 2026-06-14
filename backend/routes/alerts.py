"""Alerts REST API — alert rule CRUD + evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
)
from backend.services import rule_engine

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/", response_model=dict)
async def list_alert_rules(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all alert rules."""
    rules, total = await rule_engine.list_alert_rules(
        db, offset=offset, limit=limit
    )
    return {
        "data": [AlertRuleResponse.model_validate(r).model_dump() for r in rules],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.post("/", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    body: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new alert rule."""
    rule = await rule_engine.create_alert_rule(db, body.model_dump())
    return AlertRuleResponse.model_validate(rule)


@router.get("/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single alert rule by ID."""
    rule = await rule_engine.get_alert_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return AlertRuleResponse.model_validate(rule)


@router.patch("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    body: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update alert rule fields."""
    rule = await rule_engine.get_alert_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    updated = await rule_engine.update_alert_rule(
        db, rule, body.model_dump(exclude_unset=True)
    )
    return AlertRuleResponse.model_validate(updated)


@router.delete("/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert rule."""
    rule = await rule_engine.get_alert_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    await rule_engine.delete_alert_rule(db, rule)


@router.post("/evaluate")
async def evaluate_rules(
    db: AsyncSession = Depends(get_db),
):
    """Evaluate all enabled alert rules against current performance data.

    Returns a list of triggered alerts with details (metric, current value, threshold).
    """
    result = await rule_engine.evaluate_all_rules(db)
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "total_rules": result.get("total_rules", 0),
        "evaluated": result.get("evaluated", 0),
        "triggered_count": result.get("triggered_count", 0),
        "alerts": result.get("triggered", []),
        "summary": result.get("summary", {}),
    }
