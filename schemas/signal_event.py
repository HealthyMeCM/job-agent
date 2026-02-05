"""Signal event schemas."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from .base import BaseSchema


class SignalType(str, Enum):
    """Type of hiring signal."""

    JOB_POSTING = "job_posting"
    BLOG = "blog"
    FUNDING = "funding"
    GITHUB = "github"
    NEWS = "news"
    OTHER = "other"


class SignalEventBase(BaseSchema):
    """Base signal event fields."""

    source: str = Field(..., max_length=100, description="Source name")
    event_type: SignalType = Field(..., description="Signal type")
    timestamp: datetime = Field(..., description="Event timestamp")
    evidence_url: str | None = Field(None, max_length=500, description="Source URL")
    extracted_text: str | None = Field(None, description="Relevant extracted text")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional structured data"
    )


class SignalEventCreate(SignalEventBase):
    """Schema for creating a signal event."""

    company_id: UUID = Field(..., description="Related company ID")


class SignalEvent(SignalEventBase):
    """Full signal event schema."""

    id: UUID
    company_id: UUID
    created_at: datetime

    # Populated by joins
    company_name: str | None = Field(None, description="Related company name")
