"""SQLAlchemy ORM models for the ad placement platform.

8 core tables: campaigns, ad_groups, creatives, audience_segments,
budget_logs, experiments, alert_rules, performance_metrics.
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

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


# ── Enums ────────────────────────────────────────────────────
class BidStrategy(str, enum.Enum):
    MAX_CONVERSIONS = "max_conversions"
    TARGET_CPA = "target_cpa"
    TARGET_ROAS = "target_roas"
    ENHANCED_CPC = "enhanced_cpc"
    MANUAL_CPC = "manual_cpc"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    LEARNING = "learning"
    ENDED = "ended"


class AdGroupStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    REMOVED = "removed"


class ExperimentType(str, enum.Enum):
    AB_TEST = "ab_test"
    MULTIVARIATE = "multivariate"
    BANDIT = "bandit"


class ExperimentStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertAction(str, enum.Enum):
    NOTIFY = "notify"
    PAUSE_CAMPAIGN = "pause_campaign"
    REDUCE_BUDGET = "reduce_budget"


class AttributionModel(str, enum.Enum):
    LAST_TOUCH = "last_touch"
    FIRST_TOUCH = "first_touch"
    LINEAR = "linear"
    TIME_DECAY = "time_decay"
    POSITION_BASED = "position_based"
    DATA_DRIVEN = "data_driven"


class CreativeType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    RESPONSIVE = "responsive"
    HTML5 = "html5"
