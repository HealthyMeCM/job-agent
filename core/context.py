"""Run context and lifecycle management."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.config import Settings, SourcesConfig, snapshot_config
from core.ids import generate_run_id


class RunStatus(str, Enum):
    """Status of a pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunMetrics(BaseModel):
    """Metrics collected during a run."""

    num_fetch_tasks: int = 0
    num_snapshots_success: int = 0
    num_snapshots_failed: int = 0
    num_parse_success: int = 0
    num_parse_failed: int = 0
    num_role_leads_upserted: int = 0
    num_candidates: int = 0


class StageLog(BaseModel):
    """Log entry for a pipeline stage."""

    stage: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "running"
    items_in: int = 0
    items_out: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None


class RunContext(BaseModel):
    """Context for a pipeline run - travels through all stages."""

    run_id: str
    started_at: datetime
    status: RunStatus = RunStatus.PENDING
    completed_at: datetime | None = None

    # Configuration
    settings: Settings
    sources: SourcesConfig

    # Tracking
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    stage_logs: list[StageLog] = Field(default_factory=list)

    # Paths
    config_snapshot_path: Path | None = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def boot(
        cls,
        settings: Settings,
        sources: SourcesConfig,
        run_id: str | None = None,
    ) -> RunContext:
        """Boot a new run context.

        Creates the run, saves config snapshot, and returns initialized context.
        """
        run_id = run_id or generate_run_id()
        started_at = datetime.now(timezone.utc)

        # Create config snapshot directory
        snapshot_dir = Path(settings.config_snapshots_dir)
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Save config snapshot
        snapshot_path = snapshot_dir / f"{run_id}_config.json"
        config_data = snapshot_config(settings, sources)
        config_data["run_id"] = run_id
        config_data["started_at"] = started_at.isoformat()

        with open(snapshot_path, "w") as f:
            json.dump(config_data, f, indent=2, default=str)

        return cls(
            run_id=run_id,
            started_at=started_at,
            status=RunStatus.RUNNING,
            settings=settings,
            sources=sources,
            config_snapshot_path=snapshot_path,
        )

    def start_stage(self, stage: str, items_in: int = 0) -> StageLog:
        """Record start of a stage."""
        log = StageLog(
            stage=stage,
            started_at=datetime.now(timezone.utc),
            items_in=items_in,
        )
        self.stage_logs.append(log)
        return log

    def complete_stage(
        self,
        stage: str,
        items_out: int = 0,
        errors: list[str] | None = None,
        status: str = "completed",
    ) -> None:
        """Record completion of a stage."""
        for log in self.stage_logs:
            if log.stage == stage and log.completed_at is None:
                log.completed_at = datetime.now(timezone.utc)
                log.items_out = items_out
                log.status = status
                if errors:
                    log.errors = errors
                log.duration_seconds = (
                    log.completed_at - log.started_at
                ).total_seconds()
                break

    def complete_run(self, status: RunStatus = RunStatus.COMPLETED) -> None:
        """Mark the run as complete."""
        self.status = status
        self.completed_at = datetime.now(timezone.utc)

    def summary(self) -> dict[str, Any]:
        """Get a summary of the run for display."""
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metrics": self.metrics.model_dump(),
            "stages": [
                {
                    "stage": log.stage,
                    "status": log.status,
                    "items_in": log.items_in,
                    "items_out": log.items_out,
                    "duration": log.duration_seconds,
                    "errors": len(log.errors),
                }
                for log in self.stage_logs
            ],
        }
