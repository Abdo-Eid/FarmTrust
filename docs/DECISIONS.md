# DECISIONS
Purpose: curated decision log that records the rationale behind truth.

## Links
- PROJECT section: <PROJECT §...>
- ENGINEERING section: <ENGINEERING §...>
- TASK: <T-xx — name>

## Format
YYYY-MM-DD — Decision: <what we chose>
Why: <reasoning / constraints>
Alternatives: <A/B/C considered>
Consequences: <implications / tradeoffs>
Links: <PROJECT §... | ENGINEERING §... | TASK: T-xx>
Supersedes: <optional previous date/title>
Refines: <optional previous date/title>

---

2026-01-25 — Decision: Satellite-only assessment (no ground sensors/field visits)
Why: Core constraint for speed, scale, and cost in early deployment.
Alternatives: Add field surveys; hybrid satellite + IoT sensing.
Consequences: Higher uncertainty in some indicators; must include assessment confidence and conservative flags.
Links: PROJECT §Current-build scope | ENGINEERING §Data & signals

2026-01-25 — Decision: Current-build decision support, not automated financing
Why: Trust and interpretability are required; early models may be imperfect.
Alternatives: Automated approval/rejection rules.
Consequences: Outputs must explain reasons and assessment confidence; users remain in control.
Links: PROJECT §Outputs (what the user sees)

2026-01-25 — Decision: Current-build gap handling uses smoothing + light interpolation with assessment-confidence penalty
Why: Simple, fast, explainable approach for early deployment.
Alternatives: Multi-source fusion or model-based imputation.
Consequences: Long gaps may still mislead; assessment confidence must be conservative.
Links: ENGINEERING §Pipeline

2026-01-25 — Decision: Current-build scope boundaries and workflow
Why: Aligns early delivery with trust, coverage, and operational simplicity.
Alternatives: Pilot-only geography; larger plot size bounds; request-centric workflow; aggressive flags.
Consequences: National scope with 1–200 feddan focus; lands-only portal; conservative risk flags; weak-label validation with optional public-area review.
Links: PROJECT §Current-build scope

2026-01-27 — Decision: Current-build repo layout with shared contracts folder
Why: Enables parallel work while keeping schema truth centralized.
Alternatives: Split repos; flat services-only without shared contracts.
Consequences: Contracts must be maintained and validated across services.
Links: ENGINEERING §Repo structure (current build) | ENGINEERING §Contracts (source of truth)

2026-01-27 — Decision: Current-build schema tooling stack
Why: Enforceable payload contracts across API and portal with minimal overhead.
Alternatives: Pydantic-only; OpenAPI-first without JSON Schema; no contract validation.
Consequences: Schemas are authoritative; generated types are disposable.
Links: ENGINEERING §Contracts (source of truth)

2026-01-27 — Decision: Current-build demo entry point uses scripts (no Docker required)
Why: Faster, Windows-friendly demo for team onboarding.
Alternatives: Docker-only demo; manual multi-command setup.
Consequences: Maintain scripts for starting services, seeding AOI, and printing URLs.
Links: ENGINEERING §Ops & scaling

2026-01-27 — Decision: Current-build indicator set locked to minimal outputs
Why: Reduce model scope and focus on demo-ready, explainable signals.
Alternatives: Full indicator suite; include additional crop/yield outputs in the current build.
Consequences: Limited outputs but faster integration and lower risk.
Links: ENGINEERING §Data & signals

2026-01-29 — Decision: Current-build role breakdown adjusted
Why: Reduce current-build scope by deferring governance/QA/versioning and split seasonal analysis for parallel delivery.
Alternatives: Keep storage/curation as a dedicated role; keep ML/time-series as a single role.
Consequences: Ingestion owns minimal persistence; seasonal analysis is a distinct handoff to scoring.
Links: PROJECT §Current Build ownership | ENGINEERING §Scope notes

2026-01-29 — Decision: Current build uses direct worker flow, queue deferred
Why: POC scope does not require multi-user concurrency; faster setup and debugging.
Alternatives: Introduce queue/broker in the current build.
Consequences: Limited concurrency and reliability in the current build; queue added when multi-user reliability is needed.
Links: PROJECT §Current-build scope | ENGINEERING §Ops & scaling

