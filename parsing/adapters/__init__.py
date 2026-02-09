"""Adapter registry for source-type-specific content extraction."""

from __future__ import annotations

from parsing.adapters.base import BaseAdapter, ContentBlock
from parsing.adapters.careers_page import CareersPageAdapter

ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "careers_page": CareersPageAdapter,
}


def get_adapter(source_type: str) -> BaseAdapter | None:
    """Get an adapter instance for the given source type."""
    adapter_cls = ADAPTER_REGISTRY.get(source_type)
    if adapter_cls is None:
        return None
    return adapter_cls()


__all__ = [
    "ADAPTER_REGISTRY",
    "BaseAdapter",
    "ContentBlock",
    "CareersPageAdapter",
    "get_adapter",
]
