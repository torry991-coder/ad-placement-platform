"""Campaign REST API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    DashboardKPIs,
)
from backend.services import campaign_service

router = APIRouter()


@router.get("/", response_model=dict)
async def list_campaigns(
    status: str | None = Query(None),
    search: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List campaigns with optional filtering and search."""
    campaigns, total = await campaign_service.list_campaigns(
        db, status=status, search=search, offset=offset, limit=limit
    )
    return {
        "data": [CampaignResponse.model_validate(c).model_dump() for c in campaigns],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/dashboard", response_model=DashboardKPIs)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Get aggregate dashboard KPIs."""
    kpis = await campaign_service.get_dashboard_kpis(db)
    return DashboardKPIs(**kpis)


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(body: CampaignCreate, db: AsyncSession = Depends(get_db)):
    """Create a new campaign."""
    campaign = await campaign_service.create_campaign(db, body.model_dump())
    return CampaignResponse.model_validate(campaign)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single campaign by ID."""
    campaign = await campaign_service.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update campaign fields."""
    campaign = await campaign_service.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    updated = await campaign_service.update_campaign(
        db, campaign, body.model_dump(exclude_unset=True)
    )
    return CampaignResponse.model_validate(updated)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a campaign and all its children."""
    campaign = await campaign_service.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await campaign_service.delete_campaign(db, campaign)
