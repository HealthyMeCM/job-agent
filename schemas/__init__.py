"""
Pydantic schemas for Job Agent.

Contract-first design: these schemas define the data contracts
between all system components.
"""

from .company import Company, CompanyCreate, CompanyUpdate
from .role_lead import RoleLead, RoleLeadCreate, RoleLeadUpdate
from .signal_event import SignalEvent, SignalEventCreate
from .digest import RecommendationDigest, DigestItem, OutreachPack
from .feedback import Feedback, FeedbackCreate
from .favorite import FavoriteCompany, FavoriteCreate
from .config import (
    SeedCompaniesConfig,
    TargetTitlesConfig,
    PreferencesConfig,
    SourcesConfig,
)

__all__ = [
    # Core entities
    "Company",
    "CompanyCreate",
    "CompanyUpdate",
    "RoleLead",
    "RoleLeadCreate",
    "RoleLeadUpdate",
    "SignalEvent",
    "SignalEventCreate",
    "RecommendationDigest",
    "DigestItem",
    "OutreachPack",
    "Feedback",
    "FeedbackCreate",
    "FavoriteCompany",
    "FavoriteCreate",
    # Config schemas
    "SeedCompaniesConfig",
    "TargetTitlesConfig",
    "PreferencesConfig",
    "SourcesConfig",
]
