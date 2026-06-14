"""Audience segment management service.

Provides CRUD for audience segments, segment-level performance stats
(CTR/CVR/ROAS computed from performance_metrics), and lookalike expansion
via cosine similarity on rule vectors.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audience import AudienceSegment
from backend.models.performance import PerformanceMetric
from backend.models.campaign import Campaign


# ── public API ──────────────────────────────────────────────────────────
async def create_segment(
    db: AsyncSession,
    name: str,
    rules: dict[str, Any],
    description: Optional[str] = None,
    seed_audience_id: Optional[int] = None,
    labels: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Create a new audience segment."""
    segment = AudienceSegment(
        name=name,
        description=description,
        rules=rules,
        member_count=_estimate_member_count(rules),
        seed_audience_id=seed_audience_id,
        labels=labels,
    )
    db.add(segment)
    await db.flush()
    await db.refresh(segment)
    return _segment_to_dict(segment)


async def get_segment(db: AsyncSession, segment_id: int) -> Optional[dict[str, Any]]:
    """Fetch a single audience segment by ID."""
    result = await db.execute(
        select(AudienceSegment).where(AudienceSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        return None
    return _segment_to_dict(segment)


async def list_segments(
    db: AsyncSession,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """List audience segments with optional search."""
    query = select(AudienceSegment)
    count_q = select(func.count(AudienceSegment.id))

    if search:
        query = query.where(AudienceSegment.name.ilike(f"%{search}%"))
        count_q = count_q.where(AudienceSegment.name.ilike(f"%{search}%"))

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        query.order_by(AudienceSegment.updated_at.desc()).offset(offset).limit(limit)
    )
    segments = result.scalars().all()
    return [_segment_to_dict(s) for s in segments], total


async def calculate_segment_stats(db: AsyncSession, segment_id: int) -> dict[str, Any]:
    """Calculate CTR, CVR, ROAS for an audience segment.

    Joins PerformanceMetric rows via campaigns. In production you'd
    have direct audience-campaign mapping; here we scan all campaigns.
    """
    result = await db.execute(
        select(AudienceSegment).where(AudienceSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        return {"error": f"Segment {segment_id} not found"}

    campaigns_result = await db.execute(select(Campaign.id))
    campaign_ids = [r[0] for r in campaigns_result.all()]

    if not campaign_ids:
        return _empty_stats(segment)

    metrics_result = await db.execute(
        select(
            func.sum(PerformanceMetric.impressions).label("impressions"),
            func.sum(PerformanceMetric.clicks).label("clicks"),
            func.sum(PerformanceMetric.conversions).label("conversions"),
            func.sum(PerformanceMetric.spend).label("spend"),
            func.sum(PerformanceMetric.revenue).label("revenue"),
        ).where(PerformanceMetric.campaign_id.in_(campaign_ids))
    )
    row = metrics_result.one_or_none()

    if row is None:
        return _empty_stats(segment)

    impressions = int(row.impressions or 0)
    clicks = int(row.clicks or 0)
    conversions = int(row.conversions or 0)
    spend = float(row.spend or 0.0)
    revenue = float(row.revenue or 0.0)

    ctr = round(clicks / impressions * 100.0, 4) if impressions > 0 else 0.0
    cvr = round(conversions / clicks * 100.0, 4) if clicks > 0 else 0.0
    cpc = round(spend / clicks, 4) if clicks > 0 else 0.0
    cpa = round(spend / conversions, 4) if conversions > 0 else 0.0
    roas = round(revenue / spend, 4) if spend > 0 else 0.0

    return {
        "segment_id": segment.id,
        "segment_name": segment.name,
        "member_count": segment.member_count or 0,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "spend": round(spend, 2),
        "revenue": round(revenue, 2),
        "ctr": ctr,
        "cvr": cvr,
        "cpc": cpc,
        "cpa": cpa,
        "roas": roas,
    }


async def expand_lookalike(
    db: AsyncSession,
    seed_segment_id: int,
    top_k: int = 5,
    similarity_threshold: float = 0.3,
) -> dict[str, Any]:
    """Expand a seed audience into lookalike audiences via cosine similarity."""
    result = await db.execute(
        select(AudienceSegment).where(AudienceSegment.id == seed_segment_id)
    )
    seed = result.scalar_one_or_none()
    if seed is None:
        return {"error": f"Seed segment {seed_segment_id} not found"}

    all_result = await db.execute(
        select(AudienceSegment).where(AudienceSegment.id != seed_segment_id)
    )
    candidates = all_result.scalars().all()

    if not candidates:
        return {
            "seed": _segment_to_dict(seed),
            "lookalikes": [],
            "note": "No candidate segments available",
        }

    rule_keys = _collect_rule_keys(seed, candidates)
    seed_vec = _rules_to_vector(seed.rules, rule_keys)

    lookalikes: list[dict[str, Any]] = []
    for candidate in candidates:
        cand_vec = _rules_to_vector(candidate.rules, rule_keys)
        sim = _cosine_similarity(seed_vec, cand_vec)
        if sim >= similarity_threshold:
            lookalikes.append({
                "segment": _segment_to_dict(candidate),
                "similarity_score": round(sim, 4),
            })

    lookalikes.sort(key=lambda x: x["similarity_score"], reverse=True)
    lookalikes = lookalikes[:top_k]

    return {
        "seed": _segment_to_dict(seed),
        "lookalikes": lookalikes,
        "top_k": top_k,
        "threshold": similarity_threshold,
    }


async def update_segment(
    db: AsyncSession, segment_id: int, data: dict[str, Any]
) -> Optional[dict[str, Any]]:
    """Update an existing audience segment."""
    result = await db.execute(
        select(AudienceSegment).where(AudienceSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        return None

    for key, value in data.items():
        if value is not None and hasattr(segment, key):
            setattr(segment, key, value)

    if "rules" in data and data["rules"] is not None:
        segment.member_count = _estimate_member_count(segment.rules)

    await db.flush()
    await db.refresh(segment)
    return _segment_to_dict(segment)


async def delete_segment(db: AsyncSession, segment_id: int) -> bool:
    """Delete an audience segment. Returns True if deleted."""
    result = await db.execute(
        select(AudienceSegment).where(AudienceSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        return False
    await db.delete(segment)
    await db.flush()
    return True


# ── helpers ─────────────────────────────────────────────────────────────
def _segment_to_dict(segment: AudienceSegment) -> dict[str, Any]:
    return {
        "id": segment.id,
        "name": segment.name,
        "description": segment.description,
        "rules": segment.rules,
        "member_count": segment.member_count or 0,
        "avg_ctr": segment.avg_ctr or 0.0,
        "avg_cvr": segment.avg_cvr or 0.0,
        "roas": segment.roas or 0.0,
        "seed_audience_id": segment.seed_audience_id,
        "labels": segment.labels,
        "created_at": segment.created_at.isoformat() if segment.created_at else None,
        "updated_at": segment.updated_at.isoformat() if segment.updated_at else None,
    }


def _estimate_member_count(rules: dict[str, Any]) -> int:
    """Rough member-count estimate based on rule breadth."""
    if not rules:
        return 0
    base = 500_000
    score = 1.0
    if "age" in rules and isinstance(rules["age"], list):
        age_range = max(rules["age"]) - min(rules["age"])
        score *= age_range / 50.0
    if "gender" in rules and rules["gender"] != "all":
        score *= 0.5
    if "interests" in rules and isinstance(rules["interests"], list):
        score *= min(len(rules["interests"]), 5) / 5.0
    if "regions" in rules and isinstance(rules["regions"], list):
        score *= len(rules["regions"]) / 10.0
    return max(1_000, int(base * score))


def _empty_stats(segment: AudienceSegment) -> dict[str, Any]:
    return {
        "segment_id": segment.id,
        "segment_name": segment.name,
        "member_count": segment.member_count or 0,
        "impressions": 0, "clicks": 0, "conversions": 0,
        "spend": 0.0, "revenue": 0.0,
        "ctr": 0.0, "cvr": 0.0, "cpc": 0.0, "cpa": 0.0, "roas": 0.0,
    }


def _collect_rule_keys(
    seed: AudienceSegment, candidates: list[AudienceSegment]
) -> list[str]:
    keys: set[str] = set()
    for rules in [seed.rules] + [c.rules for c in candidates]:
        if not rules or not isinstance(rules, dict):
            continue
        for k, v in rules.items():
            if isinstance(v, list):
                for item in v:
                    keys.add(f"{k}:{item}")
            else:
                keys.add(f"{k}:{v}")
    return sorted(keys)


def _rules_to_vector(rules: Optional[dict[str, Any]], rule_keys: list[str]) -> np.ndarray:
    vec = np.zeros(len(rule_keys), dtype=np.float64)
    if not rules or not isinstance(rules, dict):
        return vec
    for k, v in rules.items():
        if isinstance(v, list):
            for item in v:
                key = f"{k}:{item}"
                if key in rule_keys:
                    vec[rule_keys.index(key)] = 1.0
        else:
            key = f"{k}:{v}"
            if key in rule_keys:
                vec[rule_keys.index(key)] = 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
