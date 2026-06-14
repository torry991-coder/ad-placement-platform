"""AdGroup model — sub-division of a campaign with its own targeting & bids."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.enums import AdGroupStatus


class AdGroup(Base):
    __tablename__ = "ad_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    status = Column(Enum(AdGroupStatus), default=AdGroupStatus.ACTIVE, nullable=False)

    # Bidding override (optional — inherits from campaign if unset)
    bid_strategy_override = Column(String(50), nullable=True)
    max_cpc = Column(Float, nullable=True)
    target_cpa = Column(Float, nullable=True)

    # Targeting
    age_range = Column(JSON, nullable=True, comment='[18, 24] or [25, 34, 35, 44]')
    gender = Column(String(20), nullable=True, comment="male / female / all")
    devices = Column(JSON, nullable=True, comment='["mobile","desktop","tablet"]')
    regions = Column(JSON, nullable=True, comment='["US","CN","JP"]')
    interests = Column(JSON, nullable=True, comment='["tech","fashion"]')
    keywords = Column(JSON, nullable=True)

    # Meta
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
    campaign = relationship("Campaign", back_populates="ad_groups")
    creatives = relationship(
        "Creative", back_populates="ad_group", cascade="all, delete-orphan"
    )
