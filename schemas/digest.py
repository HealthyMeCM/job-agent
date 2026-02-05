"""Recommendation digest schemas."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from .base import BaseSchema


class OutreachTarget(BaseSchema):
    """Suggested person to contact."""

    name: str | None = Field(None, description="Person's name if known")
    title: str = Field(..., description="Job title or role")
    source: str | None = Field(None, description="Where we found this info")
    linkedin_hint: str | None = Field(
        None, description="Search hint for LinkedIn (not a URL)"
    )


class OutreachPack(BaseSchema):
    """Outreach suggestions for a recommendation."""

    targets: list[OutreachTarget] = Field(
        default_factory=list, description="Suggested contacts"
    )
    draft_message: str | None = Field(None, description="Draft intro message")
    personalization_hooks: list[str] = Field(
        default_factory=list, description="Personalization ideas"
    )


class DigestItem(BaseSchema):
    """Single item in a recommendation digest."""

    rank: int = Field(..., ge=1, description="Ranking position")
    company_id: UUID
    company_name: str
    role_lead_id: UUID | None = Field(None, description="Specific role if applicable")
    role_title: str | None = None

    # Scoring
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence")
    score_breakdown: dict[str, float] = Field(
        default_factory=dict, description="Individual score components"
    )

    # Rationale
    why_interesting: list[str] = Field(
        ..., min_length=1, max_length=5, description="Reasons this is a good fit"
    )
    why_hiring: list[str] = Field(
        default_factory=list, description="Signals suggesting they're hiring"
    )
    concerns: list[str] = Field(
        default_factory=list, description="Potential concerns or unknowns"
    )

    # Evidence
    evidence_urls: list[str] = Field(
        default_factory=list, description="Supporting URLs"
    )

    # Outreach
    outreach: OutreachPack | None = None


class RecommendationDigestCreate(BaseSchema):
    """Schema for creating a digest."""

    digest_date: date = Field(..., description="Digest date")
    ranked_items: list[DigestItem] = Field(..., description="Ranked recommendations")
    model_version: str | None = Field(None, description="Model/pipeline version")
    config_snapshot: dict[str, Any] = Field(
        default_factory=dict, description="Config used"
    )


class RecommendationDigest(BaseSchema):
    """Full recommendation digest schema."""

    id: UUID
    date: date
    ranked_items: list[DigestItem]
    artifact_path: str | None = Field(None, description="Path to rendered artifact")
    model_version: str | None = None
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
