"""Role lead (job posting) schemas."""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, EmbeddingVector, TimestampMixin


class RemoteType(str, Enum):
    """Remote work type."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class SeniorityLevel(str, Enum):
    """Inferred seniority level."""

    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    FOUNDING = "founding"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    VP = "vp"
    UNKNOWN = "unknown"


class RoleLeadBase(BaseSchema):
    """Base role lead fields."""

    title: str = Field(..., max_length=255, description="Job title")
    url: str | None = Field(None, max_length=500, description="Job posting URL")
    location: str | None = Field(None, max_length=255, description="Location string")
    remote_type: RemoteType = Field(
        default=RemoteType.UNKNOWN, description="Remote work type"
    )
    level: SeniorityLevel = Field(
        default=SeniorityLevel.UNKNOWN, description="Inferred seniority"
    )
    summary: str | None = Field(None, description="LLM-generated summary")
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")
    posting_date: date | None = Field(None, description="Original posting date")


class RoleLeadCreate(RoleLeadBase):
    """Schema for creating a role lead."""

    company_id: UUID = Field(..., description="Parent company ID")
    raw_text: str | None = Field(None, description="Original posting text")


class RoleLeadUpdate(BaseSchema):
    """Schema for updating a role lead."""

    title: str | None = Field(None, max_length=255)
    url: str | None = Field(None, max_length=500)
    location: str | None = Field(None, max_length=255)
    remote_type: RemoteType | None = None
    level: SeniorityLevel | None = None
    summary: str | None = None
    keywords: list[str] | None = None
    posting_date: date | None = None
    is_active: bool | None = None


class RoleLead(RoleLeadBase, TimestampMixin):
    """Full role lead schema."""

    id: UUID
    company_id: UUID
    first_seen_at: datetime = Field(..., description="First discovery time")
    last_seen_at: datetime = Field(..., description="Last seen in source")
    is_active: bool = Field(default=True, description="Still appears in source")
    embedding: EmbeddingVector | None = Field(None, description="Role embedding vector")
    raw_text: str | None = Field(None, description="Original posting text")

    # Populated by joins
    company_name: str | None = Field(None, description="Parent company name")
