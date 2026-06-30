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

2026-06-29 — Decision: Multi-AOI submissions share one ingestion job and combined-bbox download
Why: Neighboring lands should avoid repeated Sentinel-2 COG reads when one bbox request can cover the submitted AOI set. The analytical boundary remains each land polygon, so reports and scores stay per AOI while the source download is shared.
Alternatives: Reject multi-polygon GeoJSON and require separate submissions; store multiple polygons as one `MultiPolygon` land record; download each polygon independently.
Consequences: A GeoJSON `FeatureCollection` or `MultiPolygon` creates one parent assessment group/submission and separate child land records tied to one job. The worker downloads a shared cube for the combined bbox and processes each polygon mask independently. The portal lists the parent group as the top-level item; stopping the parent job stops all child AOIs in that submission. Far-apart polygons may over-read a large bbox until distance-based grouping is added later.
Links: ENGINEERING §Architecture | ENGINEERING §Pipeline boundary | TASK: T-07

2026-06-27 — Decision: Product anchor is lender-facing farm risk reports for credit-readiness review
Why: The strongest and most credible current direction is a defensible satellite-to-risk-report product for lenders. Monitoring, AI explanation, crop/yield POCs, segmentation, and data-company expansion should be staged around that anchor instead of presented as the first product.
Alternatives: Start as a general agriculture platform; lead with monitoring; lead with an AI assistant; position crop/yield models as the core current product.
Consequences: Current-build wording stays conservative: Land Status, 2-Year Trend, Last Activity Window, Risk Tier, risk flags, evidence coverage, and assessment confidence. Credit-readiness is product/pitch framing, not automated loan approval and not a reason to rename the current UI/contract fields.
Links: PROJECT §Vision | PROJECT §Positioning | PROJECT §Outputs (what the user sees) | PROJECT §Roadmap | TASK: T-02
Refines: 2026-05-13 — Current build skips crop category and upgrades to interval-based land assessment; 2026-06-16 — Isolate non-committed future ideas in `FUTURE.md`

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
Why: The rasterio cache included start_date/end_date in the fingerprint, so any date-range extension forced a full re-fetch of all prior scenes. The cube migration keeps the cache unit as the solar-day mosaic, keyed on params that change that day's output (geometry/bbox, CRS, resolution, resampling, SCL classes, max_cloud, offset_policy). start_date/end_date select the window, they do not change individual day outputs; absent days are appended to existing cubes, then the local Zarr store is compacted back into physical time order.
Alternatives: Include dates in key (rejected: breaks incremental extension); cache the full pixel cube as Zarr (rejected at the time as overkill — later reversed, see 2026-06-20 "Persist the solar-day cube as `cube.zarr`").
Consequences: Same-window reruns can skip/replay current solar-day downloads. The offset_policy and AOI identity are in the key, so changing processing policy or bbox/geometry invalidates stale source pixels automatically. Incremental date-range extension downloads only missing solar days; the on-disk time axis is sorted after local compaction, and the JSONL ledger remains authoritative about which slots are real.
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

2026-06-24 — Decision: Pipeline correction — fill+smooth preprocessing, hybrid-threshold activity detection
Why: The old gap-aware local-median smoother left usable-only values and did not fill across gaps, so the seasonal detector saw disconnected short segments and missed real vegetation activity windows. The old prominence-to-noise detector exaggerated small noise blips and missed plateau/double-crop behavior. A hybrid threshold (fixed floor + dynamic baseline margin) finds activity windows that match the visible NDVI curve.
Alternatives: Whittaker smoother (rejected: user prefers Savitzky-Golay); fill-then-Whittaker; prominence-only with lower threshold (rejected: still missed plateau windows).
Consequences: Preprocessing now produces `*_filled` columns (linear interpolation across usable anchors then Savitzky-Golay) for every observed timestamp. Seasonal analysis uses all rows (not just usable) and hybrid threshold: confirmed ≥ max(0.35, baseline+0.10), borderline ≥ max(0.20, baseline+0.05). Gap metrics remain separate confidence evidence. `gap_aware_local_median_weighted_mean` is replaced by linear-interpolation-then-Savitzky-Golay as the smoothing method. The pipeline now outputs 4 activity windows and `active` land status for the demo AOI.
Links: PIPELINE §Preprocessing | PIPELINE §Activity-window analysis
Supersedes: 2026-01-25 — Current-build gap handling uses smoothing + light interpolation with assessment-confidence penalty
Refines: 2026-05-18 — Current-build preprocessing does not interpolate or synthesize timestamps
Superseded by: 2026-06-30 — Weighted Whittaker daily-grid analysis curve + timescale lambda + daily-curve detector

