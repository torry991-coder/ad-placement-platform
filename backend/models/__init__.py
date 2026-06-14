"""Models package — imports all ORM models so Base.metadata can discover them."""

from backend.models.campaign import Campaign
from backend.models.ad_group import AdGroup
from backend.models.creative import Creative
from backend.models.audience import AudienceSegment
from backend.models.budget import BudgetLog
from backend.models.experiment import Experiment
from backend.models.alert import AlertRule
from backend.models.performance import PerformanceMetric
from backend.models.user import User

__all__ = [
    "Campaign",
    "AdGroup",
    "Creative",
    "AudienceSegment",
    "BudgetLog",
    "Experiment",
    "AlertRule",
    "PerformanceMetric",
    "User",
]