2026-03-07 — Decision: Use `farmtrust_core/` as the single top-level importable Python package
Why: Keep reusable pipeline logic in one place so worker and API consume the same implementation and avoid duplication.
Alternatives: Keep logic inside service-specific folders; split reusable logic across multiple utility packages.
Consequences: Cleaner long-term reuse and simpler imports; requires disciplined boundaries so service-specific concerns do not leak into core.
Links: ENGINEERING §Repo structure (current build)

2026-03-12 — Decision: Use lean default dependency install with `data` extra for ingestion
Why: Keep default environment small for faster onboarding and lower install friction while preserving a clear opt-in path for heavy geospatial dependencies.
Alternatives: Keep ingestion/geospatial dependencies in main dependencies so `uv sync` installs everything by default.
Consequences: Ingestion contributors must run `uv sync --extra data`; docs and runbooks must point to extra-based setup to avoid missing-package errors.
Links: ENGINEERING §Dev workflow (current build) | README §Python environment (uv)

2026-05-07 — Decision: Pre-download deduplication strategy for Sentinel-2 scenes
Why: STAC returns multiple scenes per date when AOIs span tile boundaries or when S2A and S2B both acquire on the same day. Without dedup, redundant tiles waste bandwidth and pollute the time series with duplicate observations.
Alternatives: Deduplicate after processing using valid_fraction (AOI-specific quality); no dedup (keep all scenes for mosaic use cases).
Consequences: Superseded by the cube path's solar-day grouping/mosaicking. eo:cloud_cover remains the practical pre-download filter; valid_fraction (computed from SCL) remains the gold-standard quality metric but requires downloading first. The legacy `--no-dedupe` raw mode was removed with the rasterio/chip path.
Links: ENGINEERING §Pipeline | docs/documentations/00-current-build-ingestion-full-writeup.md §12

2026-05-07 — Decision: Parallel scene downloads via ThreadPoolExecutor (max_workers=4 default)
Why: Each scene requires 6 HTTP range requests to COG assets on Planetary Computer — purely I/O-bound. Sequential processing left all workers idle while waiting on network. ThreadPoolExecutor bypasses the GIL for I/O and gives ~4x speedup with no code-complexity penalty.
Alternatives: async/await (more complex refactor, no clear benefit for this workload); single-threaded (available via --workers 1 for debugging).
Consequences: Rate limit risk above ~8 workers on Planetary Computer (free tier). Retry logic with exponential backoff and SAS token re-signing on each attempt handles transient failures. max_workers is tunable via --workers CLI flag or "workers" key in config JSON.
Links: ENGINEERING §Pipeline | ENGINEERING §Ops & scaling

2026-05-07 — Decision: Split scripts/ingest_aoi.py into focused farmtrust_core/ingest/ modules
Why: The script grew to 797 lines across 5 unrelated concerns (raster I/O, index CRUD, dedup, parallel worker, orchestration). Logic in scripts/ is not importable or unit-testable.
Alternatives: Keep monolithic script; split into fewer but larger modules.
Consequences: scripts/ingest_aoi.py is now CLI argument parsing only. All pipeline logic lives in farmtrust_core/ingest/ and can be imported and tested independently. The initial rasterio modules (`window_read.py`, `scene_index.py`, `dedup.py`, `processor.py`, `pipeline.py`) were later removed when the ODC cube path became the single ingestion implementation.
Links: ENGINEERING §Repo structure | DECISIONS 2026-03-07 (farmtrust_core single package)

2026-05-13 — Decision: Current build skips crop category and upgrades to interval-based land assessment
Why: The first lender-facing current-build output must prioritize trust, explainability, and interval-level evidence over breadth. Crop category is weaker than land status, trend, season performance, and risk signals with the current validation level.
Alternatives: Keep broad crop category in the current build; add more categories before the assessment layer is stable.
Consequences: The current build now focuses on smoothed metric evidence, season count, interval-based land status, trend, latest-season performance, conservative risk flags, satellite evidence coverage, and assessment confidence. Crop/category output is deferred until stronger validation exists.
Links: PROJECT §Outputs (what the user sees) | PROJECT §Current-build scope (what we ship first) | ENGINEERING §Land assessment artifact
Refines: 2026-01-27 — Current-build indicator set locked to minimal outputs

