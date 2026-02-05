"""Source planning: translate config into fetch tasks."""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.context import RunContext
from core.config import SourceConfig


class FetchPolicy(BaseModel):
    """Policy for how to fetch a source."""

    rate_limit_rps: float = 1.0
    timeout_seconds: int = 30
    max_retries: int = 3
    follow_links: bool = False


class FetchTask(BaseModel):
    """A single fetch task for the collector."""

    url: str
    source_id: str
    source_type: str
    fetch_policy: FetchPolicy
    original_url: str  # Keep original before normalization
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def from_source_config(cls, config: SourceConfig) -> FetchTask:
        """Create a FetchTask from a SourceConfig."""
        return cls(
            url=config.url,
            original_url=config.url,
            source_id=config.source_id,
            source_type=config.source_type,
            fetch_policy=FetchPolicy(
                rate_limit_rps=config.rate_limit_rps,
                timeout_seconds=config.timeout_seconds,
                max_retries=config.max_retries,
                follow_links=config.follow_links,
            ),
            metadata=config.metadata,
        )


def plan_sources(ctx: RunContext) -> list[FetchTask]:
    """Plan fetch tasks from configured sources.

    This stage only plans - it does not fetch or parse anything.

    Args:
        ctx: The run context with source configuration

    Returns:
        List of FetchTask objects ready for collection
    """
    ctx.start_stage("plan_sources", items_in=len(ctx.sources.sources))

    tasks: list[FetchTask] = []
    errors: list[str] = []

    for source in ctx.sources.sources:
        if not source.enabled:
            continue

        try:
            task = FetchTask.from_source_config(source)
            tasks.append(task)
        except Exception as e:
            errors.append(f"Failed to plan source {source.source_id}: {e}")

    ctx.metrics.num_fetch_tasks = len(tasks)
    ctx.complete_stage("plan_sources", items_out=len(tasks), errors=errors)

    return tasks
