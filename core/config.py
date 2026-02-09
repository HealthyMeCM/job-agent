"""Configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceConfig(BaseModel):
    """Configuration for a single source."""

    source_id: str
    source_type: str  # "ats_board" | "careers_page" | "rss"
    url: str
    enabled: bool = True
    rate_limit_rps: float = 1.0
    timeout_seconds: int = 30
    max_retries: int = 3
    follow_links: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourcesConfig(BaseModel):
    """Collection of source configurations."""

    sources: list[SourceConfig] = Field(default_factory=list)


class Settings(BaseSettings):
    """Application settings from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./data/job_agent.db"

    # Storage
    snapshots_dir: str = "./data/snapshots"
    config_snapshots_dir: str = "./data/config_snapshots"
    parsed_dir: str = "./data/parsed"

    # LLM
    llm_model: str = "gpt-4o-mini"

    # Runtime
    dry_run: bool = False
    verbose: int = 0
    log_level: str = "INFO"

    @field_validator("verbose", mode="before")
    @classmethod
    def _coerce_verbose(cls, v: Any) -> int:
        if isinstance(v, bool):
            return 2 if v else 0
        if isinstance(v, str):
            low = v.strip().lower()
            # Try numeric first so "1", "2", "3" stay as-is
            try:
                return int(low)
            except ValueError:
                pass
            if low in ("true", "yes"):
                return 2
            if low in ("false", "no", ""):
                return 0
            return 0
        return int(v)

    # HTTP client defaults
    default_timeout: int = 30
    default_rate_limit: float = 1.0


def load_sources_config(path: Path) -> SourcesConfig:
    """Load sources configuration from YAML file."""
    if not path.exists():
        return SourcesConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return SourcesConfig(**data)


def load_config(
    sources_path: Path | None = None,
    settings: Settings | None = None,
) -> tuple[Settings, SourcesConfig]:
    """Load all configuration.

    Returns:
        Tuple of (Settings, SourcesConfig)
    """
    settings = settings or Settings()
    sources_path = sources_path or Path("config/sources.yaml")
    sources = load_sources_config(sources_path)

    return settings, sources


def snapshot_config(settings: Settings, sources: SourcesConfig) -> dict[str, Any]:
    """Create a serializable snapshot of the current configuration."""
    return {
        "settings": settings.model_dump(mode="json"),
        "sources": sources.model_dump(mode="json"),
    }
