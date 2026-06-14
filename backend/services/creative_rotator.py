"""Creative rotation engine with fatigue detection.

Implements intelligent creative selection that balances performance
(CTR/CVR) against fatigue avoidance. Also provides fatigue scoring
and automatic rotation actions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.creative import Creative

# ── constants ───────────────────────────────────────────────────────────
FATIGUE_IMPRESSION_THRESHOLD = 1000
FATIGUE_RECENCY_HOURS = 4
FATIGUE_DECAY_HALF_LIFE_HOURS = 24


# ── public API ──────────────────────────────────────────────────────────
async def get_next_creative(ad_group_id: int, db: AsyncSession) -> dict[str, Any]:
    """Select the best creative for an ad group, balancing performance and fatigue.

    Scoring: score = (ctr_norm + cvr_norm) / 2 * fatigue_multiplier.
    """
    result = await db.execute(
        select(Creative).where(
            and_(Creative.ad_group_id == ad_group_id, Creative.is_active == True)
        )
    )
    creatives = result.scalars().all()

    if not creatives:
        return {
            "ad_group_id": ad_group_id,
            "creative_id": None,
            "error": "No active creatives found",
            "alternatives": [],
        }

    scored: list[dict[str, Any]] = []
    ctrs = np.array([c.ctr or 0.0 for c in creatives], dtype=np.float64)
    cvrs = np.array([c.cvr or 0.0 for c in creatives], dtype=np.float64)
    ctr_max = float(ctrs.max()) if ctrs.max() > 0 else 1.0
    cvr_max = float(cvrs.max()) if cvrs.max() > 0 else 1.0
    now = datetime.now(timezone.utc)

    for i, creative in enumerate(creatives):
        ctr_norm = float(ctrs[i]) / ctr_max if ctr_max > 0 else 0.0
        cvr_norm = float(cvrs[i]) / cvr_max if cvr_max > 0 else 0.0
        fatigue = _calculate_fatigue_for_creative(creative, now)
        fatigue_mult = 1.0 - (fatigue / 100.0) * 0.7
        score = (ctr_norm * 0.5 + cvr_norm * 0.5) * max(fatigue_mult, 0.1)

        scored.append({
            "creative_id": creative.id,
            "creative_name": creative.name,
            "creative_type": creative.creative_type.value if creative.creative_type else "text",
            "score": round(score, 4),
            "ctr": round(creative.ctr or 0.0, 4),
            "cvr": round(creative.cvr or 0.0, 4),
            "fatigue_score": round(fatigue, 2),
            "impressions": creative.impressions or 0,
            "last_shown_at": creative.last_shown_at.isoformat() if creative.last_shown_at else None,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    best = scored[0]
    alternatives = scored[1:4] if len(scored) > 1 else []

    if best["fatigue_score"] < 30:
        reason = "optimal"
    elif best["fatigue_score"] < 60:
        reason = "acceptable"
    else:
        reason = "fatigued_but_best_available"

    return {
        "ad_group_id": ad_group_id,
        "creative_id": best["creative_id"],
        "creative_name": best["creative_name"],
        "score": best["score"],
        "ctr": best["ctr"],
        "cvr": best["cvr"],
        "fatigue_score": best["fatigue_score"],
        "reason": reason,
        "alternatives": alternatives,
    }


async def calculate_fatigue(creative_id: int, db: AsyncSession) -> dict[str, Any]:
    """Calculate fatigue score for a single creative (0-100).

    Factors: impression count relative to threshold, recency of last impression,
    time-decay since last shown.
    """
    result = await db.execute(
        select(Creative).where(Creative.id == creative_id)
    )
    creative = result.scalar_one_or_none()
    if creative is None:
        return {"error": f"Creative {creative_id} not found"}

    now = datetime.now(timezone.utc)
    fatigue = _calculate_fatigue_for_creative(creative, now)

    impression_ratio = (creative.impressions or 0) / FATIGUE_IMPRESSION_THRESHOLD
    impression_penalty = min(impression_ratio * 50.0, 50.0)

    hours_since_shown = (
        (now - creative.last_shown_at).total_seconds() / 3600.0
        if creative.last_shown_at else 999.0
    )
    recency_penalty = max(0.0, 50.0 * (1.0 - hours_since_shown / FATIGUE_RECENCY_HOURS))

    return {
        "creative_id": creative.id,
        "creative_name": creative.name,
        "fatigue_score": round(fatigue, 2),
        "factors": {
            "impressions": creative.impressions or 0,
            "impression_threshold": FATIGUE_IMPRESSION_THRESHOLD,
            "impression_penalty": round(impression_penalty, 2),
            "hours_since_last_shown": round(hours_since_shown, 2),
            "recency_hours_threshold": FATIGUE_RECENCY_HOURS,
            "recency_penalty": round(recency_penalty, 2),
            "decay_half_life_hours": FATIGUE_DECAY_HALF_LIFE_HOURS,
        },
        "recommendation": (
            "rotate_now" if fatigue > 70
            else "monitor" if fatigue > 40
            else "ok"
        ),
    }


async def auto_rotate(ad_group_id: int, db: AsyncSession) -> dict[str, Any]:
    """Automatically determine which creatives to pause/activate for rotation.

    - Creatives with fatigue > 70: recommend pause.
    - Creatives with fatigue < 30 and good performance: recommend activate.
    - Underperforming creatives: recommend deactivate.
    """
    result = await db.execute(
        select(Creative).where(Creative.ad_group_id == ad_group_id)
    )
    creatives = result.scalars().all()

    if not creatives:
        return {"ad_group_id": ad_group_id, "actions": [], "error": "No creatives found"}

    now = datetime.now(timezone.utc)
    ctrs = np.array([c.ctr or 0.0 for c in creatives], dtype=np.float64)
    ctr_median = float(np.median(ctrs)) if len(ctrs) > 0 else 0.0

    actions: list[dict[str, Any]] = []

    for creative in creatives:
        fatigue = _calculate_fatigue_for_creative(creative, now)
        action = None

        if fatigue > 70 and creative.is_active:
            action = {
                "creative_id": creative.id,
                "creative_name": creative.name,
                "action": "pause",
                "reason": f"High fatigue ({fatigue:.1f}/100)",
                "fatigue_score": round(fatigue, 2),
                "ctr": round(creative.ctr or 0.0, 4),
            }
        elif fatigue < 30 and not creative.is_active:
            action = {
                "creative_id": creative.id,
                "creative_name": creative.name,
                "action": "activate",
                "reason": f"Low fatigue ({fatigue:.1f}/100), ready for rotation",
                "fatigue_score": round(fatigue, 2),
                "ctr": round(creative.ctr or 0.0, 4),
            }
        elif (
            creative.is_active
            and (creative.ctr or 0.0) < ctr_median * 0.5
            and (creative.impressions or 0) > 500
        ):
            action = {
                "creative_id": creative.id,
                "creative_name": creative.name,
                "action": "deactivate",
                "reason": f"Underperforming (CTR {creative.ctr:.4f} < median {ctr_median:.4f})",
                "fatigue_score": round(fatigue, 2),
                "ctr": round(creative.ctr or 0.0, 4),
            }

        if action:
            actions.append(action)

    # Apply the actions
    for action in actions:
        creative_id = action["creative_id"]
        if action["action"] in ("pause", "deactivate"):
            await db.execute(
                update(Creative).where(Creative.id == creative_id).values(is_active=False, updated_at=now)
            )
        elif action["action"] == "activate":
            await db.execute(
                update(Creative).where(Creative.id == creative_id).values(is_active=True, updated_at=now)
            )

    await db.flush()

    return {
        "ad_group_id": ad_group_id,
        "total_creatives": len(creatives),
        "actions": actions,
        "summary": {
            "paused": sum(1 for a in actions if a["action"] == "pause"),
            "activated": sum(1 for a in actions if a["action"] == "activate"),
            "deactivated": sum(1 for a in actions if a["action"] == "deactivate"),
        },
    }


# ── helpers ─────────────────────────────────────────────────────────────
def _calculate_fatigue_for_creative(creative: Creative, now: datetime) -> float:
    """Internal fatigue calculation for a single creative. Returns 0-100."""
    impressions = creative.impressions or 0
    last_shown = creative.last_shown_at

    if impressions >= FATIGUE_IMPRESSION_THRESHOLD:
        impression_penalty = 50.0
    else:
        impression_penalty = (impressions / FATIGUE_IMPRESSION_THRESHOLD) * 50.0

    if last_shown is None:
        recency_penalty = 0.0
    else:
        hours_since = (now - last_shown).total_seconds() / 3600.0
        if hours_since <= FATIGUE_RECENCY_HOURS:
            recency_penalty = 50.0 * (1.0 - hours_since / FATIGUE_RECENCY_HOURS)
        else:
            extra_hours = hours_since - FATIGUE_RECENCY_HOURS
            recency_penalty = max(0.0, 50.0 * (0.5 ** (extra_hours / FATIGUE_DECAY_HALF_LIFE_HOURS)))

    fatigue = min(impression_penalty + recency_penalty, 100.0)
    return max(fatigue, 0.0)
