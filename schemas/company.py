"""Company entity schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, EmbeddingVector, TimestampMixin


class CompanyStage(str, Enum):
    """Company funding stage."""

    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D_PLUS = "series_d_plus"
    PUBLIC = "public"
    BOOTSTRAPPED = "bootstrapped"
    UNKNOWN = "unknown"


class CompanyBase(BaseSchema):
    """Base company fields."""

    name: str = Field(..., max_length=255, description="Canonical company name")
    website: str | None = Field(None, max_length=500, description="Company website URL")
    careers_url: str | None = Field(
        None, max_length=500, description="Careers page URL"
    )
    description: str | None = Field(None, description="Company description/summary")
    stage: CompanyStage = Field(
        default=CompanyStage.UNKNOWN, description="Funding stage"
    )
    domain_tags: list[str] = Field(
        default_factory=list, description="Industry/domain tags"
    )


class CompanyCreate(CompanyBase):
    """Schema for creating a company."""

    pass


class CompanyUpdate(BaseSchema):
    """Schema for updating a company (all fields optional)."""

    name: str | None = Field(None, max_length=255)
    website: str | None = Field(None, max_length=500)
    careers_url: str | None = Field(None, max_length=500)
    description: str | None = None
    stage: CompanyStage | None = None
    domain_tags: list[str] | None = None


class Company(CompanyBase, TimestampMixin):
    """Full company schema with all fields."""

    id: UUID
    embedding: EmbeddingVector | None = Field(
        None, description="Company embedding vector"
    )

    # Computed/aggregated fields (populated by queries)
    active_role_count: int | None = Field(
        None, description="Number of active role leads"
    )
    latest_signal_date: datetime | None = Field(
        None, description="Date of most recent signal"
    )
    is_favorited: bool = Field(default=False, description="User has favorited")
