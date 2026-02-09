"""Pure utility functions for text extraction and normalization."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from core.ids import slugify

# Tags to remove entirely before extracting text
_STRIP_TAGS = {
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "noscript",
    "svg",
    "iframe",
}

# Max chars to send to the LLM (roughly 8K chars ≈ 2K tokens)
_MAX_CONTENT_CHARS = 8000


def extract_domain(url: str) -> str:
    """Extract bare domain from a URL, stripping 'www.' prefix."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def make_company_id(name: str, domain: str) -> str:
    """Build a deterministic company ID from name and domain."""
    return f"{slugify(name)}-{slugify(domain)}"


def clean_text(text: str) -> str:
    """Collapse whitespace and remove null bytes."""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_main_content(html_bytes: bytes) -> str:
    """Extract main readable text from HTML, stripping boilerplate.

    Returns cleaned text truncated to ~8K chars for LLM context.
    """
    soup = BeautifulSoup(html_bytes, "lxml")

    # Remove unwanted tags
    for tag_name in _STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Try to find main content area
    main: Tag | None = soup.find("main") or soup.find("article") or soup.find("body")  # type: ignore[assignment]
    if main is None:
        main = soup  # type: ignore[assignment]

    assert main is not None
    text = main.get_text(separator="\n", strip=True)
    text = clean_text(text)

    if len(text) > _MAX_CONTENT_CHARS:
        text = text[:_MAX_CONTENT_CHARS] + "\n\n[TRUNCATED]"

    return text


def extract_meta(html_bytes: bytes) -> dict[str, str | list[str]]:
    """Extract title, meta description, OG tags, and key links from HTML."""
    soup = BeautifulSoup(html_bytes, "lxml")
    meta: dict[str, str | list[str]] = {}

    # Title
    title_tag = soup.find("title")
    if title_tag:
        meta["title"] = title_tag.get_text(strip=True)

    # Meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag and isinstance(desc_tag, Tag):
        content = desc_tag.get("content", "")
        if content:
            meta["description"] = str(content)

    # Open Graph tags
    for og_tag in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
        if isinstance(og_tag, Tag):
            prop = og_tag.get("property", "")
            content = og_tag.get("content", "")
            if prop and content:
                meta[str(prop)] = str(content)

    # Key links (careers, about, jobs)
    links: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        if isinstance(a_tag, Tag):
            href = str(a_tag.get("href", ""))
            text_lower = a_tag.get_text(strip=True).lower()
            if any(
                kw in href.lower() or kw in text_lower
                for kw in ("career", "job", "about", "team")
            ):
                links.append(href)
    if links:
        meta["key_links"] = links[:20]  # Cap at 20

    return meta
