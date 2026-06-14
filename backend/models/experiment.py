"""Experiment model — A/B tests with statistical analysis."""

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
)

from backend.database import Base
from backend.models.enums import ExperimentStatus, ExperimentType


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    experiment_type = Column(
        Enum(ExperimentType), default=ExperimentType.AB_TEST, nullable=False
    )
    status = Column(
        Enum(ExperimentStatus), default=ExperimentStatus.DRAFT, nullable=False
    )

    # Variants
    control_campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    variant_campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    traffic_split = Column(
        Float, default=50.0, comment="实验组流量比例 (0-100)"
    )

    # Results (populated by analysis engine)
    results = Column(JSON, nullable=True, comment="统计检验结果JSON")
    is_significant = Column(Boolean, default=False, comment="是否达到统计显著性")
    confidence_level = Column(Float, nullable=True, comment="置信度")
    winner_variant = Column(String(50), nullable=True, comment='"control" / "variant"')

    # Schedule
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    auto_stop = Column(
        Boolean, default=True, comment="达到显著性时自动停止"
    )

    # Notes
    hypothesis = Column(String(500), nullable=True)

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
