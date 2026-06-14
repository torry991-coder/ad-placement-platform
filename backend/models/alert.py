"""AlertRule model — custom alert rules with auto-actions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    JSON,
    String,
    Text,
)

from backend.database import Base
from backend.models.enums import AlertAction, AlertSeverity


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    is_enabled = Column(Boolean, default=True)

    # Condition as JSON
    # Example: {"metric": "ctr", "operator": "<", "threshold": 0.5, "window_hours": 24}
    condition = Column(JSON, nullable=False)

    severity = Column(Enum(AlertSeverity), default=AlertSeverity.WARNING, nullable=False)
    action = Column(Enum(AlertAction), default=AlertAction.NOTIFY, nullable=False)

    # Scope
    scope_type = Column(String(20), default="campaign", comment="campaign / ad_group / account")
    scope_id = Column(Integer, nullable=True, comment="Target entity ID")

    # Notification
    notify_channels = Column(JSON, nullable=True, comment='["ui","email","webhook"]')
    webhook_url = Column(String(500), nullable=True)

    # Cooldown (minutes)
    cooldown_minutes = Column(Integer, default=60)

    # Stats
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, default=0)

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
