"""Collectors: source planning, HTTP client, and collection adapters."""

from collectors.planner import FetchTask, plan_sources
from collectors.collector import collect
from collectors.http_client import HttpClient

__all__ = [
    "FetchTask",
    "plan_sources",
    "collect",
    "HttpClient",
]
