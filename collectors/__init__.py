"""
Data collectors for Job Agent.

Each collector is responsible for fetching data from a specific source
(ATS platform, careers page, etc.) and returning normalized RawJobPosting objects.
"""

from collectors.base import BaseCollector, RawJobPosting

__all__ = [
    "BaseCollector",
    "RawJobPosting",
]
