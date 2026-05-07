# DECISIONS
Purpose: append-only decision log that records the rationale behind truth.

## Links
- PROJECT section: <PROJECT §...>
- ENGINEERING section: <ENGINEERING §...>
- PLAN: <P-xx — name>

## Format
YYYY-MM-DD — Decision: <what we chose>
Why: <reasoning / constraints>
Alternatives: <A/B/C considered>
Consequences: <implications / tradeoffs>
Links: <PROJECT §... | ENGINEERING §... | PLAN: P-xx>

---

YYYY-MM-DD — Decision: ...
Why: ...
Alternatives: ...
Consequences: ...
Links: ...

2026-01-25 — Decision: Satellite-only assessment (no ground sensors/field visits)
Why: Core constraint for speed, scale, and cost in early deployment.
Alternatives: Add field surveys; hybrid satellite + IoT sensing.
Consequences: Higher uncertainty in some indicators; must include confidence and conservative flags.
Links: PROJECT §MVP scope | ENGINEERING §Data & signals

2026-01-25 — Decision: MVP is decision support, not automated financing
Why: Trust and interpretability are required; early models may be imperfect.
Alternatives: Automated approval/rejection rules.
Consequences: Outputs must explain reasons and confidence; users remain in control.
Links: PROJECT §Outputs (what the user sees)

2026-01-25 — Decision: MVP gap handling uses smoothing + light interpolation with confidence penalty
Why: Simple, fast, explainable approach for early deployment.
Alternatives: Multi-source fusion or model-based imputation.
Consequences: Long gaps may still mislead; confidence must be conservative.
Links: ENGINEERING §Pipeline

2026-01-25 — Decision: Include broad crop category in MVP; yield bands deferred
Why: Adds decision value with lower label burden; yield bands need stronger validation.
Alternatives: Defer crop categories; introduce yield bands early.
Consequences: Crop outputs remain coarse; yield insight postponed until evidence is stronger.
Links: PROJECT §MVP scope

2026-01-25 — Decision: MVP scope boundaries and workflow
Why: Aligns early delivery with trust, coverage, and operational simplicity.
Alternatives: Pilot-only geography; larger plot size bounds; request-centric workflow; aggressive flags.
Consequences: National scope with 1–200 feddan focus; lands-only portal; conservative risk flags; weak-label validation with optional public-area review.
Links: PROJECT §MVP scope

2026-01-25 — Decision: Data sources use Sentinel-2 with Landsat fallback
Why: Improves continuity while staying on open data sources.
Alternatives: Sentinel-2 only; add commercial sources.
Consequences: Handle cross-sensor consistency in processing and confidence.
Links: ENGINEERING §Data & signals

2026-01-27 — Decision: Phase A repo layout with shared contracts folder
Why: Enables parallel work while keeping schema truth centralized.
Alternatives: Split repos; flat services-only without shared contracts.
Consequences: Contracts must be maintained and validated across services.
Links: ENGINEERING §Repo structure (Phase A) | ENGINEERING §Contracts (source of truth)

2026-01-27 — Decision: Phase A schema tooling stack
Why: Enforceable payload contracts across API and portal with minimal overhead.
Alternatives: Pydantic-only; OpenAPI-first without JSON Schema; no contract validation.
Consequences: Schemas are authoritative; generated types are disposable.
Links: ENGINEERING §Contracts (source of truth)

2026-01-27 — Decision: Phase A demo entry point uses scripts (no Docker required)
Why: Faster, Windows-friendly demo for team onboarding.
Alternatives: Docker-only demo; manual multi-command setup.
Consequences: Maintain scripts for starting services, seeding AOI, and printing URLs.
Links: ENGINEERING §Ops & scaling

2026-01-27 — Decision: Phase A indicator set locked to minimal outputs
Why: Reduce model scope and focus on demo-ready, explainable signals.
Alternatives: Full indicator suite; include crop classes or yield bands in Phase A.
Consequences: Limited outputs but faster integration and lower risk.
Links: ENGINEERING §Data & signals

