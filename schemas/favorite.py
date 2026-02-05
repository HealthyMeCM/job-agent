"""Favorite company schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, TimestampMixin


class FavoriteBase(BaseSchema):
    """Base favorite fields."""

    notes: str | None = Field(None, description="User notes")
    priority: int = Field(default=0, description="Sort priority (higher = more important)")


class FavoriteCreate(FavoriteBase):
    """Schema for creating a favorite."""

    company_id: UUID = Field(..., description="Company to favorite")


class FavoriteCompany(FavoriteBase, TimestampMixin):
    """Full favorite schema."""

    id: UUID
    company_id: UUID

    # Populated by joins
    company_name: str | None = None
    company_website: str | None = None
    active_role_count: int | None = None