2026-06-17 — Decision: Insufficient satellite evidence requires manual review
Why: A completed pipeline run can still lack enough usable evidence for a final automated land assessment. In that case, the product must avoid implying land/farmer failure or issuing unsupported financing-review signals.
Alternatives: Return a provisional automated land status; return no assessment object; treat insufficient evidence as a high-risk land result.
Consequences: API and reports expose `assessment_status: complete | manual_review_required`. Manual-review results keep satellite evidence coverage and low assessment confidence, but do not present final automated `land_status`, `trend_2y`, `season_performance`, `risk_tier`, or land risk flags. Confidence is capped by evidence coverage: no cap for `good`, max `medium` for `fair`, max `low` for `limited`, and `low` for `insufficient`.
Links: PROJECT §Outputs (what the user sees) | ENGINEERING §Assessment artifact boundary | PIPELINE §Evidence coverage interpretation
Refines: 2026-06-17 — Decision: Gap diagnostics describe evidence coverage, not land risk

2026-06-30 — Decision: Weighted Whittaker daily-grid analysis curve + timescale lambda + daily-curve detector
Why: The prior smoother fit a polynomial on the integer observation index (not real time), distorting irregular cloud-gapped Sentinel-2 series and mislabeled as Savitzky-Golay; a second gap-aware smoother was dead code whose parameters were still published. The detector measured peak min-distance in observation-index units (merging two cycles across a temporal gap) and mislabeled open-edge cycles as complete.
Alternatives: keep Savitzky-Golay but make it time-aware (weaker across long gaps); adaptive lambda via GCV (rejected as default — empirically undersmooths daily-gridded NDVI, minimizing at lambda≈1-10); double-logistic/GPR (rejected: segmentation/determinism/explainability costs); HMM as production detector (rejected — kept as research cross-check only).
Consequences: Smoothing is a quality-weighted Whittaker-Eilers smoother on a regular daily grid (`analysis_curve.py`); lambda is derived from a ~45-day phenology timescale (`lambda=(T/2π)^4`≈2631), an agronomic constant rather than a single-AOI fit. A new `season_analysis_curve.csv` artifact is persisted; `ndvi_smoothed.csv` keeps its columns (now the daily curve sampled at observations). The detector runs on the daily curve with real-day peak distance, asymmetric per-limb SOS/EOS thresholds (alpha_start 0.20 / alpha_end 0.35), slope confirmation, sub-peak merging (berseem stays one cycle), and crossing-reachability lifecycle. A deterministic HMM cross-check (`outputs/tools/hmm_phenology.py`, diagnostic only) and a self-contained visualization HTML are produced under `outputs/diagnostics/<aoi>/`. `scipy` is now a base dependency.
Links: PIPELINE §Preprocessing | PIPELINE §Activity-window analysis | T-11 §Done Summary
Supersedes: 2026-06-24 — `gap_aware_local_median_weighted_mean` replaced by linear-interpolation-then-Savitzky-Golay
Refines: 2026-06-29 — T-11 detector decision (deterministic backbone aligned with peak/trough per-cycle amplitude)

2026-06-30 — Decision: Grounded report evidence packet as the correctness layer (T-11 Layer 5)
Why: Reports and assisted summaries must rest on one deterministic, grounded Observed/Interpreted/Confidence/Watch artifact that invents no new evidence. A single evidence packet anchors correctness and lets downstream layers (assistants, lenders, portals) build interpretation on a stable, auditable foundation.
Alternatives: Let each downstream consumer (assistant, API, portal) synthesize its own evidence summary; build evidence layer after the assistant; keep evidence embedded in the assessment object.
Consequences: `farmtrust_core/report/evidence_packet.py` builds `data/assessment/<aoi>/report_evidence_packet.json` during the worker's report_generation phase. The packet is deterministic and byte-reproducible. Structure: Observed (raw data surface) → Interpreted (seasonal/trend inference) → Confidence (per-claim confidence scores) → Watch claims (each with confidence + "rests_on" citation). Additional sections: per-land track record (past assessments), risk register split into land_risk vs evidence_limitation, a fixed "what this does NOT tell you" boundaries block (the only place yield/income/legal/credit/neighbor-comparison terms appear), cautious indicators, and limitations. Per-claim confidence (0–1 confidence score) enables adaptive messaging downstream. No wall-clock or byte-ordering metadata ensures determinism and reproducibility.
Links: PROJECT §Outputs (what the user sees) | ENGINEERING §Assessment artifact boundary | TASK: T-11