2026-01-29 — Decision: Phase A role breakdown adjusted
Why: Reduce Phase A scope by deferring governance/QA/versioning and split seasonal analysis for parallel delivery.
Alternatives: Keep storage/curation as a dedicated role; keep ML/time-series as a single role.
Consequences: Ingestion owns minimal persistence; seasonal analysis is a distinct handoff to scoring.
Links: PROJECT §Phase 1 ownership | ENGINEERING §Phase scope notes

2026-01-29 — Decision: Phase A uses direct worker flow, queue deferred
Why: POC scope does not require multi-user concurrency; faster setup and debugging.
Alternatives: Introduce queue/broker in Phase A.
Consequences: Limited concurrency and reliability in Phase A; queue added in Phase B.
Links: PROJECT §MVP scope | ENGINEERING §Ops & scaling

2026-03-07 — Decision: Use `farmtrust_core/` as the single top-level importable Python package
Why: Keep reusable pipeline logic in one place so worker and API consume the same implementation and avoid duplication.
Alternatives: Keep logic inside service-specific folders; split reusable logic across multiple utility packages.
Consequences: Cleaner long-term reuse and simpler imports; requires disciplined boundaries so service-specific concerns do not leak into core.
Links: ENGINEERING §Repo structure (Phase A) | PLAN: P-01 — Starter pipeline for three roles

2026-03-12 — Decision: Use lean default dependency install with `data` extra for ingestion
Why: Keep default environment small for faster onboarding and lower install friction while preserving a clear opt-in path for heavy geospatial dependencies.
Alternatives: Keep ingestion/geospatial dependencies in main dependencies so `uv sync` installs everything by default.
Consequences: Ingestion contributors must run `uv sync --extra data`; docs and runbooks must point to extra-based setup to avoid missing-package errors.
Links: ENGINEERING §Dev workflow (Phase A) | README §Python environment (uv)

2026-05-07 — Decision: Pre-download deduplication strategy for Sentinel-2 scenes
Why: STAC returns multiple scenes per date when AOIs span tile boundaries or when S2A and S2B both acquire on the same day. Without dedup, redundant tiles waste bandwidth and pollute the time series with duplicate observations.
Alternatives: Deduplicate after processing using valid_fraction (AOI-specific quality); no dedup (keep all scenes for mosaic use cases).
Consequences: Pre-download filter saves bandwidth and download time. eo:cloud_cover (tile-wide metadata) is the practical pre-filter criterion; valid_fraction (computed from SCL) remains the gold-standard quality metric but requires downloading first. --no-dedupe flag preserves raw mode when needed.
Links: ENGINEERING §Pipeline | docs/documentations/00-phaseA_ingestion_full_writeup.md §12

2026-05-07 — Decision: Parallel scene downloads via ThreadPoolExecutor (max_workers=4 default)
Why: Each scene requires 6 HTTP range requests to COG assets on Planetary Computer — purely I/O-bound. Sequential processing left all workers idle while waiting on network. ThreadPoolExecutor bypasses the GIL for I/O and gives ~4x speedup with no code-complexity penalty.
Alternatives: async/await (more complex refactor, no clear benefit for this workload); single-threaded (available via --workers 1 for debugging).
Consequences: Rate limit risk above ~8 workers on Planetary Computer (free tier). Retry logic with exponential backoff and SAS token re-signing on each attempt handles transient failures. max_workers is tunable via --workers CLI flag or "workers" key in config JSON.
Links: ENGINEERING §Pipeline | ENGINEERING §Ops & scaling

2026-05-07 — Decision: Split scripts/ingest_aoi.py into focused farmtrust_core/ingest/ modules
Why: The script grew to 797 lines across 5 unrelated concerns (raster I/O, index CRUD, dedup, parallel worker, orchestration). Logic in scripts/ is not importable or unit-testable.
Alternatives: Keep monolithic script; split into fewer but larger modules.
Consequences: scripts/ingest_aoi.py is now ~100 lines (CLI argument parsing only). All pipeline logic lives in farmtrust_core/ingest/ and can be imported and tested independently. New modules: window_read.py, scene_index.py, dedup.py, processor.py, pipeline.py.
Links: ENGINEERING §Repo structure | DECISIONS 2026-03-07 (farmtrust_core single package)
