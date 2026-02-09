# Architecture

## System Overview

Job Agent is an agentic pipeline that discovers high-confidence job opportunities (Founding AI Engineer / AI Engineer / ML Engineer) from ToS-safe public sources. It runs a daily pipeline: collect from career pages and ATS boards, parse, dedupe, rank, and produce a 3-5 item digest with evidence-backed summaries.

### Design Philosophy

- **Data flows forward only** — collectors never rank, rankers never fetch, enrichment never mutates entity identity
- **Evidence-first** — raw HTML snapshots are always stored alongside metadata; never trust summaries without source links
- **Observable and idempotent** — every stage logs items_in/items_out, duration, and errors; safe to re-run
- **Reproducible** — each run snapshots its configuration and preserves all raw data
- **Incremental delivery** — the system is built checkpoint-by-checkpoint (A through E), each a working product slice
- **Structured LLM outputs only** — all LLM usage (future) must use Pydantic models with validation

---

## Pipeline Flow

```
                        IMPLEMENTED (Checkpoint A)
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  ┌──────────┐    ┌──────────────┐    ┌───────────────┐  │
  │  │  Stage 0  │───>│   Stage 1    │───>│    Stage 2    │  │
  │  │   Boot    │    │ Plan Sources │    │   Collect     │  │
  │  │          │    │              │    │  (Fetch +     │  │
  │  │ RunContext│    │ SourceConfig │    │   Snapshot)   │  │
  │  │ + Config  │    │  -> FetchTask│    │              │  │
  │  │ Snapshot  │    │   list       │    │ FetchTask    │  │
  │  └──────────┘    └──────────────┘    │  -> RawSnapshot│  │
  │                                      └───────────────┘  │
  └─────────────────────────────────────────────────────────┘

                        PLANNED (Checkpoint B)
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  ┌──────────────┐    ┌──────────────────┐               │
  │  │   Stage 3    │───>│     Stage 4      │               │
  │  │   Parse +    │    │  Dedupe +        │               │
  │  │  Normalize   │    │  Candidate Pool  │               │
  │  │              │    │                  │               │
  │  │ RawSnapshot  │    │ Company/RoleLead │               │
  │  │  -> Company  │    │  -> CandidateSet │               │
  │  │  -> RoleLead │    │                  │               │
  │  └──────────────┘    └──────────────────┘               │
  └─────────────────────────────────────────────────────────┘

                     PLANNED (Checkpoints C-E)
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  Stage 5: Feature Computation (deterministic)           │
  │  Stage 6: Similarity / Embeddings (optional)            │
  │  Stage 7: Ranking + Selection -> Top 3-5                │
  │  Stage 8: LLM Enrichment (summaries + outreach drafts)  │
  │  Stage 9: Digest Assembly + Artifact Export              │
  │  Stage 10: Feedback Capture (manual, async)              │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
```

---

## Module Breakdown

### `core/` — Configuration, Context, and Utilities *[implemented]*

**Purpose:** Foundation layer providing configuration loading, run lifecycle management, and shared utilities (ID generation, URL normalization, hashing).

**Depends on:** nothing (leaf module)
**Depended on by:** every other module

**Key abstractions:**

