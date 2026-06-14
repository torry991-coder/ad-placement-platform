"""BudgetLog model — hourly budget consumption tracking for pacing."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from backend.database import Base


class BudgetLog(Base):
    __tablename__ = "budget_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Time bucket
    date = Column(String(10), nullable=False, comment="YYYY-MM-DD")
    hour = Column(Integer, nullable=False, comment="0-23")

    # Spend
    spend = Column(Float, default=0.0, comment="本时段消耗 (¥)")
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    # Derived
    cpc = Column(Float, nullable=True)
    ctr = Column(Float, nullable=True)
    roas = Column(Float, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
