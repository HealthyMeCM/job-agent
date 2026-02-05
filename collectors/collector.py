"""Collection stage: fetch URLs and store raw snapshots."""

from __future__ import annotations

from datetime import datetime, timezone

from collectors.planner import FetchTask
from collectors.http_client import HttpClient
from core.context import RunContext
from core.ids import normalize_url, content_hash
from evidence.snapshot import RawSnapshot, SnapshotStore


async def _collect_task(
    task: FetchTask,
    client: HttpClient,
    store: SnapshotStore,
    run_id: str,
) -> tuple[RawSnapshot | None, str | None]:
    """Collect a single task and store snapshot.

    Returns:
        Tuple of (snapshot, error_message)
    """
    result = await client.fetch(task.url)

    snapshot = RawSnapshot(
        run_id=run_id,
        source_id=task.source_id,
        source_type=task.source_type,
        original_url=task.original_url,
        canonical_url=normalize_url(task.url),
        fetched_at=datetime.now(timezone.utc),
        status_code=result.status_code,
        success=result.success,
        content_hash=content_hash(result.content) if result.content else None,
        content_type=result.content_type,
        content_length=len(result.content),
        duration_ms=result.duration_ms,
        error=result.error,
        headers=result.headers,
    )

    # Store the snapshot (metadata + content)
    stored = store.save(snapshot, result.content)

    if not result.success:
        return stored, result.error or f"HTTP {result.status_code}"

    return stored, None


async def collect(
    tasks: list[FetchTask],
    ctx: RunContext,
    store: SnapshotStore,
) -> list[RawSnapshot]:
    """Collect all fetch tasks and store raw snapshots.

    This stage only fetches and stores - it does not parse.

    Args:
        tasks: List of fetch tasks from planning stage
        ctx: Run context
        store: Snapshot store for persisting raw data

    Returns:
        List of successfully stored snapshots
    """
    ctx.start_stage("collect", items_in=len(tasks))

    snapshots: list[RawSnapshot] = []
    errors: list[str] = []

    # Group tasks by rate limit to avoid overwhelming any single source
    async with HttpClient(
        timeout=ctx.settings.default_timeout,
        rate_limit=ctx.settings.default_rate_limit,
    ) as client:
        for task in tasks:
            snapshot, error = await _collect_task(
                task, client, store, ctx.run_id
            )

            if snapshot:
                snapshots.append(snapshot)
                if snapshot.success:
                    ctx.metrics.num_snapshots_success += 1
                else:
                    ctx.metrics.num_snapshots_failed += 1

            if error:
                errors.append(f"{task.source_id}: {error}")

    ctx.complete_stage(
        "collect",
        items_out=len(snapshots),
        errors=errors,
        status="completed" if snapshots else "failed",
    )

    return snapshots
