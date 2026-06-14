"""Bidding REST API — real-time auction endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import (
    AuctionRequest,
    AuctionResponse,
    BatchAuctionRequest,
    BatchAuctionResponse,
)
from backend.services.bidding_engine import get_bidding_engine, AuctionContext
from backend.services.campaign_service import get_campaign

router = APIRouter(prefix="/api/bidding", tags=["bidding"])

AVAILABLE_STRATEGIES = [
    {
        "id": "max_conversions",
        "name": "Max Conversions",
        "description": "Auto-optimize bids for the most conversions within your daily budget",
        "requires_target_cpa": False,
        "requires_target_roas": False,
    },
    {
        "id": "target_cpa",
        "name": "Target CPA",
        "description": "Set bids to maintain average cost-per-acquisition at or below your target",
        "requires_target_cpa": True,
        "requires_target_roas": False,
    },
    {
        "id": "target_roas",
        "name": "Target ROAS",
        "description": "Set bids to achieve a target return-on-ad-spend",
        "requires_target_cpa": False,
        "requires_target_roas": True,
    },
    {
        "id": "enhanced_cpc",
        "name": "Enhanced CPC",
        "description": "Semi-automatic CPC with ML-powered bid adjustments based on conversion likelihood",
        "requires_target_cpa": False,
        "requires_target_roas": False,
    },
    {
        "id": "manual_cpc",
        "name": "Manual CPC",
        "description": "Fixed cost-per-click — you set the max CPC, we bid that amount",
        "requires_target_cpa": False,
        "requires_target_roas": False,
    },
]


@router.get("/strategies")
async def list_strategies():
    """List all available bid strategies with descriptions and requirements."""
    return {"strategies": AVAILABLE_STRATEGIES}


@router.post("/auction", response_model=AuctionResponse)
async def run_auction(
    body: AuctionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run a single real-time auction simulation.

    Fetches campaign context from DB to enrich the auction with actual
    campaign metrics (CTR, CVR, quality score).
    """
    engine = get_bidding_engine()

    # Look up campaign for enriched context
    campaign = await get_campaign(db, body.campaign_id)
    campaign_ctr = 3.5
    campaign_cvr = 4.0
    if campaign:
        campaign_ctr = getattr(campaign, "ctr", 3.5) or 3.5
        campaign_cvr = getattr(campaign, "cvr", 4.0) or 4.0

    ctx = AuctionContext(
        campaign_id=body.campaign_id,
        ad_group_id=body.ad_group_id,
        daily_budget=body.daily_budget,
        budget_spent_today=body.budget_spent_today,
        bid_strategy=body.bid_strategy,
        target_cpa=body.target_cpa,
        target_roas=body.target_roas,
        max_cpc=body.max_cpc,
        campaign_ctr=campaign_ctr,
        campaign_cvr=campaign_cvr,
        age_range=body.age_range,
        gender=body.gender,
        device=body.device,
        platform=body.platform,
        hour=body.hour,
    )

    try:
        result = engine.bid(ctx)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Bidding failed: {exc}",
        )

    return AuctionResponse(
        bid_amount=result.bid_amount,
        predicted_ctr=result.predicted_ctr,
        predicted_cvr=result.predicted_cvr,
        ad_rank=result.ad_rank,
        won=result.won,
        win_price=result.win_price,
        estimated_conversion_value=result.estimated_conversion_value,
        model_used=result.model_used,
    )


@router.post("/batch", response_model=BatchAuctionResponse)
async def run_batch_auctions(
    body: BatchAuctionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run multiple auction simulations in a single batch (max 100)."""
    engine = get_bidding_engine()
    contexts: list[AuctionContext] = []

    for req in body.auctions:
        campaign = await get_campaign(db, req.campaign_id)
        campaign_ctr = 3.5
        campaign_cvr = 4.0
        if campaign:
            campaign_ctr = getattr(campaign, "ctr", 3.5) or 3.5
            campaign_cvr = getattr(campaign, "cvr", 4.0) or 4.0

        ctx = AuctionContext(
            campaign_id=req.campaign_id,
            ad_group_id=req.ad_group_id,
            daily_budget=req.daily_budget,
            budget_spent_today=req.budget_spent_today,
            bid_strategy=req.bid_strategy,
            target_cpa=req.target_cpa,
            target_roas=req.target_roas,
            max_cpc=req.max_cpc,
            campaign_ctr=campaign_ctr,
            campaign_cvr=campaign_cvr,
            age_range=req.age_range,
            gender=req.gender,
            device=req.device,
            platform=req.platform,
            hour=req.hour,
        )
        contexts.append(ctx)

    try:
        results = engine.batch_bid(contexts)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Batch bidding failed: {exc}",
        )

    won_count = sum(1 for r in results if r.won)
    total_cost = sum(r.win_price for r in results)

    return BatchAuctionResponse(
        results=[
            AuctionResponse(
                bid_amount=r.bid_amount,
                predicted_ctr=r.predicted_ctr,
                predicted_cvr=r.predicted_cvr,
                ad_rank=r.ad_rank,
                won=r.won,
                win_price=r.win_price,
                estimated_conversion_value=r.estimated_conversion_value,
                model_used=r.model_used,
            )
            for r in results
        ],
        total_auctions=len(results),
        won_count=won_count,
        total_cost=round(total_cost, 4),
    )
