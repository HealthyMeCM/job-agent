"""ID generation and hashing utilities."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse, urlunparse
import uuid


def generate_run_id() -> str:
    """Generate a unique run ID.

    Format: YYYYMMDD_HHMMSS_<short_uuid>
    """
    now = datetime.now(timezone.utc)
    short_uuid = uuid.uuid4().hex[:8]
    return f"{now.strftime('%Y%m%d_%H%M%S')}_{short_uuid}"


def content_hash(content: str | bytes) -> str:
    """Generate SHA-256 hash of content.

    Returns first 16 characters for brevity while maintaining uniqueness.
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:16]


# URL parameters to strip during normalization (tracking params)
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "source",
    "mc_cid",
    "mc_eid",
}


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication.

    - Lowercases scheme and host
    - Removes tracking parameters
    - Removes trailing slashes (except root)
    - Sorts remaining query parameters
    """
    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove tracking params and sort remaining
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {
        k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMS
    }
    sorted_query = "&".join(
        f"{k}={v[0]}" for k, v in sorted(filtered_params.items()) if v
    )

    # Normalize path - remove trailing slash unless root
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return urlunparse((scheme, netloc, path, "", sorted_query, ""))


def url_hash(url: str) -> str:
    """Generate a hash for a URL (after normalization)."""
    normalized = normalize_url(url)
    return content_hash(normalized)


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    # Lowercase and replace spaces/special chars with hyphens
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")
