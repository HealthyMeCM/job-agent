"""Pydantic models for the parsing stage."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EvidenceSnippet(BaseModel):
    """A quoted snippet from the source page grounding a claim."""

    text: str
    context: str  # Where on the page (e.g., "meta description", "hero section")


class Signal(BaseModel):
    """A hiring/seriousness proxy extracted from the page."""

    name: str  # e.g., "active_hiring", "ai_focus", "growth_stage"
    value: str  # e.g., "high", "true", "Series B"
    evidence: EvidenceSnippet


class CompanyProfile(BaseModel):
    """Structured company profile extracted from a single snapshot."""

    company_id: str  # slugify(name) + "-" + slugify(domain)
    name: str
    domain: str  # e.g., "anthropic.com"
    website: str  # Canonical URL
    summary: str  # 1-3 sentence "what they do"
    tags: list[str] = Field(default_factory=list)  # 5-15 tags
    signals: list[Signal] = Field(default_factory=list)  # 3-5 signals with evidence
    confidence: float = 0.0  # 0.0-1.0 extraction confidence
    unknowns: list[str] = Field(default_factory=list)  # What couldn't be determined
    raw_llm_response: str | None = None  # Raw LLM output for debugging


class ParseStatus(StrEnum):
    """Status of a single parse operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class ParsedItemLog(BaseModel):
    """Per-snapshot parse log entry."""

    snapshot_id: str
    source_id: str
    status: ParseStatus
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    llm_model: str | None = None
    llm_tokens_used: int = 0


class ParseResult(BaseModel):
    """Result of parsing a single snapshot."""

    company_profile: CompanyProfile | None = None
    log: ParsedItemLog


class ParseSummary(BaseModel):
    """Aggregate output from the parse stage."""

    num_success: int = 0
    num_partial: int = 0
    num_failed: int = 0
    num_skipped: int = 0
    total_tokens: int = 0
    profiles: list[CompanyProfile] = Field(default_factory=list)
    logs: list[ParsedItemLog] = Field(default_factory=list)
