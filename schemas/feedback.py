"""Feedback schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from .base import BaseSchema


class FeedbackLabel(str, Enum):
    """User feedback label."""

    POSITIVE = "positive"  # Checkmark
    NEGATIVE = "negative"  # X


class FeedbackTag(str, Enum):
    """Predefined feedback tags for learning."""

    TOO_LATE_STAGE = "too_late_stage"
    TOO_EARLY_STAGE = "too_early_stage"
    NOT_INTERESTING_DOMAIN = "not_interesting_domain"
    COMP_RISK = "comp_risk"  # Compensation concerns
    NOT_CREDIBLE = "not_credible"  # Company seems sketchy
    WRONG_ROLE_TYPE = "wrong_role_type"
    LOCATION_MISMATCH = "location_mismatch"
    ALREADY_APPLIED = "already_applied"
    GREAT_FIT = "great_fit"
    INTERESTING_COMPANY = "interesting_company"
    GOOD_ROLE_MATCH = "good_role_match"


class FeedbackBase(BaseSchema):
    """Base feedback fields."""

    label: FeedbackLabel = Field(..., description="Positive or negative")
    tags: list[FeedbackTag] = Field(default_factory=list, description="Feedback tags")
    note: str | None = Field(None, description="Free-form note")


class FeedbackCreate(FeedbackBase):
    """Schema for creating feedback."""

    digest_id: UUID = Field(..., description="Parent digest ID")
    company_id: UUID = Field(..., description="Rated company")
    role_lead_id: UUID | None = Field(None, description="Specific role (optional)")


class Feedback(FeedbackBase):
    """Full feedback schema."""

    id: UUID
    digest_id: UUID
    company_id: UUID
    role_lead_id: UUID | None = None
    created_at: datetime

    # Populated by joins
    company_name: str | None = None
