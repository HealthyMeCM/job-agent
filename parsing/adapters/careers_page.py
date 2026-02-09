"""Careers page adapter — extracts content from company career pages."""

from __future__ import annotations

from typing import Any

from evidence.snapshot import RawSnapshot
from parsing.adapters.base import BaseAdapter, ContentBlock
from parsing.normalizers import extract_main_content, extract_meta


class CareersPageAdapter(BaseAdapter):
    """Extract content from a careers/company page for LLM parsing."""

    def extract_content(
        self,
        snapshot: RawSnapshot,  # noqa: ARG002
        html_bytes: bytes,
        source_metadata: dict[str, Any],
    ) -> ContentBlock:
        main_text = extract_main_content(html_bytes)
        meta = extract_meta(html_bytes)

        # Pull key_links from meta if present
        key_links: list[str] = []
        raw_links = meta.pop("key_links", [])
        if isinstance(raw_links, list):
            key_links = [str(link) for link in raw_links]

        return ContentBlock(
            main_text=main_text,
            meta=meta,
            key_links=key_links,
            company_hint=source_metadata.get("company"),
        )