2026-05-18 — Decision: Current-build preprocessing does not interpolate or synthesize timestamps
Why: Preserve observation truth and make gaps explicit for downstream assessment confidence, seasonal interpretation, and lender-facing explanations.
Alternatives: Keep light interpolation as the current-build default; resample to canonical monthly timestamps.
Consequences: Preprocessing smooths usable observations and reports gap diagnostics; downstream scoring must reason about observation count, long gaps, satellite evidence coverage, and assessment confidence instead of assuming contiguous time series.
Links: PIPELINE §Preprocessing | ENGINEERING §Pipeline boundary
Refines: 2026-01-25 — Current-build gap handling uses smoothing + light interpolation with assessment-confidence penalty

2026-05-18 — Decision: Document current implementation separately from intended product behavior
Why: Some current-build code is still mock/dev oriented, while the product direction remains user-drawn polygon input, a 24-month assessment window, and unresolved satellite-source strategy.
Alternatives: Rewrite docs to match only current code; leave non-current ideas embedded in canonical docs.
Consequences: Workstream docs must clearly label current implementation versus intended behavior. Current implemented source is Sentinel-2; Landsat and other source choices are unresolved and tracked outside product scope. Current CLI AOI input is bbox/config; intended product AOI input is a drawn polygon.
Links: PROJECT §Current-build scope | ENGINEERING §Data & signals | PIPELINE §Boundaries and handoffs

2026-05-18 — Decision: Remove unused STAC query cache, keep local source reuse
Why: The expensive ingestion work is source-pixel download, COG reads, and index computation. The active pipeline skips reusable work through `cube.zarr`, `scenes_index.jsonl`, cache keys, and per-band completeness checks. A TTL-based STAC query-result cache risks stale scene lists and was not wired into the active pipeline.
Alternatives: Keep the unused helper for later; wire the STAC query cache into the active pipeline now.
Consequences: STAC is queried on each ingestion run. Local cube/band reuse remains active and skips already-present source bands for matching AOI/grid configuration; derived CSV processing can rerun from local pixels. If STAC search becomes a proven bottleneck later, revisit with explicit freshness and invalidation rules.
Links: PIPELINE §Local reuse behavior | ENGINEERING §Pipeline boundary
Supersedes: 2026-01-25 — Data sources use Sentinel-2 with Landsat fallback

2026-06-16 — Decision: Isolate non-committed future ideas in `FUTURE.md`
Why: Detailed future ideas in product or engineering truth bias later brainstorming and make speculative direction look committed.
Alternatives: Keep non-committed ideas embedded in `PROJECT.md` and `ENGINEERING.md`; delete parked ideas entirely.
Consequences: `PROJECT.md` and `ENGINEERING.md` stay focused on current truth. `FUTURE.md` preserves ideas but is not scope, roadmap, or architecture truth; items must be re-evaluated before promotion.
Links: PROJECT §Future ideas | ENGINEERING §Exploration boundary | FUTURE.md

2026-06-17 — Decision: Gap diagnostics describe evidence coverage, not land risk
Why: Cloud gaps and weak satellite coverage are data limitations, not farmer or land failures. User-facing outputs must not make evidence gaps look like land risk.
Alternatives: Expose internal `gap_risk` directly; hide gap diagnostics entirely; treat gaps as land risk flags.
Consequences: User-facing surfaces should use satellite evidence coverage and assessment confidence. Internal fields such as `gap_risk` may remain pipeline helpers, but they must map to evidence limitations, not land/farmer problems. Land risk flags remain reserved for land-condition signals such as waterlogging, salinity likelihood, abandonment, and encroachment / land-use change.
Links: PROJECT §Outputs (what the user sees) | PROJECT §Big picture (end-to-end) | PIPELINE §Evidence coverage interpretation
Refines: 2026-05-18 — Current-build preprocessing does not interpolate or synthesize timestamps

