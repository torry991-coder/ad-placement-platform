"""Creative model — ad creative assets (copy, images, videos)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.enums import CreativeType


class Creative(Base):
    __tablename__ = "creatives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ad_group_id = Column(
        Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    creative_type = Column(
        Enum(CreativeType), default=CreativeType.TEXT, nullable=False
    )

    # Content
    headline = Column(String(90), nullable=True, comment="标题 (max 30 chars per line, 3 lines)")
    description = Column(String(180), nullable=True, comment="描述")
    call_to_action = Column(String(30), nullable=True, comment="CTA")
    image_url = Column(String(500), nullable=True, comment="图片URL")
    video_url = Column(String(500), nullable=True, comment="视频URL")
    landing_url = Column(String(500), nullable=True, comment="落地页URL")

    # Performance (denormalized snapshot for quick filtering)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0, comment="点击率")
    cvr = Column(Float, default=0.0, comment="转化率")

    # Fatigue tracking
    fatigue_score = Column(Float, default=0.0, comment="疲劳度评分 0-100")
    last_shown_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

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
    ad_group = relationship("AdGroup", back_populates="creatives")
