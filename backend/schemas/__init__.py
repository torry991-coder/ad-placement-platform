"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.models.enums import (
    AdGroupStatus,
    BidStrategy,
    CampaignStatus,
    ExperimentStatus,
    ExperimentType,
)

# ── Campaign ─────────────────────────────────────────────────
class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    daily_budget: float = Field(..., gt=0)
    total_budget: Optional[float] = None
    bid_strategy: BidStrategy = BidStrategy.MAX_CONVERSIONS
    target_cpa: Optional[float] = None
    target_roas: Optional[float] = None
    max_cpc: Optional[float] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    platforms: list[str] = ["simulated"]
    notes: Optional[str] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[CampaignStatus] = None
    daily_budget: Optional[float] = Field(None, gt=0)
    total_budget: Optional[float] = None
    bid_strategy: Optional[BidStrategy] = None
    target_cpa: Optional[float] = None
    target_roas: Optional[float] = None
    max_cpc: Optional[float] = None
    end_date: Optional[datetime] = None
    notes: Optional[str] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    status: CampaignStatus
    daily_budget: float
    total_budget: Optional[float]
    bid_strategy: BidStrategy
    target_cpa: Optional[float]
    target_roas: Optional[float]
    max_cpc: Optional[float]
    start_date: datetime
    end_date: Optional[datetime]
    platforms: Optional[list]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── AdGroup ──────────────────────────────────────────────────
class AdGroupCreate(BaseModel):
    campaign_id: int
    name: str = Field(..., min_length=1, max_length=255)
    bid_strategy_override: Optional[str] = None
    max_cpc: Optional[float] = None
    target_cpa: Optional[float] = None
    age_range: Optional[list[int]] = None
    gender: Optional[str] = None
    devices: Optional[list[str]] = None
    regions: Optional[list[str]] = None
    interests: Optional[list[str]] = None
    keywords: Optional[list[str]] = None


class AdGroupResponse(BaseModel):
    id: int
    campaign_id: int
    name: str
    status: AdGroupStatus
    max_cpc: Optional[float]
    target_cpa: Optional[float]
    regions: Optional[list]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Creative ─────────────────────────────────────────────────
class CreativeCreate(BaseModel):
    ad_group_id: int
    name: str = Field(..., max_length=255)
    creative_type: str = "text"
    headline: Optional[str] = None
    description: Optional[str] = None
    call_to_action: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    landing_url: Optional[str] = None


class CreativeResponse(BaseModel):
    id: int
    ad_group_id: int
    name: str
    creative_type: str
    headline: Optional[str]
    description: Optional[str]
    ctr: float
    cvr: float
    fatigue_score: float
    is_active: bool

    model_config = {"from_attributes": True}


# ── Experiment ───────────────────────────────────────────────
class ExperimentCreate(BaseModel):
    name: str
    experiment_type: ExperimentType = ExperimentType.AB_TEST
    control_campaign_id: int
    variant_campaign_id: int
    traffic_split: float = Field(50.0, ge=1, le=99)
    start_date: datetime
    end_date: Optional[datetime] = None
    auto_stop: bool = True
    hypothesis: Optional[str] = None


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    traffic_split: Optional[float] = Field(None, ge=1, le=99)
    end_date: Optional[datetime] = None
    hypothesis: Optional[str] = None


class ExperimentResponse(BaseModel):
    id: int
    name: str
    status: ExperimentStatus
    control_campaign_id: int
    variant_campaign_id: int
    traffic_split: float
    results: Optional[dict]
    is_significant: bool
    confidence_level: Optional[float]
    winner_variant: Optional[str]

    model_config = {"from_attributes": True}


class ExperimentResultsResponse(BaseModel):
    experiment_id: int
    name: str
    status: str
    control_metrics: dict = {}
    variant_metrics: dict = {}
    p_value: Optional[float] = None
    confidence_level: Optional[float] = None
    is_significant: bool = False
    winner_variant: Optional[str] = None
    recommendation: Optional[str] = None


# ── Alert ────────────────────────────────────────────────────
class AlertRuleCreate(BaseModel):
    name: str
    condition: dict
    severity: str = "warning"
    action: str = "notify"
    scope_type: str = "campaign"
    scope_id: Optional[int] = None
    notify_channels: list[str] = ["ui"]
    cooldown_minutes: int = 60


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[int] = None
    condition: Optional[dict] = None
    severity: Optional[str] = None
    action: Optional[str] = None
    scope_type: Optional[str] = None
    scope_id: Optional[int] = None
    notify_channels: Optional[list[str]] = None
    webhook_url: Optional[str] = None
    cooldown_minutes: Optional[int] = None


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    is_enabled: bool
    condition: dict
    severity: str
    action: str
    scope_type: str
    scope_id: Optional[int]
    notify_channels: Optional[list]
    webhook_url: Optional[str]
    cooldown_minutes: int
    last_triggered_at: Optional[datetime]
    trigger_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Performance ──────────────────────────────────────────────