2026-06-20 — Decision: Move to ODC/xarray cube ingestion as primary path (T-06)
Why: The scene-centred rasterio path had three silent bugs — effective 20m resolution (grid built from SCL window), in-tile-only valid_fraction denominator for boundary AOIs, and missing BOA offset for post-2022 data. Cube ingestion fixes all three and better models the multi-year time-series use case.
Alternatives: Keep rasterio path and patch bugs individually; switch to stackstac instead of odc-stac.
Consequences: Primary loader is now odc.stac.load; rasterio path retained as reference/equivalence checker until promotion criteria pass. CSV row semantics change from "one STAC scene" to "one solar-day mosaic". BOA reflectance offset (DN-1000)/10000 is now applied explicitly. Cache is keyed by solar_day and excludes start_date/end_date; date-range changes append absent days without rewriting existing chunks.
Links: ENGINEERING §Pipeline boundary | T-06

2026-06-20 — Decision: odc-stac as the cube loader, not stackstac (D1)
Why: Per-band resampling is required — SCL needs nearest-neighbour (fractional class codes are meaningless) while reflectance needs bilinear. stackstac.stack() applies one kernel to all assets; odc.stac.load accepts a per-band resampling dict natively.
Alternatives: stackstac (rejected: no per-band resampling); manual per-band rasterio reads (rejected: loses the mosaicking and alignment benefits of cube loading).
Consequences: New declared dependency odc-stac. dask[array] is now explicitly declared (previously an undeclared transitive dep of stackstac). stackstac kept temporarily until equivalence check passes.
Links: T-06 D1

2026-06-20 — Decision: Solar-day mosaicking replaces per-scene dedup (D3)
Why: The prior dedup grouped by (date, spacecraft) and discarded one tile for boundary AOIs, silently excluding 40%+ of the AOI while valid_fraction still read ~1.0. groupby="solar_day" mosaics all overlapping tiles and produces correct full-AOI coverage.
Alternatives: Keep per-scene dedup; add post-hoc mosaic step in rasterio path.
Consequences: CSV row now means "one solar-day mosaic." valid_fraction finally describes the whole AOI for boundary-crossing cases. Rasterio equivalence check will show a difference — the cube is correct; the rasterio value was silently truncated.
Links: T-06 D3

2026-06-20 — Decision: Apply BOA reflectance offset explicitly in cube path (D6)
Why: Sentinel-2 baseline 04.00 (Jan 2022) introduced BOA_ADD_OFFSET = -1000. Correct surface reflectance = (DN-1000)/10000. The rasterio path used DN/10000 with no offset, biasing post-2022 reflectance ~0.1 high and NDVI ~0.1–0.2. odc.stac.load is configured with integer dtypes so it returns raw DN, and apply_boa_offset() applies the correct formula including treating DN=0 as NODATA.
Alternatives: Rely on odc auto-scale from STAC raster:bands metadata (rejected: version-specific behaviour, untestable offline, no DN=0 NODATA handling).
Consequences: Offset policy is part of the per-solar-day cache key. Any delta from the rasterio path is a rasterio bug, not a cube regression. Equivalence-to-rasterio is a sanity check against a biased reference, not proof of correctness.
Links: T-06 D6

2026-06-20 — Decision: Cache keyed by solar_day, excluding start_date/end_date (D7)
Why: The rasterio cache included start_date/end_date in the fingerprint, so any date-range extension forced a full re-fetch of all prior scenes. The cube migration keeps the cache unit as the solar-day mosaic, keyed on params that change that day's output (geometry/bbox, CRS, resolution, resampling, SCL classes, max_cloud, offset_policy). start_date/end_date select the window, they do not change individual day outputs; absent days are appended to existing cubes and processed into sorted CSV rows.
Alternatives: Include dates in key (rejected: breaks incremental extension); cache the full pixel cube as Zarr (rejected at the time as overkill — later reversed, see 2026-06-20 "Persist the solar-day cube as `cube.zarr`").
Consequences: Same-window reruns can skip/replay current solar-day downloads. The offset_policy and AOI identity are in the key, so changing processing policy or bbox/geometry invalidates stale source pixels automatically. Incremental date-range extension appends only missing solar days; the on-disk time axis may be append-ordered, while the JSONL ledger and sorted CSV are the downstream contract.
Links: T-06 D7

