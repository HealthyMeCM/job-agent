"""File-based storage for parsed company profiles."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from core import verbose
from parsing.models import CompanyProfile, ParsedItemLog


class ParseStore(ABC):
    """Abstract base for parsed profile storage."""

    @abstractmethod
    def save_profiles(self, run_id: str, profiles: list[CompanyProfile]) -> None:
        """Save extracted company profiles for a run."""

    @abstractmethod
    def save_parse_log(self, run_id: str, logs: list[ParsedItemLog]) -> None:
        """Save parse logs for a run."""

    @abstractmethod
    def load_profiles(self, run_id: str) -> list[CompanyProfile]:
        """Load company profiles for a run."""

    @abstractmethod
    def load_parse_log(self, run_id: str) -> list[ParsedItemLog]:
        """Load parse logs for a run."""


class FileParseStore(ParseStore):
    """File-based storage for parsed data.

    Structure:
        base_dir/
            {run_id}/
                profiles.json      (list of CompanyProfile dicts)
                parse_log.json     (list of ParsedItemLog dicts)
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        path = self.base_dir / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_profiles(self, run_id: str, profiles: list[CompanyProfile]) -> None:
        """Save profiles to profiles.json."""
        path = self._run_dir(run_id) / "profiles.json"
        data = [p.model_dump(mode="json") for p in profiles]
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        verbose.detail(f"Saved {len(profiles)} profiles → {path}")

    def save_parse_log(self, run_id: str, logs: list[ParsedItemLog]) -> None:
        """Save parse logs to parse_log.json."""
        path = self._run_dir(run_id) / "parse_log.json"
        data = [log.model_dump(mode="json") for log in logs]
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        verbose.detail(f"Saved {len(logs)} parse logs → {path}")

    def load_profiles(self, run_id: str) -> list[CompanyProfile]:
        """Load profiles from profiles.json."""
        path = self._run_dir(run_id) / "profiles.json"
        if not path.exists():
            return []
        with open(path) as f:
            data = json.load(f)
        return [CompanyProfile.model_validate(item) for item in data]

    def load_parse_log(self, run_id: str) -> list[ParsedItemLog]:
        """Load parse logs from parse_log.json."""
        path = self._run_dir(run_id) / "parse_log.json"
        if not path.exists():
            return []
        with open(path) as f:
            data = json.load(f)
        return [ParsedItemLog.model_validate(item) for item in data]
