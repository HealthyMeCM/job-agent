"""
Configuration loader for the Job Agent pipeline.

Loads and validates:
- Environment variables from .env
- YAML config files from configs/
- Writes run artifacts for reproducibility
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from schemas.config import (
    PreferencesConfig,
    SeedCompaniesConfig,
    SourcesConfig,
    TargetTitlesConfig,
)


class EnvConfig(BaseSettings):
    """Environment variables configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://job_agent:job_agent@localhost:5432/job_agent",
        description="PostgreSQL connection string",
    )

    # OpenAI
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for embeddings and LLM",
    )

    # Langfuse (optional)
    langfuse_public_key: str = Field(default="", description="Langfuse public key")
    langfuse_secret_key: str = Field(default="", description="Langfuse secret key")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse host URL",
    )

    # Application
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")

    @property
    def has_openai(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.openai_api_key)

    @property
    def has_langfuse(self) -> bool:
        """Check if Langfuse is configured."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


class AppConfig(BaseSettings):
    """Combined application configuration."""

    model_config = SettingsConfigDict(arbitrary_types_allowed=True)

    env: EnvConfig
    seed_companies: SeedCompaniesConfig
    target_titles: TargetTitlesConfig
    preferences: PreferencesConfig
    sources: SourcesConfig

    # Metadata
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    config_dir: Path = Field(default=Path("configs"))

    def to_snapshot(self) -> dict[str, Any]:
        """Create a serializable snapshot for artifact storage."""
        return {
            "loaded_at": self.loaded_at.isoformat(),
            "config_dir": str(self.config_dir),
            "seed_companies": self.seed_companies.model_dump(),
            "target_titles": self.target_titles.model_dump(),
            "preferences": self.preferences.model_dump(),
            "sources": self.sources.model_dump(by_alias=True),
            "env": {
                "database_url": "***",  # Redact sensitive info
                "has_openai": self.env.has_openai,
                "has_langfuse": self.env.has_langfuse,
                "log_level": self.env.log_level,
                "debug": self.env.debug,
            },
        }


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []


class ConfigLoader:
    """Loads and validates configuration from environment and YAML files."""

    REQUIRED_CONFIGS = [
        "seed_companies.yaml",
        "target_titles.yaml",
        "preferences.yaml",
        "sources.yaml",
    ]

    def __init__(
        self,
        config_dir: str | Path = "configs",
        env_file: str | Path | None = ".env",
        artifacts_dir: str | Path = "artifacts",
    ):
        self.config_dir = Path(config_dir)
        self.env_file = Path(env_file) if env_file else None
        self.artifacts_dir = Path(artifacts_dir)
        self._config: AppConfig | None = None

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        """Load a YAML file from the config directory."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise ConfigValidationError(f"Config file not found: {filepath}")

        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if data is not None else {}

    def _validate_required_configs(self) -> list[str]:
        """Check that all required config files exist."""
        missing = []
        for filename in self.REQUIRED_CONFIGS:
            filepath = self.config_dir / filename
            if not filepath.exists():
                missing.append(filename)
        return missing

    def _validate_env(self, env: EnvConfig) -> list[str]:
        """Validate environment configuration and return warnings."""
        warnings = []

        if not env.has_openai:
            warnings.append(
                "OPENAI_API_KEY not set - embeddings and LLM features will be disabled"
            )

        if not env.has_langfuse:
            warnings.append(
                "Langfuse not configured - tracing will be disabled"
            )

        return warnings

    def load(self, validate_env: bool = True) -> AppConfig:
        """
        Load all configuration.

        Args:
            validate_env: Whether to validate environment variables

        Returns:
            Combined AppConfig object

        Raises:
            ConfigValidationError: If required configs are missing or invalid
        """
        # Check required files exist
        missing = self._validate_required_configs()
        if missing:
            raise ConfigValidationError(
                f"Missing required config files: {', '.join(missing)}"
            )

        # Load environment
        if self.env_file and self.env_file.exists():
            os.environ.setdefault("ENV_FILE", str(self.env_file))
            env = EnvConfig(_env_file=self.env_file)
        else:
            env = EnvConfig()

        # Validate env and collect warnings
        env_warnings = self._validate_env(env) if validate_env else []

        # Load YAML configs
        try:
            seed_companies = SeedCompaniesConfig(**self._load_yaml("seed_companies.yaml"))
        except ValidationError as e:
            raise ConfigValidationError(
                "Invalid seed_companies.yaml",
                errors=e.errors(),
            ) from e

        try:
            target_titles = TargetTitlesConfig(**self._load_yaml("target_titles.yaml"))
        except ValidationError as e:
            raise ConfigValidationError(
                "Invalid target_titles.yaml",
                errors=e.errors(),
            ) from e

        try:
            preferences = PreferencesConfig(**self._load_yaml("preferences.yaml"))
        except ValidationError as e:
            raise ConfigValidationError(
                "Invalid preferences.yaml",
                errors=e.errors(),
            ) from e

        try:
            sources = SourcesConfig(**self._load_yaml("sources.yaml"))
        except ValidationError as e:
            raise ConfigValidationError(
                "Invalid sources.yaml",
                errors=e.errors(),
            ) from e

        # Build combined config
        self._config = AppConfig(
            env=env,
            seed_companies=seed_companies,
            target_titles=target_titles,
            preferences=preferences,
            sources=sources,
            config_dir=self.config_dir,
        )

        # Log warnings
        for warning in env_warnings:
            # Using print for now; will be replaced with structlog
            print(f"[CONFIG WARNING] {warning}")

        return self._config

    def write_run_artifact(self, run_id: str | None = None) -> Path:
        """
        Write a run artifact with the current configuration snapshot.

        Args:
            run_id: Optional run identifier. If not provided, uses timestamp.

        Returns:
            Path to the written artifact file

        Raises:
            ValueError: If config hasn't been loaded yet
        """
        if self._config is None:
            raise ValueError("Config not loaded. Call load() first.")

        # Generate run ID if not provided
        if run_id is None:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Ensure artifacts directory exists
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Create artifact
        artifact = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": self._config.to_snapshot(),
        }

        # Write artifact
        artifact_path = self.artifacts_dir / f"run_{run_id}_config.json"
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2, default=str)

        return artifact_path

    @property
    def config(self) -> AppConfig:
        """Get the loaded config, raising if not loaded."""
        if self._config is None:
            raise ValueError("Config not loaded. Call load() first.")
        return self._config


def load_config(
    config_dir: str | Path = "configs",
    env_file: str | Path | None = ".env",
    write_artifact: bool = True,
    artifacts_dir: str | Path = "artifacts",
) -> AppConfig:
    """
    Convenience function to load configuration.

    Args:
        config_dir: Path to config directory
        env_file: Path to .env file (or None to skip)
        write_artifact: Whether to write a run artifact
        artifacts_dir: Path to artifacts directory

    Returns:
        Loaded and validated AppConfig
    """
    loader = ConfigLoader(
        config_dir=config_dir,
        env_file=env_file,
        artifacts_dir=artifacts_dir,
    )
    config = loader.load()

    if write_artifact:
        artifact_path = loader.write_run_artifact()
        print(f"[CONFIG] Run artifact written to: {artifact_path}")

    return config
