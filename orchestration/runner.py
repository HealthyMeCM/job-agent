"""Pipeline runner for checkpoint execution."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from collectors.collector import collect
from collectors.planner import plan_sources
from core import verbose
from core.config import Settings, SourcesConfig, load_config
from core.context import RunContext, RunStatus
from evidence.snapshot import FileSnapshotStore
from parsing.parser import parse_and_normalize
from parsing.store import FileParseStore


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
    run_start = time.monotonic()

    # Stage 0: Boot
    if settings is None or sources is None:
        settings, sources = load_config(sources_path)

    verbose.configure(settings.verbose)

    ctx = RunContext.boot(settings, sources, run_id)

    verbose.header(f"Pipeline Run {ctx.run_id}")
    verbose.stage("Boot", "initialize run context and save config")
    verbose.step(
        f"Config loaded (verbose={settings.verbose}, dry_run={settings.dry_run})"
    )
    enabled = sum(1 for s in sources.sources if s.enabled)
    verbose.step(f"Sources: {len(sources.sources)} configured, {enabled} enabled")
    verbose.step(f"Config snapshot saved → {ctx.config_snapshot_path}")
    verbose.vprint("")

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

    total = time.monotonic() - run_start
    verbose.header(
        f"Done: {ctx.metrics.num_snapshots_success} snapshots, "
        f"{ctx.metrics.num_snapshots_failed} failures ({total:.2f}s)"
    )

    return ctx


def run_checkpoint_a(
    settings: Settings | None = None,
    sources: SourcesConfig | None = None,
    sources_path: Path | None = None,
    run_id: str | None = None,
) -> RunContext:
    """Synchronous wrapper for run_checkpoint_a_async."""
    return asyncio.run(run_checkpoint_a_async(settings, sources, sources_path, run_id))


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


async def run_checkpoint_b_async(
    settings: Settings | None = None,
    sources: SourcesConfig | None = None,
    sources_path: Path | None = None,
    run_id: str | None = None,
) -> RunContext:
    """Run checkpoint B: Boot -> Plan -> Collect -> Parse.

    Extends checkpoint A with LLM-based CompanyProfile extraction.

    Args:
        settings: Optional pre-loaded settings
        sources: Optional pre-loaded sources config
        sources_path: Path to sources YAML (if sources not provided)
        run_id: Optional explicit run ID

    Returns:
        RunContext with metrics and stage logs
    """
    run_start = time.monotonic()

    # Stage 0: Boot
    if settings is None or sources is None:
        settings, sources = load_config(sources_path)

    verbose.configure(settings.verbose)

    ctx = RunContext.boot(settings, sources, run_id)

    verbose.header(f"Pipeline Run {ctx.run_id} (Checkpoint B)")
    verbose.stage("Boot", "initialize run context and save config")
    verbose.step(
        f"Config loaded (verbose={settings.verbose}, dry_run={settings.dry_run})"
    )
    verbose.step(f"LLM model: {settings.llm_model}")
    enabled = sum(1 for s in sources.sources if s.enabled)
    verbose.step(f"Sources: {len(sources.sources)} configured, {enabled} enabled")
    verbose.step(f"Config snapshot saved → {ctx.config_snapshot_path}")
    verbose.vprint("")

    try:
        # Stage 1: Plan sources
        tasks = plan_sources(ctx)

        if not tasks:
            ctx.complete_run(RunStatus.COMPLETED)
            return ctx

        # Stage 2: Collect snapshots
        snapshot_store = FileSnapshotStore(settings.snapshots_dir)
        snapshots = await collect(tasks, ctx, snapshot_store)

        # Stage 3: Parse snapshots → CompanyProfiles
        parse_store = FileParseStore(settings.parsed_dir)
        parse_summary = parse_and_normalize(snapshots, ctx, snapshot_store, parse_store)

        verbose.step(
            f"Parse results: {parse_summary.num_success} success, "
            f"{parse_summary.num_partial} partial, "
            f"{parse_summary.num_failed} failed, "
            f"{parse_summary.num_skipped} skipped"
        )
        verbose.step(f"Total LLM tokens: {parse_summary.total_tokens}")

        ctx.complete_run(RunStatus.COMPLETED)

    except Exception as e:
        ctx.complete_run(RunStatus.FAILED)
        if ctx.stage_logs:
            ctx.stage_logs[-1].errors.append(str(e))
        raise

    total = time.monotonic() - run_start
    verbose.header(
        f"Done: {ctx.metrics.num_snapshots_success} snapshots, "
        f"{ctx.metrics.num_parse_success} profiles, "
        f"{ctx.metrics.num_parse_failed} parse failures ({total:.2f}s)"
    )

    return ctx


def run_checkpoint_b(
    settings: Settings | None = None,
    sources: SourcesConfig | None = None,
    sources_path: Path | None = None,
    run_id: str | None = None,
) -> RunContext:
    """Synchronous wrapper for run_checkpoint_b_async."""
    return asyncio.run(run_checkpoint_b_async(settings, sources, sources_path, run_id))


def get_checkpoint_b_results(ctx: RunContext) -> dict[str, Any]:
    """Get detailed results from a checkpoint B run.

    Returns summary, snapshots, and parsed profiles.
    """
    settings = ctx.settings
    snapshot_store = FileSnapshotStore(settings.snapshots_dir)
    parse_store = FileParseStore(settings.parsed_dir)

    snapshots = snapshot_store.list_by_run(ctx.run_id)
    profiles = parse_store.load_profiles(ctx.run_id)
    parse_logs = parse_store.load_parse_log(ctx.run_id)

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
        "profiles": [p.model_dump(mode="json") for p in profiles],
        "parse_logs": [log.model_dump(mode="json") for log in parse_logs],
    }
