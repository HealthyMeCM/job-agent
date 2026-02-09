"""LLM extraction client using litellm for provider abstraction."""

from __future__ import annotations

import json
import time

import litellm  # type: ignore[import-untyped]
from pydantic import ValidationError

from core import verbose
from parsing.adapters.base import ContentBlock
from parsing.models import (
    CompanyProfile,
    ParsedItemLog,
    ParseStatus,
)

_SYSTEM_PROMPT = """\
You are an expert at extracting structured company information from web pages.
Given the text content of a company's web page, extract a CompanyProfile as JSON.

Rules:
- Every claim you make must be grounded with an evidence snippet from the page text.
- Each signal must include an evidence snippet with the exact quoted text and where it appears.
- Tags should cover: domain/market (e.g., "ai-safety", "enterprise-saas") and tech themes (e.g., "llm", "python", "kubernetes").
- Provide 5-15 tags, 3-5 signals.
- Set confidence between 0.0 and 1.0 based on how much you could extract.
- List anything you couldn't determine in the unknowns field.
- Return ONLY valid JSON matching the schema below. No markdown, no explanation.

JSON Schema:
{schema}
"""

_USER_PROMPT = """\
Extract a CompanyProfile from this page.

Company hint: {company_hint}
Page URL: {url}
Page title: {title}
Meta description: {description}

--- PAGE CONTENT ---
{content}
"""


def _build_messages(
    content_block: ContentBlock,
    url: str,
    schema_json: str,
) -> list[dict[str, str]]:
    """Build chat messages for the LLM call."""
    title = content_block.meta.get("title", "unknown")
    description = content_block.meta.get("description", "none")

    return [
        {
            "role": "system",
            "content": _SYSTEM_PROMPT.format(schema=schema_json),
        },
        {
            "role": "user",
            "content": _USER_PROMPT.format(
                company_hint=content_block.company_hint or "unknown",
                url=url,
                title=title,
                description=description,
                content=content_block.main_text,
            ),
        },
    ]


def extract_company_profile(
    content_block: ContentBlock,
    model: str,
    snapshot_id: str,
    source_id: str,
    url: str,
) -> tuple[CompanyProfile | None, ParsedItemLog]:
    """Extract a CompanyProfile from prepared content via LLM.

    Returns:
        Tuple of (CompanyProfile or None, ParsedItemLog with status/metrics)
    """
    start = time.monotonic()
    log = ParsedItemLog(
        snapshot_id=snapshot_id,
        source_id=source_id,
        status=ParseStatus.FAILED,
        llm_model=model,
    )

    schema_json = json.dumps(CompanyProfile.model_json_schema(), indent=2)
    messages = _build_messages(content_block, url, schema_json)

    verbose.step(f"LLM call → {model} for {source_id}")

    try:
        response = litellm.completion(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    except Exception as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        log.duration_ms = elapsed_ms
        log.errors.append(f"LLM call failed: {e}")
        verbose.step(f"LLM error: {e}")
        return None, log

    elapsed_ms = (time.monotonic() - start) * 1000
    log.duration_ms = elapsed_ms

    # Extract token usage
    usage = getattr(response, "usage", None)
    if usage:
        log.llm_tokens_used = getattr(usage, "total_tokens", 0)

    # Extract response text
    raw_text: str = response.choices[0].message.content or ""  # type: ignore[union-attr]
    verbose.detail(f"LLM response: {len(raw_text)} chars, {log.llm_tokens_used} tokens")

    # Parse and validate
    try:
        data = json.loads(raw_text)
        profile = CompanyProfile.model_validate(data)
        profile.raw_llm_response = raw_text
        log.status = ParseStatus.SUCCESS
        verbose.step(
            f"Extracted: {profile.name} ({profile.domain}) — confidence={profile.confidence:.2f}"
        )
        return profile, log
    except (json.JSONDecodeError, ValidationError) as e:
        log.status = ParseStatus.PARTIAL if raw_text else ParseStatus.FAILED
        log.errors.append(f"Validation failed: {e}")
        log.warnings.append("Raw LLM output stored for debugging")
        verbose.step(f"Parse validation failed: {e}")

        # Try to salvage partial data
        try:
            data = json.loads(raw_text)
            # Fill required fields with fallbacks for partial extraction
            data.setdefault("company_id", "unknown")
            data.setdefault("name", content_block.company_hint or "Unknown")
            data.setdefault("domain", "unknown")
            data.setdefault("website", url)
            data.setdefault("summary", "Extraction incomplete")
            profile = CompanyProfile.model_validate(data)
            profile.raw_llm_response = raw_text
            profile.confidence = min(profile.confidence, 0.3)
            log.status = ParseStatus.PARTIAL
            verbose.step("Salvaged partial profile")
            return profile, log
        except Exception:
            # Complete failure — store raw response in a stub profile for debugging
            verbose.step("Could not salvage profile")
            return None, log