2026-06-20 — Decision: Loader-agnostic ingestion seam; rasterio path removed (T-06)
Why: The API worker and CLI both imported the concrete rasterio loader (`write_outputs`) and caught its concrete `PipelineCancelledError`. Coupling callers to an implementation meant the cube migration rippled into every caller. A single seam keeps the interface stable so the implementation can change underneath.
Alternatives: Keep both loaders behind a `--loader` switch duplicated in each caller; make loader exceptions subclass a shared base instead of translating in the runner.
Consequences: New module `farmtrust_core/ingest/runner.py` exposes `run_ingestion(loader="odc", ...)` plus a loader-neutral `IngestCancelled` (the runner translates `CubePipelineCancelledError`). Worker and CLI depend only on the seam. The five rasterio files (`pipeline.py`, `processor.py`, `window_read.py`, `dedup.py`, `scene_index.py`) and the `stackstac` dependency were deleted after the cube path passed the full preprocess→seasonal→scoring chain. The cube CSV gained `timestamp` (solar_day at 00:00 UTC) and `item_id` (representative id) columns so preprocess `REQUIRED_COLUMNS` is satisfied without changing preprocessing (T-06 OUT scope).
Links: ENGINEERING §Pipeline boundary | T-06
Refines: 2026-06-20 — Move to ODC/xarray cube ingestion as primary path (T-06)

2026-06-20 — Decision: Persist the solar-day cube as `cube.zarr`; split ingestion into download/process phases
Why: The cube is now a reusable on-disk dataset asset, not a throwaway in-memory reduction. Storing raw DN pixels lets a policy change (BOA offset, SCL validity classes, a new index) reprocess locally with no re-download. Pre-allocating the full sorted time axis and region-writing each day keeps the on-disk axis sorted regardless of download-completion order while bounding memory to one day in flight.
Alternatives: Keep the in-memory reduce-and-discard model (D7's original stance); persist via NetCDF or per-day GeoTIFF/COG (COG pays off only at district/region clip scale — deferred); fuse download+process into one pass (rejected: couples network and compute, loses reprocess-without-redownload, and the stats are cheap relative to network so fusion saves little).
Consequences: Four sibling artifacts per AOI — `cube.zarr` (primary source artifact: raw-DN pixels + per-day provenance on one sorted time axis, config in root attrs; 10m bands in the root group and native 20m bands in the `20m` group), `indices_timeseries.csv` (derived stats export / downstream handoff), `run_metadata.json` (run config; Phase 2's config read-path; kept because preprocess/scoring/api read it), and `scenes_index.jsonl` v4+ (operational ledger — `cache_key`+`status` plus per-band `band_status` when backfill is used). Derived stats are recomputed from cube pixels and are not stored in the source cube. The ledger, not the cube's time axis, is authoritative about which days are real, so phantom zero-filled slots from failed/cancelled downloads are never processed. Missing requested bands are repairable/backfilled independently and do not force existing bands to be rewritten. `zarr` added to the `data` extra; new stores prefer Zarr v2 with `consolidated=False`, while writes to existing stores preserve their current Zarr format. No JSON→JSONL migration across the storage-model change: existing AOI dirs with no cube re-download on first run.
Links: ENGINEERING §Pipeline boundary | PIPELINE §Ingestion
Refines: 2026-06-20 — Cache keyed by solar_day, excluding start_date/end_date (D7)

2026-06-17 — Decision: Insufficient satellite evidence requires manual review
Why: A completed pipeline run can still lack enough usable evidence for a final automated land assessment. In that case, the product must avoid implying land/farmer failure or issuing unsupported financing-review signals.
Alternatives: Return a provisional automated land status; return no assessment object; treat insufficient evidence as a high-risk land result.
Consequences: API and reports expose `assessment_status: complete | manual_review_required`. Manual-review results keep satellite evidence coverage and low assessment confidence, but do not present final automated `land_status`, `trend_2y`, `season_performance`, `risk_tier`, or land risk flags. Confidence is capped by evidence coverage: no cap for `good`, max `medium` for `fair`, max `low` for `limited`, and `low` for `insufficient`.
Links: PROJECT §Outputs (what the user sees) | ENGINEERING §Assessment artifact boundary | PIPELINE §Evidence coverage interpretation
Refines: 2026-06-17 — Decision: Gap diagnostics describe evidence coverage, not land risk
