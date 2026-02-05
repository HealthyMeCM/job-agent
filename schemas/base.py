"""Base schema utilities and common types."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for created_at/updated_at timestamps."""

    created_at: datetime
    updated_at: datetime | None = None


# Common field types
HttpUrl = Annotated[str, Field(max_length=500, pattern=r"^https?://")]
EmbeddingVector = list[float]  # 1536 dimensions for OpenAI embeddings
