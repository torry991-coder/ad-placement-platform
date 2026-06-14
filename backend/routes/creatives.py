"""Creative REST API — creative asset CRUD + rotation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.creative import Creative
from backend.schemas import CreativeResponse

router = APIRouter(prefix="/api/creatives", tags=["creatives"])


@router.get("/", response_model=dict)
async def list_creatives(
    ad_group_id: int | None = Query(None),
    creative_type: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List creatives with optional filters."""
    query = select(Creative)
    count_q = select(func.count(Creative.id))

    if ad_group_id:
        query = query.where(Creative.ad_group_id == ad_group_id)
        count_q = count_q.where(Creative.ad_group_id == ad_group_id)
    if creative_type:
        query = query.where(Creative.creative_type == creative_type)
        count_q = count_q.where(Creative.creative_type == creative_type)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        query.order_by(Creative.updated_at.desc()).offset(offset).limit(limit)
    )
    creatives = result.scalars().all()

    return {
        "data": [CreativeResponse.model_validate(c).model_dump() for c in creatives],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.post("/", response_model=CreativeResponse, status_code=201)
async def create_creative(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Create a new creative asset."""
    creative = Creative(
        ad_group_id=body.get("ad_group_id"),
        name=body.get("name", "New Creative"),
        creative_type=body.get("creative_type", "text"),
        headline=body.get("headline"),
        description=body.get("description"),
        call_to_action=body.get("call_to_action"),
        image_url=body.get("image_url"),
        video_url=body.get("video_url"),
        landing_url=body.get("landing_url"),
    )
    db.add(creative)
    await db.flush()
    await db.refresh(creative)
    return CreativeResponse.model_validate(creative)


@router.get("/{creative_id}", response_model=CreativeResponse)
async def get_creative(creative_id: int, db: AsyncSession = Depends(get_db)):
    creative = (await db.execute(
        select(Creative).where(Creative.id == creative_id)
    )).scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")
    return CreativeResponse.model_validate(creative)


@router.patch("/{creative_id}", response_model=CreativeResponse)
async def update_creative(
    creative_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    creative = (await db.execute(
        select(Creative).where(Creative.id == creative_id)
    )).scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    for key, value in body.items():
        if value is not None and hasattr(creative, key):
            setattr(creative, key, value)

    await db.flush()
    await db.refresh(creative)
    return CreativeResponse.model_validate(creative)


@router.delete("/{creative_id}", status_code=204)
async def delete_creative(creative_id: int, db: AsyncSession = Depends(get_db)):
    creative = (await db.execute(
        select(Creative).where(Creative.id == creative_id)
    )).scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")
    await db.delete(creative)
    await db.flush()
