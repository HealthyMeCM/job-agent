"""Base adapter for content extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from evidence.snapshot import RawSnapshot


class ContentBlock(BaseModel):
    """Prepared content for LLM extraction."""

    main_text: str
    meta: dict[str, Any] = Field(default_factory=dict)
    key_links: list[str] = Field(default_factory=list)
    company_hint: str | None = None


class BaseAdapter(ABC):
    """Abstract adapter that extracts content from a snapshot for the LLM."""

    @abstractmethod
    def extract_content(
        self,
        snapshot: RawSnapshot,
        html_bytes: bytes,
        source_metadata: dict[str, Any],
    ) -> ContentBlock:
        """Extract main content text + metadata from raw HTML.

        Adapters are minimal — they prepare text for the LLM,
        not field-level parsing.
        """
