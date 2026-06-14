"""
Real-time Bidding Engine.

Supports 5 bid strategies:
  - max_conversions  : Auto-optimize for most conversions within budget
  - target_cpa       : Maintain average CPA ≤ target
  - target_roas      : Hit target ROAS (revenue/spend)
  - enhanced_cpc     : Semi-automatic CPC with ML boost
  - manual_cpc       : Fixed CPC bid

Simulates ad auction: quality score × bid → ad rank → winner placement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import random as _random
import math

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False

from backend.services.ml_engine import MLEngine, PredictionResult, get_ml_engine
from backend.cache import cache_get, cache_set, get_cache_stats


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AuctionContext:
    """Context passed to the bidding engine for a single auction."""
    campaign_id: int
    ad_group_id: int
    daily_budget: float
    budget_spent_today: float
    bid_strategy: str                           # max_conversions | target_cpa | ...
    target_cpa: Optional[float] = None
    target_roas: Optional[float] = None
    max_cpc: Optional[float] = None
    campaign_ctr: float = 3.5
    campaign_cvr: float = 4.0
    quality_score: float = 6.0                  # 1-10
    age_range: Optional[list[int]] = None
    gender: Optional[str] = None
    device: str = "mobile"
    platform: str = "simulated"
    hour: Optional[int] = None


@dataclass
class AuctionResult:
    """Result of a single auction."""
    bid_amount: float                           # Actual bid placed (¥)
    predicted_ctr: float                        # Predicted CTR %
    predicted_cvr: float                        # Predicted CVR %
    ad_rank: float                              # bid × quality_score × predicted_ctr
    won: bool                                   # Did we win the auction?
    win_price: float                            # Second-price auction cost (¥)
    estimated_conversion_value: float           # Expected revenue from this impression
    model_used: str                             # "xgboost" | "statistical"
    cache_hit: bool = False                     # Was prediction served from cache?


@dataclass
class Competitor:
    """Simulated competitor in the auction."""
    name: str
    base_bid: float
    quality_score: float


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class BiddingEngine:
    """Real-time bidding engine with 5 strategies + simulated auction."""

    # Simulated competitors (for auction dynamics) — initialised in __init__
    _competitors: list[Competitor]

    def __init__(self, ml_engine: Optional[MLEngine] = None) -> None:
        self.ml = ml_engine or get_ml_engine()
        self._competitors = [
            Competitor("Brand-A", 1.5, 7.0),
            Competitor("Brand-B", 2.0, 6.5),
            Competitor("Competitor-X", 1.0, 5.0),
            Competitor("Competitor-Y", 3.0, 8.0),
        ]

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------
    def bid(self, ctx: AuctionContext) -> AuctionResult:
        """Main entry point: calculate bid and simulate auction outcome."""
        # ── Prediction caching ──────────────────────────────────────────
        context_hash = hash((
            tuple(ctx.age_range or []),
            ctx.gender,
            ctx.device,
            ctx.platform,
            ctx.hour,
            round(ctx.campaign_ctr, 3),
            round(ctx.campaign_cvr, 3),
        ))
        cache_key = f"pred:{ctx.campaign_id}:{ctx.ad_group_id}:{context_hash}"

        cache_hit = False
        cached = cache_get(cache_key)
        if cached is not None:
            pred = PredictionResult(
                ctr=cached[0],
                cvr=cached[1],
                confidence=cached[2],
                model_used=cached[3],
            )
            cache_hit = True
        else:
            # 1. Predict CTR / CVR
            pred = self.ml.predict(
                campaign_id=ctx.campaign_id,
                ad_group_id=ctx.ad_group_id,
                age_range=ctx.age_range,
                gender=ctx.gender,
                device=ctx.device,
                platform=ctx.platform,
                hour=ctx.hour,
                campaign_ctr=ctx.campaign_ctr,
                campaign_cvr=ctx.campaign_cvr,
            )
            # Cache for 60 seconds
            cache_set(cache_key, (pred.ctr, pred.cvr, pred.confidence, pred.model_used), ttl_seconds=60)

        # 2. Determine bid amount by strategy
        bid = self._compute_bid(ctx, pred)

        # 3. Cap at max_cpc
        if ctx.max_cpc and bid > ctx.max_cpc:
            bid = ctx.max_cpc

        # 4. Budget check
        remaining = ctx.daily_budget - ctx.budget_spent_today
        if bid > remaining:
            # Reduce bid to stay within budget, but never bid below 0.01
            bid = max(0.01, remaining * 0.5)

        # 5. Simulate auction
        ad_rank = bid * ctx.quality_score * (pred.ctr / 100.0)
        result = self._run_auction(bid, ad_rank, pred, ctx, cache_hit)

        return result

    def batch_bid(
        self,
        contexts: list[AuctionContext],
    ) -> list[AuctionResult]:
        """Run multiple auctions in batch (e.g., for reporting / simulation)."""
        return [self.bid(ctx) for ctx in contexts]

    # ----------------------------------------------------------------
    # Strategy implementations
    # ----------------------------------------------------------------
    def _compute_bid(self, ctx: AuctionContext, pred: PredictionResult) -> float:
        """Route to the correct strategy implementation."""
        strategy = ctx.bid_strategy
        if strategy == "max_conversions":
            return self._bid_max_conversions(pred, ctx)
        if strategy == "target_cpa":
            return self._bid_target_cpa(pred, ctx)
        if strategy == "target_roas":
            return self._bid_target_roas(pred, ctx)
        if strategy == "enhanced_cpc":
            return self._bid_enhanced_cpc(pred, ctx)
        if strategy == "manual_cpc":
            return self._bid_manual_cpc(ctx)
        # Default fallback
        return self._bid_max_conversions(pred, ctx)

    def _bid_max_conversions(
        self, pred: PredictionResult, ctx: AuctionContext
    ) -> float:
        """Aggressive bid to maximise conversion volume.

        Bid = estimated conversion value × conversion probability.
        """
        est_value = (ctx.target_cpa or 50.0) * (pred.cvr / 100.0)
        # Add exploration bonus for low-confidence predictions
        explore = (1.0 - pred.confidence) * 0.3
        return est_value * (1.0 + explore)

    def _bid_target_cpa(
        self, pred: PredictionResult, ctx: AuctionContext
    ) -> float:
        """Bid to keep CPA ≤ target.

        Bid = target_cpa × predicted_cvr — only bid when CPA is likely acceptable.
        """
        target = ctx.target_cpa or 50.0
        bid = target * (pred.cvr / 100.0)
        # Reduce bid if predicted conversion probability is very low
        if pred.cvr < 1.0:
            bid *= 0.3
        return bid

    def _bid_target_roas(
        self, pred: PredictionResult, ctx: AuctionContext
    ) -> float:
        """Bid to achieve a target ROAS.

        Bid = (estimated_conversion_value × predicted_cvr) / target_roas.
        """
        target_roas = ctx.target_roas or 3.0
        est_value = ctx.target_cpa or 100.0
        bid = (est_value * pred.cvr / 100.0) / target_roas
        return bid

    def _bid_enhanced_cpc(
        self, pred: PredictionResult, ctx: AuctionContext
    ) -> float:
        """Semi-automatic CPC with ML enhancement.

        Start from a base CPC and adjust up/down based on conversion likelihood.
        """
        base = ctx.max_cpc or 2.0
        factor = 1.0
        # Higher conversion probability → bid more
        if pred.cvr > 5.0:
            factor = 1.3
        elif pred.cvr < 2.0:
            factor = 0.6
        # Lower confidence → less aggressive
        factor *= 0.7 + pred.confidence * 0.3
        return base * factor

    def _bid_manual_cpc(self, ctx: AuctionContext) -> float:
        """Fixed CPC — return max_cpc (or sensible default)."""
        return ctx.max_cpc or 1.0

    # ----------------------------------------------------------------
    # Auction simulation
    # ----------------------------------------------------------------
    def _run_auction(
        self,
        bid: float,
        ad_rank: float,
        pred: PredictionResult,
        ctx: AuctionContext,
        cache_hit: bool = False,
    ) -> AuctionResult:
        """Simulate a second-price auction against competitors."""
        # Competing bids
        competitors = [
            (c.base_bid + _random.gauss(0, 0.3)) * c.quality_score
            for c in self._competitors[: _random.randint(2, 5)]
        ]
        # Add noise to our rank
        noisy_rank = ad_rank * _random.uniform(0.85, 1.15)
        all_ranks = sorted([noisy_rank] + competitors, reverse=True)

        won = noisy_rank == all_ranks[0]

        # Second-price: pay the second-highest rank's bid
        if won and len(all_ranks) > 1:
            win_price = all_ranks[1] / (ctx.quality_score * (pred.ctr / 100.0))
            win_price = round(max(0.01, win_price), 4)
        elif won:
            win_price = round(bid, 4)
        else:
            win_price = 0.0

        est_revenue = (pred.cvr / 100.0) * (ctx.target_cpa or 50.0)

        return AuctionResult(
            bid_amount=round(bid, 4),
            predicted_ctr=pred.ctr,
            predicted_cvr=pred.cvr,
            ad_rank=round(noisy_rank, 4),
            won=won,
            win_price=win_price,
            estimated_conversion_value=round(est_revenue, 2),
            model_used=pred.model_used,
            cache_hit=cache_hit,
        )


# Singleton
_bidding_engine: Optional[BiddingEngine] = None


def get_bidding_engine() -> BiddingEngine:
    global _bidding_engine
    if _bidding_engine is None:
        _bidding_engine = BiddingEngine()
    return _bidding_engine
