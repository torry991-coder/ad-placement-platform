"""PerformanceMetric model — hourly/daily performance snapshots."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Time bucket
    date = Column(String(10), nullable=False, comment="YYYY-MM-DD")
    hour = Column(Integer, nullable=True, comment="0-23, NULL = daily aggregate")
    platform = Column(String(20), nullable=True, comment="simulated / google / meta / tiktok")

    # Core metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    spend = Column(Float, default=0.0)
    revenue = Column(Float, default=0.0)

    # Derived metrics
    ctr = Column(Float, nullable=True, comment="Click-through rate %")
    cvr = Column(Float, nullable=True, comment="Conversion rate %")
    cpc = Column(Float, nullable=True, comment="Cost per click")
    cpa = Column(Float, nullable=True, comment="Cost per acquisition")
    roas = Column(Float, nullable=True, comment="Return on ad spend")

    # Quality signals
    quality_score = Column(Float, nullable=True, comment="质量分 1-10")
    bounce_rate = Column(Float, nullable=True, comment="跳出率")

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    campaign = relationship("Campaign", back_populates="performance")