2026-06-30 — Decision: Evidence packet exposed via a dedicated endpoint + report-card UI, separate from the PDF export (T-11 Layer 6)
Why: The evidence packet is the lender-facing correctness layer and must be accessible in real time (no export/build step) and independently renderable (not buried in the PDF PDF workflow). A dedicated endpoint and portal view make the packet discoverable and enable interactive evidence review without the latency and file-management overhead of PDF generation.
Alternatives: Embed evidence summary only in the PDF export; return evidence in the land assessment response; expose evidence via webhook to async PDF builder only.
Consequences: API GET `/lands/{id}/evidence-packet` returns `EvidencePacketResponse` (api/schemas.py); the portal renders it as a lender Report Card at route `/lands/[id]/packet` (portal/src/components/report/EvidencePacketReport.tsx), linked from the Land Summary action bar. The packet is separate from the PDF export at `/lands/[id]/report`. Endpoint returns 404 until the evidence packet is generated during the report_generation phase (after risk_modeling). The UI is stateless and reads directly from the EvidencePacketResponse JSON, enabling rapid iteration on evidence rendering without regenerating the packet.
Links: PROJECT §Outputs (what the user sees) | ENGINEERING §Assessment artifact boundary | TASK: T-11

2026-06-30 — Decision: Bounded report assistant — deterministic-first, packet-grounded, with Azure gpt-4o layered on top (T-11 Layer 7 / T-04)
Why: The report needs plain-language narration and a "free to ask, bounded in what it may assert" analyst chat for lenders, without ever becoming a dependency of the core risk report or a source of crop/yield/pest/loan claims. Grounding strictly in the evidence packet, with the deterministic brief as the always-on path, keeps the assistant honest and the report stable when the LLM is absent or wrong.
Alternatives: LLM-first narration (rejected — makes AI load-bearing); a chatbot over arbitrary documents (rejected — out of evidence scope); the OpenAI SDK or Anthropic directly (rejected — reuse the user's working Azure config); forcing structured output on free chat (rejected — exhausts the model; chat is free-form, narration is structured); an output forbidden-phrase guardrail scan (tried, then removed — see revision below).
Consequences: `farmtrust_core/report/brief.py` is the no-LLM narration and the fallback; `api/assistant/` adds config/prompt/llm/service with `langchain-openai`'s `AzureChatOpenAI` isolated in `llm.py` (lazy-imported, gated off when `AZURE_API_KEY` is absent — key in gitignored `.env`, never logged). `POST /lands/{id}/assistant/{narrate,chat}`; hybrid output (structured narration via `with_structured_output`, free-form chat). Each call persists an `AssistantMessage` audit row (packet hash, model, prompt version). Grounding is enforced entirely by the system prompt. Packet provenance enriched to `v1.1` (`claim_type`, `provenance_level`, `source`, `method`, `allowed_use`, `restriction`) for honest claim typing — these live in the structured fields ONLY, never inline in the text. Portal: a "Report / Ask the assistant" tab on `/lands/[id]/packet`; chat answers render as Markdown (`react-markdown`) and reply in the user's language (Arabic/English). Deferred to pre-production: the heavy code-enforced per-line validator and response streaming.
Revised 2026-06-30 (post user testing): the light output guardrail scan was REMOVED. It was Latin-only (blind to Arabic crop names) and risked blocking a *correct* refusal that quotes a crop name (e.g. "crop identity cannot be determined, such as corn or wheat"), forcing a needless deterministic fallback. The grounded prompt already produces those refusals, so it is the sole control; `guardrails.py` and its tests were deleted. The heavy per-line validator remains a documented pre-production consideration. Also dropped: the inline `[claim_type]` tags the model was emitting in prose (typing now lives only in the structured fields/pills).
Revised 2026-07-01 (expert mode + knowledge file): the assistant was too timid (refused even when the user supplied ground-truth crop labels) and lacked agronomy expertise. Three changes: (1) the prompt now includes the per-cycle **activity-record timeline** and **regional agronomy knowledge**, and treats crops the **user declares** as ground truth — mapping them onto observed cycles and reasoning about rotation/consistency — while never asserting a crop from satellite alone and keeping yield/income/loan hard-excluded; (2) that local expertise lives in a dedicated, **runtime-loaded** `api/assistant/knowledge.md` (curated/generalized from `docs/documentations/05-local-interpretation-context.md`; edit-and-go, no restart, `05` stays the human research log); (3) mixed Arabic/English renders per-paragraph (`unicode-bidi: plaintext` + `dir="auto"`) so embedded Latin runs no longer scramble. `PROMPT_VERSION` → `assistant-prompt-v2-2026-07-01`.
Links: PIPELINE §Report evidence packet (Surfaces) | TASK: T-04 | TASK: T-11 Layer 7 | api/assistant/knowledge.md
