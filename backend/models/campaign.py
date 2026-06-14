"""Campaign model — top-level advertising campaign."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.enums import BidStrategy, CampaignStatus


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    status = Column(
        Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False
    )

    # Budget
    daily_budget = Column(Float, nullable=False, comment="日预算 (¥)")
    total_budget = Column(Float, nullable=True, comment="总预算 (¥)")

    # Bidding
    bid_strategy = Column(
        Enum(BidStrategy), default=BidStrategy.MAX_CONVERSIONS, nullable=False
    )
    target_cpa = Column(Float, nullable=True, comment="目标CPA")
    target_roas = Column(Float, nullable=True, comment="目标ROAS")
    max_cpc = Column(Float, nullable=True, comment="最高CPC上限")

    # Schedule
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    ad_schedule = Column(JSON, nullable=True, comment="排期: 按日/时段")

    # Platform targeting
    platforms = Column(JSON, nullable=True, comment='["google","meta","tiktok"]')

    # Attribution
    attribution_model = Column(
        String(50), default="last_touch", comment="归因模型"
    )

    # Meta
    notes = Column(Text, nullable=True)
    labels = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    ad_groups = relationship(
        "AdGroup", back_populates="campaign", cascade="all, delete-orphan"
    )
    performance = relationship(
        "PerformanceMetric", back_populates="campaign", cascade="all, delete-orphan"
    )
