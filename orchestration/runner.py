"""Pipeline runner for checkpoint execution."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from core.config import Settings, SourcesConfig, load_config
from core.context import RunContext, RunStatus
from collectors.planner import plan_sources, FetchTask
from collectors.collector import collect
from evidence.snapshot import RawSnapshot, FileSnapshotStore


async def run_checkpoint_a_async(
    settings: Settings | None = None,
    sources: SourcesConfig | None = None,
    sources_path: Path | None = None,
    run_id: str | None = None,
) -> RunContext:
    """Run checkpoint A: Boot -> Plan -> Collect.

    Checkpoint A validates:
    - Config loading and snapshot
    - Source planning
    - HTTP collection with rate limiting
    - Raw snapshot storage

    Args:
        settings: Optional pre-loaded settings
        sources: Optional pre-loaded sources config
        sources_path: Path to sources YAML (if sources not provided)
        run_id: Optional explicit run ID

    Returns:
        RunContext with metrics and stage logs
    """
    # Stage 0: Boot
    if settings is None or sources is None:
        settings, sources = load_config(sources_path)

    ctx = RunContext.boot(settings, sources, run_id)

    try:
        # Stage 1: Plan sources
        tasks = plan_sources(ctx)

        if not tasks:
            ctx.complete_run(RunStatus.COMPLETED)
            return ctx

        # Stage 2: Collect snapshots
        store = FileSnapshotStore(settings.snapshots_dir)
        snapshots = await collect(tasks, ctx, store)

        ctx.complete_run(RunStatus.COMPLETED)

    except Exception as e:
        ctx.complete_run(RunStatus.FAILED)
        # Add error to the current stage if any
        if ctx.stage_logs:
            ctx.stage_logs[-1].errors.append(str(e))
        raise

    return ctx


def run_checkpoint_a(
    settings: Settings | None = None,
    sources: SourcesConfig | None = None,
    sources_path: Path | None = None,
    run_id: str | None = None,
) -> RunContext:
    """Synchronous wrapper for run_checkpoint_a_async."""
    return asyncio.run(
        run_checkpoint_a_async(settings, sources, sources_path, run_id)
    )


def get_checkpoint_a_results(ctx: RunContext) -> dict[str, Any]:
    """Get detailed results from a checkpoint A run.

    Useful for inspection and debugging.
    """
    settings = ctx.settings
    store = FileSnapshotStore(settings.snapshots_dir)
    snapshots = store.list_by_run(ctx.run_id)

    return {
        "summary": ctx.summary(),
        "snapshots": [
            {
                "snapshot_id": s.snapshot_id,
                "source_id": s.source_id,
                "url": s.canonical_url,
                "success": s.success,
                "status_code": s.status_code,
                "content_type": s.content_type,
                "content_length": s.content_length,
                "error": s.error,
            }
            for s in snapshots
        ],
    }
