# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job Agent is an agentic pipeline that discovers high-confidence job opportunities (Founding AI Engineer / AI Engineer / ML Engineer) from ToS-safe public sources. It runs a daily pipeline: collect from career pages/ATS boards, parse, dedupe, rank, and produce a 3-5 item digest with evidence-backed summaries. No LinkedIn scraping or automation.

The project is built incrementally via checkpoints (A through E). **Currently at Checkpoint A** (Boot + Plan + Collect + Snapshot Store). Checkpoint B (Parsing + Normalization + Dedupe + Candidate Pool) is next.

## Commands

```bash
# Install
uv venv && uv sync --dev

# Run the pipeline entry point
uv run job-agent

# Lint
uv run ruff check .
uv run ruff format --check .

# Type check
uv run mypy .

# Tests (evals directory)
uv run pytest
uv run pytest -m "not integration"         # skip integration tests
uv run pytest evals/test_foo.py::test_bar  # single test

# Docker (Postgres + pgvector + app)
docker compose up -d db       # just the database
docker compose up              # full stack
```

## Architecture

### Pipeline Flow (data flows forward only)

```
Boot (RunContext) → Plan Sources → Collect → [Parse → Dedupe → Rank → Enrich → Digest]
                                              ^--- Checkpoint B onwards
```

Each run gets a `run_id` (format: `YYYYMMDD_HHMMSS_<uuid8>`) and a `RunContext` that travels through every stage carrying config, metrics, and stage logs.

### Module Responsibilities

- **`core/`** — Config loading (`Settings` from env via pydantic-settings, `SourcesConfig` from YAML), `RunContext` lifecycle (boot, stage tracking, metrics), ID generation and URL normalization
- **`collectors/`** — `planner.py` converts `SourceConfig` → `FetchTask` list (planning never fetches). `collector.py` executes fetches via `HttpClient` (rate-limited, retried with tenacity). `adapters/` will hold source-type-specific logic (not yet implemented)
- **`evidence/`** — `RawSnapshot` model and `SnapshotStore` abstraction. `FileSnapshotStore` persists to `data/snapshots/{run_id}/{snapshot_id}.{content,meta.json}`
- **`orchestration/`** — `run_checkpoint_a` sequences Boot → Plan → Collect. New checkpoints will be added as `run_checkpoint_b`, etc.
- **`storage/`** — Placeholder for SQLAlchemy/Alembic DB layer (Checkpoint B)
- **`config/sources.yaml`** — Source registry (career pages, ATS boards with rate limits and metadata)

### Key Design Patterns

- **Stages are idempotent and observable** — each logs items_in/items_out, duration, errors
- **Evidence-first** — raw HTML snapshots are always stored alongside metadata; never trust summaries without source links
- **Config snapshot per run** — saved to `data/config_snapshots/` for reproducibility
- **Separation of concerns** — collectors never rank, rankers never fetch, enrichment never mutates entity identity
- **Structured LLM outputs only** — all LLM usage (future) must use Pydantic models with validation
- **Verbose switches everywhere** — every module, stage, and significant function must support an easy on/off verbose mode (via `VERBOSE=true` env var or `--verbose` CLI flag) that prints human-readable details of what's happening: inputs, outputs, decisions made, data flowing between stages. This is critical during development for understanding and debugging the pipeline flow. Verbose output should use `core/verbose.py` helpers to keep formatting consistent. Default is off in production, but trivially togglable for any dev run

### Data Storage

Currently file-based (`data/` directory, gitignored). Postgres + pgvector planned for Checkpoint B. Config snapshots and raw snapshots are organized by run_id.

## Configuration

- **Environment**: `.env` file (see `.env.example`) — `DATABASE_URL`, `OPENAI_API_KEY`, `LANGFUSE_*` keys
- **Sources**: `config/sources.yaml` — each source has `source_id`, `source_type`, `url`, rate limits, metadata
- **Settings class**: `core/config.py:Settings` — loaded from env with pydantic-settings, defaults to SQLite and file-based storage

## Project Scope References

- `PROJECT_SCOPE.md` — full system design (data model, ranking strategy, phased plan)
- `PHASE_1.md` — detailed stage specs and contracts for Stages 0-4 (through Checkpoint B)
- `CHECKPOINT_A_B.md` — implementation guide for current/next checkpoints
- `notebooks/test_checkpoint_a.ipynb` — interactive validation of the current pipeline

## Tech Stack

Python 3.11, pydantic/pydantic-settings, httpx, tenacity, PyYAML, beautifulsoup4, structlog. Future: SQLAlchemy + Alembic + pgvector, FastAPI + Streamlit, OpenAI + LangChain + LangGraph + Langfuse. Build: hatchling. Package manager: uv. Linter: ruff. Type checker: mypy (strict).
