"""Raw snapshot models and storage abstraction."""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from core import verbose


class RawSnapshot(BaseModel):
    """A raw snapshot of fetched content - the evidence layer."""

    # Identity
    snapshot_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    run_id: str

    # Source info
    source_id: str
    source_type: str

    # URLs
    original_url: str
    canonical_url: str

    # Fetch metadata
    fetched_at: datetime
    status_code: int
    success: bool

    # Content metadata
    content_hash: str | None = None
    content_type: str | None = None
    content_length: int = 0

    # Performance
    duration_ms: float = 0.0

    # Error tracking
    error: str | None = None

    # Raw headers (for debugging)
    headers: dict[str, str] = Field(default_factory=dict)

    # Storage reference (set after save)
    content_path: str | None = None


class SnapshotStore(ABC):
    """Abstract base for snapshot storage."""

    @abstractmethod
    def save(self, snapshot: RawSnapshot, content: bytes) -> RawSnapshot:
        """Save a snapshot and its content. Returns updated snapshot with content_path."""
        pass

    @abstractmethod
    def get_metadata(self, snapshot_id: str) -> RawSnapshot | None:
        """Get snapshot metadata by ID."""
        pass

    @abstractmethod
    def get_content(self, snapshot_id: str) -> bytes | None:
        """Get raw content by snapshot ID."""
        pass

    @abstractmethod
    def list_by_run(self, run_id: str) -> list[RawSnapshot]:
        """List all snapshots for a run."""
        pass


class FileSnapshotStore(SnapshotStore):
    """File-based snapshot storage.

    Structure:
        base_dir/
            {run_id}/
                {snapshot_id}.meta.json  (metadata)
                {snapshot_id}.content    (raw content)
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        path = self.base_dir / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _meta_path(self, run_id: str, snapshot_id: str) -> Path:
        return self._run_dir(run_id) / f"{snapshot_id}.meta.json"

    def _content_path(self, run_id: str, snapshot_id: str) -> Path:
        return self._run_dir(run_id) / f"{snapshot_id}.content"

    def save(self, snapshot: RawSnapshot, content: bytes) -> RawSnapshot:
        """Save snapshot metadata and content to files."""
        # Save content
        content_path = self._content_path(snapshot.run_id, snapshot.snapshot_id)
        content_path.write_bytes(content)

        # Update snapshot with content path
        snapshot.content_path = str(content_path)

        # Save metadata
        meta_path = self._meta_path(snapshot.run_id, snapshot.snapshot_id)
        with open(meta_path, "w") as f:
            json.dump(snapshot.model_dump(mode="json"), f, indent=2, default=str)

        content_kb = len(content) / 1024
        verbose.detail(
            f"Snapshot saved → {snapshot.snapshot_id} ({content_kb:.1f}kb)"
        )

        return snapshot

    def get_metadata(self, snapshot_id: str) -> RawSnapshot | None:
        """Get snapshot metadata - searches all runs."""
        for run_dir in self.base_dir.iterdir():
            if run_dir.is_dir():
                meta_path = run_dir / f"{snapshot_id}.meta.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        return RawSnapshot(**json.load(f))
        return None

    def get_content(self, snapshot_id: str) -> bytes | None:
        """Get raw content - searches all runs."""
        for run_dir in self.base_dir.iterdir():
            if run_dir.is_dir():
                content_path = run_dir / f"{snapshot_id}.content"
                if content_path.exists():
                    return content_path.read_bytes()
        return None

    def list_by_run(self, run_id: str) -> list[RawSnapshot]:
        """List all snapshots for a run."""
        run_dir = self._run_dir(run_id)
        snapshots = []

        for meta_file in run_dir.glob("*.meta.json"):
            with open(meta_file) as f:
                snapshots.append(RawSnapshot(**json.load(f)))

        return sorted(snapshots, key=lambda s: s.fetched_at)

    def get_content_by_path(self, content_path: str) -> bytes | None:
        """Get content directly by path."""
        path = Path(content_path)
        if path.exists():
            return path.read_bytes()
        return None
