"""Campaign CRUD service layer."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.campaign import Campaign
from backend.models.enums import CampaignStatus


async def create_campaign(db: AsyncSession, data: dict) -> Campaign:
    campaign = Campaign(**data)
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


async def get_campaign(db: AsyncSession, campaign_id: int) -> Optional[Campaign]:
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    return result.scalar_one_or_none()


async def list_campaigns(
    db: AsyncSession,
    status: Optional[str] = None,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Campaign], int]:
    query = select(Campaign)
    count_query = select(func.count(Campaign.id))

    if status:
        query = query.where(Campaign.status == status)
        count_query = count_query.where(Campaign.status == status)
    if search:
        query = query.where(Campaign.name.ilike(f"%{search}%"))
        count_query = count_query.where(Campaign.name.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(Campaign.updated_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total


async def update_campaign(
    db: AsyncSession, campaign: Campaign, data: dict
) -> Campaign:
    for key, value in data.items():
        if value is not None:
            setattr(campaign, key, value)
    await db.flush()
    await db.refresh(campaign)
    return campaign


async def delete_campaign(db: AsyncSession, campaign: Campaign) -> None:
    await db.delete(campaign)
    await db.flush()


async def get_dashboard_kpis(db: AsyncSession) -> dict:
    """Aggregate dashboard KPIs across all campaigns."""
    result = await db.execute(
        select(
            func.count(Campaign.id).filter(Campaign.status == CampaignStatus.ACTIVE).label("active"),
            func.count(Campaign.id).label("total"),
        )
    )
    row = result.one()
    return {
        "active_campaigns": row.active or 0,
        "total_campaigns": row.total or 0,
    }
