"""AudienceSegment model — custom audience groups with targeting rules."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import relationship

from backend.database import Base


class AudienceSegment(Base):
    __tablename__ = "audience_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=True)

    # Targeting rules (JSON DSL)
    # Example: {"age": [18,35], "gender": "female", "interests": ["fashion","beauty"]}
    rules = Column(JSON, nullable=False)

    # Stats
    member_count = Column(Integer, default=0, comment="预估受众数量")
    avg_ctr = Column(Float, default=0.0)
    avg_cvr = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)

    # Seed audience for lookalike expansion
    seed_audience_id = Column(Integer, nullable=True, comment="种子受众ID(用于Lookalike扩展)")

    # Meta
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
