"""Main parse stage: snapshot → CompanyProfile via adapter + LLM."""

from __future__ import annotations

from core import verbose
from core.context import RunContext
from evidence.snapshot import RawSnapshot, SnapshotStore
from parsing.adapters import get_adapter
from parsing.llm import extract_company_profile
from parsing.models import (
    ParsedItemLog,
    ParseStatus,
    ParseSummary,
)
from parsing.normalizers import extract_domain, make_company_id
from parsing.store import ParseStore


def parse_and_normalize(
    snapshots: list[RawSnapshot],
    ctx: RunContext,
    snapshot_store: SnapshotStore,
    parse_store: ParseStore,
) -> ParseSummary:
    """Parse raw snapshots into structured CompanyProfiles.

    For each successful snapshot:
    1. Get adapter for source_type
    2. Load content from snapshot store
    3. Adapter extracts ContentBlock
    4. LLM extracts CompanyProfile from ContentBlock
    5. Post-process: set company_id, domain, website from snapshot URL
    6. Persist results

    Args:
        snapshots: Snapshots from the collect stage
        ctx: Run context
        snapshot_store: For loading raw HTML content
        parse_store: For persisting parsed profiles

    Returns:
        ParseSummary with profiles and logs
    """
    ctx.start_stage("parse", items_in=len(snapshots))
    verbose.stage("Parse", "extract CompanyProfiles from raw snapshots")

    summary = ParseSummary()
    model = ctx.settings.llm_model

    for snapshot in snapshots:
        # Skip failed fetches
        if not snapshot.success:
            log = ParsedItemLog(
                snapshot_id=snapshot.snapshot_id,
                source_id=snapshot.source_id,
                status=ParseStatus.SKIPPED,
                warnings=[f"Snapshot not successful (HTTP {snapshot.status_code})"],
            )
            summary.logs.append(log)
            summary.num_skipped += 1
            verbose.step(f"SKIP {snapshot.source_id} — HTTP {snapshot.status_code}")
            continue

        # Get adapter
        adapter = get_adapter(snapshot.source_type)
        if adapter is None:
            log = ParsedItemLog(
                snapshot_id=snapshot.snapshot_id,
                source_id=snapshot.source_id,
                status=ParseStatus.SKIPPED,
                warnings=[f"No adapter for source_type={snapshot.source_type}"],
            )
            summary.logs.append(log)
            summary.num_skipped += 1
            verbose.step(
                f"SKIP {snapshot.source_id} — no adapter for {snapshot.source_type}"
            )
            continue

        # Load raw content
        html_bytes = snapshot_store.get_content(snapshot.snapshot_id)
        if html_bytes is None:
            log = ParsedItemLog(
                snapshot_id=snapshot.snapshot_id,
                source_id=snapshot.source_id,
                status=ParseStatus.FAILED,
                errors=["Could not load snapshot content"],
            )
            summary.logs.append(log)
            summary.num_failed += 1
            verbose.step(f"FAIL {snapshot.source_id} — content not found")
            continue

        # Extract content via adapter
        verbose.step(f"Extracting content: {snapshot.source_id}")
        source_metadata: dict[str, str] = {}
        # Reconstruct source metadata from source config
        for src in ctx.sources.sources:
            if src.source_id == snapshot.source_id:
                source_metadata = {k: str(v) for k, v in src.metadata.items()}
                break

        content_block = adapter.extract_content(snapshot, html_bytes, source_metadata)
        verbose.detail(
            f"Content: {len(content_block.main_text)} chars, "
            f"meta keys: {list(content_block.meta.keys())}"
        )

        # LLM extraction
        profile, log = extract_company_profile(
            content_block=content_block,
            model=model,
            snapshot_id=snapshot.snapshot_id,
            source_id=snapshot.source_id,
            url=snapshot.canonical_url,
        )

        # Post-process: set deterministic fields
        if profile is not None:
            domain = extract_domain(snapshot.canonical_url)
            profile.domain = domain
            profile.website = snapshot.canonical_url
            profile.company_id = make_company_id(profile.name, domain)

        # Update summary
        summary.logs.append(log)
        summary.total_tokens += log.llm_tokens_used

        if log.status == ParseStatus.SUCCESS:
            summary.num_success += 1
            ctx.metrics.num_parse_success += 1
            if profile is not None:
                summary.profiles.append(profile)
        elif log.status == ParseStatus.PARTIAL:
            summary.num_partial += 1
            ctx.metrics.num_parse_success += 1  # Partial counts as success for metrics
            if profile is not None:
                summary.profiles.append(profile)
        elif log.status == ParseStatus.FAILED:
            summary.num_failed += 1
            ctx.metrics.num_parse_failed += 1
        else:
            summary.num_skipped += 1

    # Persist results
    parse_store.save_profiles(ctx.run_id, summary.profiles)
    parse_store.save_parse_log(ctx.run_id, summary.logs)

    errors = [log.errors[0] for log in summary.logs if log.errors]
    ctx.complete_stage(
        "parse",
        items_out=len(summary.profiles),
        errors=errors,
        status="completed",
    )

    stage_log = next((sl for sl in ctx.stage_logs if sl.stage == "parse"), None)
    verbose.stage_end(
        "parse",
        items_out=len(summary.profiles),
        errors=summary.num_failed,
        duration=stage_log.duration_seconds
        if stage_log and stage_log.duration_seconds
        else 0.0,
    )

    return summary