| File | Responsibility |
|------|---------------|
| `config.py` | `Settings` (env via pydantic-settings), `SourceConfig` / `SourcesConfig` (YAML), `load_config()`, `snapshot_config()` |
| `context.py` | `RunContext` (the pipeline's traveling context), `RunStatus` enum, `RunMetrics`, `StageLog` |
| `ids.py` | `generate_run_id()`, `content_hash()`, `normalize_url()`, `url_hash()`, `slugify()` |

`RunContext` is the central abstraction — it is created once via `RunContext.boot()` and passed to every stage. It carries configuration, accumulates metrics and stage logs, and records run status transitions.

---

### `collectors/` — Source Planning and HTTP Collection *[implemented]*

**Purpose:** Translate source configuration into fetch tasks (planning), then execute those fetches with rate limiting and retries (collection). Never parses content.

**Depends on:** `core/` (config, context, IDs), `evidence/` (snapshot storage)
**Depended on by:** `orchestration/`

**Key abstractions:**

| File | Responsibility |
|------|---------------|
| `planner.py` | `FetchTask` and `FetchPolicy` models; `plan_sources(ctx)` converts `SourceConfig` entries into `FetchTask` list — planning never fetches |
| `collector.py` | `collect(tasks, ctx, store)` executes fetches via `HttpClient`, creates `RawSnapshot` records, persists via `SnapshotStore` |
| `http_client.py` | `HttpClient` (async context manager with httpx), `RateLimiter` (token bucket), `FetchResult` dataclass; retries via tenacity with exponential backoff |
| `adapters/` | Placeholder for source-type-specific logic (Greenhouse, Lever, Ashby, custom careers pages) — not yet implemented |

**Design:** Planning and collection are strictly separated. `plan_sources` is a pure function of config; `collect` is the only stage that touches the network.

---

### `evidence/` — Raw Snapshot Models and Storage *[implemented]*

**Purpose:** Persist raw fetched content alongside structured metadata. This is the "ground truth" evidence layer that all downstream processing references.

**Depends on:** nothing (leaf module, models only)
**Depended on by:** `collectors/`, `orchestration/`, future `parsing/`

**Key abstractions:**

| File | Responsibility |
|------|---------------|
| `snapshot.py` | `RawSnapshot` model (identity, URLs, fetch metadata, content metadata, error tracking), `SnapshotStore` ABC (save, get_metadata, get_content, list_by_run), `FileSnapshotStore` implementation |

`SnapshotStore` is an abstract base class enabling future storage backends (DB, S3) without changing consuming code. `FileSnapshotStore` writes to `data/snapshots/{run_id}/{snapshot_id}.{content,meta.json}`.

---

### `orchestration/` — Pipeline Sequencing *[implemented]*

**Purpose:** Sequences stages into checkpoint runs. Each checkpoint is a self-contained pipeline that boots, executes stages in order, and records the outcome.

**Depends on:** `core/`, `collectors/`, `evidence/`
**Depended on by:** CLI entry point (`__main__`)

**Key abstractions:**

| File | Responsibility |
|------|---------------|
| `runner.py` | `run_checkpoint_a_async()` sequences Boot -> Plan -> Collect; `run_checkpoint_a()` is the sync wrapper; `get_checkpoint_a_results()` for inspection |

**Error handling:** If any stage raises an exception, the run is marked `FAILED` and the error is appended to the current stage's error list. Individual fetch failures within the collect stage are recorded but do not abort the run (continue-on-failure).

---

### `storage/` — Database Layer *[placeholder]*

**Purpose:** SQLAlchemy models, Alembic migrations, and repository pattern for persistent entity storage (Companies, RoleLeads, Runs, Digests, Feedback).

**Planned for:** Checkpoint B (Postgres + pgvector)

---

### `parsing/` — Parsing and Normalization *[planned]*

**Purpose:** Convert raw snapshots into structured entities. Source-type-specific adapters (Greenhouse, Lever, custom HTML) extract companies and role leads. Deterministic — no LLM usage.

**Planned for:** Checkpoint B

**Expected abstractions:** `ParserEngine` with adapter interface per source type, shared normalizers, `ParsedItem` intermediate records, parse logs.

---

### `intelligence/` — Features, Ranking, and Enrichment *[planned]*

**Purpose:** Compute deterministic features (title match, recency, location), optionally compute embedding similarity, rank candidates into a top 3-5 shortlist, and enrich selected recommendations with LLM-generated summaries and outreach drafts.

**Planned for:** Checkpoints C and D

**Expected submodules:** `features.py`, `embeddings.py`, `ranking.py`, `enrichment.py`, `outreach.py`

---

### `artifacts/` — Digest Export *[planned]*

**Purpose:** Assemble the daily digest artifact (JSON + markdown/HTML) from ranked and enriched recommendations.

**Planned for:** Checkpoint D

---

## Data Flow

Each stage has well-defined inputs and outputs. Data flows strictly forward.

```
Stage 0 (Boot)
  IN:  .env, config/sources.yaml
  OUT: RunContext (run_id, settings, sources)
       Config snapshot -> data/config_snapshots/{run_id}_config.json

Stage 1 (Plan Sources)
  IN:  RunContext.sources (list of SourceConfig)
  OUT: list[FetchTask] (in-memory, logged via StageLog)

Stage 2 (Collect)
  IN:  list[FetchTask]
  OUT: list[RawSnapshot]
       Raw content -> data/snapshots/{run_id}/{snapshot_id}.content
       Metadata    -> data/snapshots/{run_id}/{snapshot_id}.meta.json

--- Checkpoint A boundary (above is implemented) ---

Stage 3 (Parse + Normalize) [planned]
  IN:  RawSnapshots from current run
  OUT: Company records, RoleLead records (upserted to DB)
       ParseLog entries

Stage 4 (Dedupe + Candidate Pool) [planned]
  IN:  Companies, RoleLeads, preferences/exclusions
  OUT: CandidateSet (persisted per run)
       Updated seen_count, last_seen on RoleLeads

--- Checkpoint B boundary ---

Stages 5-9 (Features -> Ranking -> Enrichment -> Digest) [planned]
  IN:  CandidateSet
  OUT: Ranked shortlist, enriched summaries, daily digest artifact

Stage 10 (Feedback) [planned]
  IN:  User labels on recommendations
  OUT: Feedback records for learning loop
```

### Evidence Chain

Every recommendation traces back to raw evidence:

```
Digest Item -> Recommendation -> RoleLead -> RawSnapshot -> raw HTML + URL
```

Raw snapshots are immutable once stored. Content hashes (`SHA-256[:16]`) detect changes across runs. Canonical URLs (tracking params stripped, normalized) enable deduplication.

---

## Orchestration

### Run Lifecycle

1. **Boot:** `RunContext.boot(settings, sources)` generates a `run_id` (format: `YYYYMMDD_HHMMSS_<uuid8>`), saves a config snapshot to disk, and returns an initialized `RunContext` with status `RUNNING`.

2. **Stage execution:** Each stage calls `ctx.start_stage(name, items_in)` at entry and `ctx.complete_stage(name, items_out, errors)` at exit. This produces `StageLog` entries with timing, counts, and error lists.

3. **Metrics accumulation:** `RunMetrics` on the context tracks aggregate counters (`num_fetch_tasks`, `num_snapshots_success`, `num_snapshots_failed`, etc.) that stages update directly.

4. **Completion:** `ctx.complete_run(status)` sets the final status (`COMPLETED` or `FAILED`) and timestamp.

### Error Handling

- **Stage-level:** Individual item failures within a stage are logged but do not abort the stage (continue-on-failure). The stage completes with a list of error strings.
- **Run-level:** If a stage raises an unhandled exception, the run is marked `FAILED` and the error is appended to the failing stage's log. The exception propagates to the caller.
- **Empty results:** If planning produces zero tasks (e.g., all sources disabled), the run completes successfully with no collection.

### Checkpoint Sequencing

Checkpoints are implemented as separate functions (`run_checkpoint_a`, future `run_checkpoint_b`, etc.). Each checkpoint extends the previous one with additional stages. The orchestrator creates the required infrastructure (e.g., `FileSnapshotStore`) and wires stages together.

---

## Configuration

### Two-Layer Config

| Layer | Source | Model | Purpose |
|-------|--------|-------|---------|
| Environment | `.env` file | `Settings` (pydantic-settings) | Runtime: DB URL, storage paths, timeouts, rate limits, feature flags |
| Source Registry | `config/sources.yaml` | `SourcesConfig` (list of `SourceConfig`) | What to collect: URLs, source types, per-source rate limits, metadata |

`load_config()` loads both layers and returns `(Settings, SourcesConfig)`.

### Config Snapshot

Every run persists its resolved configuration to `data/config_snapshots/{run_id}_config.json` via `snapshot_config()`. This includes the full `Settings` dump and all source configurations, making any run reproducible.

### Source Configuration

Each source entry in `sources.yaml` specifies:
- `source_id` — unique identifier (e.g., `anthropic_careers`)
- `source_type` — `careers_page`, `ats_board`, or `rss`
- `url` — target URL
- `enabled` — toggle without removing the entry
- Rate limits, timeouts, retry counts
- `metadata` — arbitrary key-value pairs (company name, priority, ATS provider)

---

## Storage and Evidence Layer

### Current: File-Based Storage

```
data/
  config_snapshots/
    {run_id}_config.json          # resolved config for reproducibility
  snapshots/
    {run_id}/
      {snapshot_id}.meta.json     # RawSnapshot metadata (Pydantic JSON)
      {snapshot_id}.content       # raw fetched bytes (HTML/text)
```

`FileSnapshotStore` implements the `SnapshotStore` ABC. Content and metadata are stored as separate files, organized by run. Lookups by `snapshot_id` scan across runs; lookups by `run_id` are directory-scoped.

### Planned: Database Layer (Checkpoint B+)

- **Postgres + pgvector** for structured entities (Companies, RoleLeads, Runs, Feedback) and embedding similarity search
- **SQLAlchemy + Alembic** for ORM and migrations
- **Repository pattern** in `storage/` for data access
- Raw snapshot storage may remain file-based (or migrate to S3) while metadata moves to the database

---

## Checkpoint Progression

| Checkpoint | Stages | What It Adds | Status |
|-----------|--------|-------------|--------|
| **A** | 0-2 | Boot + Plan + Collect + Snapshot Store | **Implemented** |
| **B** | 0-4 | Parsing + Normalization + Dedupe + Candidate Pool + DB layer | Planned (next) |
| **C** | 0-7 | Deterministic features + Ranking -> shortlist of 3-5 | Planned |
| **D** | 0-9 | LLM enrichment + Outreach drafts + Daily digest artifact | Planned |
| **E** | 0-10 | Feedback capture + Learning loop foundation | Planned |

Each checkpoint is a working "product slice" — the system is useful at every stage, with increasing intelligence and polish.

### Module Dependencies by Checkpoint

```
Checkpoint A:  core ─── collectors ─── evidence ─── orchestration

Checkpoint B:  core ─┬─ collectors ─── evidence
                     ├─ parsing (new)
                     ├─ storage (new: DB + repos)
                     └─ orchestration (extended)

Checkpoint C:  ... + intelligence/features + intelligence/ranking

Checkpoint D:  ... + intelligence/enrichment + artifacts

Checkpoint E:  ... + feedback capture (storage + API)
```
