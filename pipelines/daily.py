"""Daily pipeline orchestration."""

import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

import structlog

from pipelines.utils import AppConfig, ConfigValidationError, load_config

logger = structlog.get_logger()


async def run_daily_pipeline(config: AppConfig) -> None:
    """
    Run the complete daily pipeline.

    Args:
        config: Loaded and validated application config

    Steps:
    1. Collect from all configured sources
    2. Normalize and deduplicate
    3. Enrich with LLM summaries and embeddings
    4. Rank candidates
    5. Generate digest
    """
    logger.info(
        "Starting daily pipeline",
        date=str(date.today()),
        daily_count=config.preferences.digest.daily_count,
        sources_enabled=list(
            k for k, v in config.sources.ats_sources.items() if v.enabled
        ),
    )

    # TODO: Implement pipeline steps
    # await collect_step(config)
    # await normalize_step(config)
    # await enrich_step(config)
    # await rank_step(config)
    # await digest_step(config)

    logger.info("Daily pipeline complete")


def main() -> None:
    """Entry point for the daily pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Determine config directory (allow override via env)
    import os
    config_dir = Path(os.getenv("JOB_AGENT_CONFIG_DIR", "configs"))
    artifacts_dir = Path(os.getenv("JOB_AGENT_ARTIFACTS_DIR", "artifacts"))

    # Load configuration
    try:
        config = load_config(
            config_dir=config_dir,
            artifacts_dir=artifacts_dir,
            write_artifact=True,
        )
    except ConfigValidationError as e:
        logger.error("Configuration error", error=str(e), errors=e.errors)
        sys.exit(1)

    # Run the pipeline
    asyncio.run(run_daily_pipeline(config))


if __name__ == "__main__":
    main()
