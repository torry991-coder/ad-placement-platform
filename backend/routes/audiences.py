"""Audiences REST API — audience segment CRUD + stats + lookalike expansion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import (
    AudienceSegmentCreate,
    AudienceSegmentResponse,
    AudienceSegmentUpdate,
    LookalikeResponse,
)
from backend.services import audience_service

router = APIRouter(prefix="/api/audiences", tags=["audiences"])


@router.get("/", response_model=dict)
async def list_audiences(
    search: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all audience segments."""
    audiences, total = await audience_service.list_segments(
        db, search=search, offset=offset, limit=limit
    )
    return {
        "data": audiences,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.post("/", response_model=dict, status_code=201)
async def create_audience(
    body: AudienceSegmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new audience segment with targeting rules."""
    audience = await audience_service.create_segment(
        db,
        name=body.name,
        rules=body.rules,
        description=body.description,
        seed_audience_id=body.seed_audience_id,
        labels=body.labels,
    )
    return audience


@router.get("/{audience_id}", response_model=dict)
async def get_audience(
    audience_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single audience segment by ID."""
    audience = await audience_service.get_segment(db, audience_id)
    if not audience:
        raise HTTPException(status_code=404, detail="Audience segment not found")
    return audience


@router.patch("/{audience_id}", response_model=dict)
async def update_audience(
    audience_id: int,
    body: AudienceSegmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update audience segment fields."""
    updated = await audience_service.update_segment(
        db, audience_id, body.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Audience segment not found")
    return updated


@router.delete("/{audience_id}", status_code=204)
async def delete_audience(
    audience_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an audience segment."""
    deleted = await audience_service.delete_segment(db, audience_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Audience segment not found")


@router.post("/{audience_id}/calculate-stats")
async def calculate_audience_stats(
    audience_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Calculate estimated stats (member count, avg CTR/CVR, ROAS) for an audience."""
    stats = await audience_service.calculate_segment_stats(db, audience_id)
    return stats


@router.post("/{audience_id}/expand-lookalike")
async def expand_lookalike(
    audience_id: int,
    similarity: float = Query(0.7, ge=0.1, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """Create a lookalike audience by expanding targeting rules from a seed audience."""
    result = await audience_service.expand_lookalike(
        db,
        seed_segment_id=audience_id,
        top_k=5,
        similarity_threshold=similarity,
    )
    return result