class PerformanceSummary(BaseModel):
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_spend: float = 0.0
    total_revenue: float = 0.0
    avg_ctr: float = 0.0
    avg_cvr: float = 0.0
    avg_cpc: float = 0.0
    avg_cpa: float = 0.0
    avg_roas: float = 0.0


# ── Dashboard ────────────────────────────────────────────────
class DashboardKPIs(BaseModel):
    active_campaigns: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_spend: float = 0.0
    total_revenue: float = 0.0
    avg_ctr: float = 0.0
    avg_cvr: float = 0.0
    avg_roas: float = 0.0
    budget_utilization: float = 0.0
    alert_count: int = 0


# ── Bidding ──────────────────────────────────────────────────
class AuctionRequest(BaseModel):
    campaign_id: int
    ad_group_id: int
    daily_budget: float = Field(..., gt=0)
    budget_spent_today: float = 0.0
    bid_strategy: str = "max_conversions"
    target_cpa: Optional[float] = None
    target_roas: Optional[float] = None
    max_cpc: Optional[float] = None
    age_range: Optional[list[int]] = None
    gender: Optional[str] = None
    device: str = "mobile"
    platform: str = "simulated"
    hour: Optional[int] = None


class AuctionResponse(BaseModel):
    bid_amount: float
    predicted_ctr: float
    predicted_cvr: float
    ad_rank: float
    won: bool
    win_price: float
    estimated_conversion_value: float
    model_used: str


class BatchAuctionRequest(BaseModel):
    auctions: list[AuctionRequest] = Field(..., min_length=1, max_length=100)


class BatchAuctionResponse(BaseModel):
    results: list[AuctionResponse]
    total_auctions: int
    won_count: int
    total_cost: float


# ── Analytics ────────────────────────────────────────────────
class TrendPoint(BaseModel):
    date: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0
    ctr: Optional[float] = None
    cvr: Optional[float] = None
    cpc: Optional[float] = None
    roas: Optional[float] = None


class TrendsResponse(BaseModel):
    campaign_id: Optional[int] = None
    granularity: str
    data: list[TrendPoint]


class PlatformBreakdown(BaseModel):
    platform: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0
    ctr: float = 0.0
    cvr: float = 0.0
    roas: float = 0.0


class AnalyticsDashboard(BaseModel):
    active_campaigns: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_spend: float = 0.0
    total_revenue: float = 0.0
    avg_ctr: float = 0.0
    avg_cvr: float = 0.0
    avg_cpc: float = 0.0
    avg_cpa: float = 0.0
    avg_roas: float = 0.0
    budget_utilization: float = 0.0
    platform_breakdown: list[PlatformBreakdown] = []
    daily_trend: list[TrendPoint] = []


# ── Audience ─────────────────────────────────────────────────
class AudienceSegmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    rules: dict = Field(..., description="Targeting rules JSON DSL")
    seed_audience_id: Optional[int] = None
    labels: Optional[list[str]] = None


class AudienceSegmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[dict] = None
    labels: Optional[list[str]] = None


class AudienceSegmentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    rules: dict
    member_count: int
    avg_ctr: float
    avg_cvr: float
    roas: float
    seed_audience_id: Optional[int]
    labels: Optional[list]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LookalikeResponse(BaseModel):
    source_audience_id: int
    expanded_count: int
    similarity_threshold: float
    rules: dict


# ── Report ───────────────────────────────────────────────────
class ReportGenerateRequest(BaseModel):
    report_type: str = "daily"
    campaign_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    metrics: list[str] = ["impressions", "clicks", "conversions", "spend", "revenue"]
    format: str = "json"


class ReportResponse(BaseModel):
    report_id: str
    report_type: str
    generated_at: datetime
    data: dict


# ── Agent ────────────────────────────────────────────────────
class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    campaign_id: Optional[int] = None
    context: Optional[dict] = None


class AgentChatResponse(BaseModel):
    reply: str
    actions: list[dict] = []
    suggestions: list[str] = []
    model_used: str
