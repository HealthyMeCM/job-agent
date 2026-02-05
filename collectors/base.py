"""Base collector interface and common types."""

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field


class RawJobPosting(BaseModel):
    """Raw job posting data from a collector."""

    source: str = Field(..., description="Source identifier (e.g., 'greenhouse')")
    source_id: str = Field(..., description="Unique ID within the source")
    company_name: str = Field(..., description="Company name as found in source")
    title: str = Field(..., description="Job title")
    url: str = Field(..., description="URL to the job posting")
    location: str | None = Field(None, description="Location string")
    description_html: str | None = Field(None, description="Raw HTML description")
    description_text: str | None = Field(None, description="Plain text description")
    posted_at: datetime | None = Field(None, description="Posting date if available")
    collected_at: datetime = Field(
        default_factory=datetime.utcnow, description="Collection timestamp"
    )
    raw_data: dict | None = Field(None, description="Original raw data from source")


class BaseCollector(ABC):
    """Abstract base class for all collectors."""

    source_name: str = "base"

    def __init__(self, config: dict | None = None):
        """Initialize collector with optional config."""
        self.config = config or {}

    @abstractmethod
    async def collect(self) -> list[RawJobPosting]:
        """
        Collect job postings from this source.

        Returns:
            List of raw job postings
        """
        pass

    @abstractmethod
    async def collect_for_company(self, company_id: str) -> list[RawJobPosting]:
        """
        Collect job postings for a specific company.

        Args:
            company_id: Company identifier (e.g., board_id for ATS)

        Returns:
            List of raw job postings for that company
        """
        pass
