# PIPELINE

This document is the detailed implementation reference and runbook for the current FarmTrust build
pipeline. It describes the live end-to-end path from AOI input to ingestion, preprocessing, seasonal
analysis, and the final assessment output.

## Purpose

The current build is designed to produce an explainable, file-based land assessment for one AOI over a
selected interval, with enough evidence to support API and portal consumption.

The current-build output focuses on:

- smoothed vegetation and moisture signals
- vegetation activity-window count over the interval
- interval-based land status
- trend when enough activity-window history exists
- history/evidence coverage and absence-gate status
- latest activity-window performance
- conservative risk flags
- satellite evidence coverage
- assessment confidence and supporting evidence
- explicit gap diagnostics
- cautious numeric indicators: p95/spread, EVI, NDMI, and MNDWI evidence signals
- boundary provenance for model-derived activity-window dates

The current build does **not** currently output crop category.

## Boundaries and handoffs

Current pipeline boundaries:

- current product input is user-drawn polygon AOI geometry from the portal
- current local/demo CLI fixtures can still use bbox/config input for repeatable pipeline validation
- current stage handoffs are file-based so each stage can be tested independently
- FastAPI runs or triggers the pipeline, reads the generated assessment artifact, maps it into API DTOs, and sends shaped responses to the portal
- the frontend should not depend on raw runtime artifact paths or filenames

Current runtime artifacts are useful for local validation and backend handoff, but generated data files do not need to be committed for the implementation to be considered present.

## Canonical pipeline stages

### 1. Ingestion

Entrypoint:

```powershell
uv run ingest-aoi --config scripts/ingest_demo.json
```

Primary responsibilities (two phases, see `farmtrust_core/ingest/cube_pipeline.py`):

- **Phase 1 — `download_cubes`:** search Sentinel-2 L2A through STAC (Planetary Computer), filter by `eo:cloud_cover`, group items by solar day, and load each day as an AOI-clipped mosaic across all overlapping tiles via `odc.stac.load`. Fresh runs pre-allocate a time-sorted `cube.zarr`; reruns skip current days, append only missing date-range observations, backfill missing requested bands, then compact the local Zarr store back into physical time order. Repairing/deleting `B11` or adding `B05` does not re-download existing bands.
- **Phase 2 — `process_cubes`:** open `cube.zarr`, read 10m root bands plus native 20m grouped bands as needed, apply the AOI polygon mask + SCL validity classes, apply the BOA offset `(DN-1000)/10000`, compute per-day index statistics and `valid_fraction`, and emit `indices_timeseries.csv`. Derived stats are not written back into the source cube.
- Separating the phases means a policy change (offset, SCL classes, a new index) reprocesses via Phase 2 only; adding or repairing a source band backfills only that band.

Main code:

- `scripts/ingest_aoi.py` (CLI)
- `farmtrust_core/ingest/runner.py` (loader-agnostic seam: `run_ingestion`, `IngestCancelled`)
- `farmtrust_core/ingest/cube_pipeline.py` (two-phase orchestrator)
- `farmtrust_core/ingest/cube_loader.py` (`odc.stac.load` wrapper, per-band resampling, raw DN)
- `farmtrust_core/ingest/cube_stats.py` (BOA offset, AOI mask, per-day stats — pure, no I/O)
- `farmtrust_core/ingest/config.py`
- `farmtrust_core/ingest/utils.py`

Main outputs:

- `data/<aoi_id>/cube.zarr` — **primary source artifact**: raw-DN pixels, per-day provenance, and config. Root stores the 10m grid (`B02 B03 B04 B08`) plus time/provenance; the `20m` group stores native 20m source bands (`B05 B06 B07 B8A B11 B12 SCL`) when requested.
- `data/<aoi_id>/indices_timeseries.csv` — derived per-solar-day export (downstream handoff)
- `data/<aoi_id>/run_metadata.json` — run config (downstream contract; Phase 2 reads config here)
- `data/<aoi_id>/scenes_index.jsonl` — operational write-ahead ledger (v4+): one line per attempted solar day with `cache_key`, day `status`, and per-band `band_status` when backfill is used

AOI and window notes:

- intended assessment window is selected/configured per run; legacy/default examples may still use a 24-month lookback
- demo and smoke-test runs may use shorter configured windows to validate code paths quickly
- metadata includes `window` and `lookback_months`
- one row is emitted per solar-day mosaic
- STAC search currently uses the AOI bbox
- `odc.stac.load` clips to the AOI bbox and aligns to centroid-estimated UTM, reading only the needed COG windows over HTTP; 10m bands are stored on the root grid and 20m bands are stored in the native `20m` group
- when polygon geometry is provided, the pipeline applies a polygon mask on the loaded cube grid
- index statistics and `valid_fraction` are computed only over pixels inside the polygon mask
- for bbox-only CLI fixtures, the whole bbox window is treated as the AOI

`valid_fraction` meaning:

- polygon AOI: usable pixels inside polygon / all pixels inside polygon
- bbox-only AOI: usable pixels inside bbox window / all pixels inside bbox window
- usable pixels are pixels not excluded by the current scene classification mask

Satellite access notes:

- Sentinel-2 L2A is the current implemented source
- STAC access uses Planetary Computer and supports endpoint fallback
- Planetary Computer signing is handled softly where needed
- broader satellite source strategy is unresolved and tracked in `OPEN_ITEMS.md`, including when and why to use Sentinel-2, Landsat, or other possible sources

Current index output includes per-solar-day mean and p95 values for:

- NDVI
- EVI
- NDMI
- NDWI
- MNDWI

Required downstream columns include:

- `timestamp`
- `item_id`
- `valid_fraction`
- `ndvi_mean`, `ndvi_p95`
- `evi_mean`, `evi_p95`
- `ndmi_mean`, `ndmi_p95`
- `ndwi_mean`, `ndwi_p95`
- `mndwi_mean`, `mndwi_p95`

Observation cadence is irregular and keyed by solar-day mosaics. Fixed-interval views belong downstream in preprocessing or analysis. Missing values remain null/NaN so downstream stages can reason explicitly about observation count and gaps.

Local reuse behavior:

- the active pipeline still queries STAC on each run
- local reuse is solar-day based through `scenes_index.jsonl` (v4+ JSONL; one operational line per solar day, with per-band status when backfill is used)
- the ledger stores `cache_key` + `status` and can store `band_status`; provenance (`item_ids`, `mgrs_tiles`, `min_cloud_cover`) lives in `cube.zarr`, while derived stats live in `indices_timeseries.csv`
- the ledger — not the cube's time axis — is authoritative about which days are real, so failed/partial (zero-filled) slots are never processed
- Phase 1 skips day downloads when the stored `cache_key` matches, status is `downloaded`/legacy `ok`, and all requested bands exist; missing dates trigger day-level backfill, missing bands trigger band-only backfill, and the cube is physically sorted after local compaction. Phase 2 recomputes derived stats from cube pixels and rewrites `indices_timeseries.csv`
- ingestion artifact validation fails loudly when root/`20m` time axes diverge, when the cube time axis is unsorted, or when `indices_timeseries.csv` does not match confirmed ledger days; preprocessing runs the same guard before consuming the CSV
- there is no active STAC query-result TTL/env-var cache

### 2. Preprocessing

Entrypoint:

```powershell
python scripts/preprocess_timeseries.py --aoi-id <aoi_id>
```

Primary responsibilities:

- collapse same-day duplicates
- filter usable observations with `valid_fraction >= 0.90`
- smooth core vegetation and moisture signals
- compute continuity metrics and gap diagnostics
- interpret satellite evidence coverage separately from land condition

Main code:

- `scripts/preprocess_timeseries.py`
- `farmtrust_core/preprocess/pipeline.py`
- `farmtrust_core/preprocess/gaps.py`
- `farmtrust_core/preprocess/smoothing.py`

Input contract:

- input directory: `data/<aoi_id>/`
- required files: `indices_timeseries.csv`, `run_metadata.json`
- required CSV columns: `item_id`, `timestamp`, `valid_fraction`, `ndvi_mean`, `ndvi_p95`, `evi_mean`, `evi_p95`, `ndmi_mean`, `ndmi_p95`, `ndwi_mean`, `ndwi_p95`, `mndwi_mean`, `mndwi_p95`

Processing behavior:

- timestamps are parsed and normalized to UTC
- observations are sorted before merge/filter operations
- duplicate observations are grouped by UTC calendar day
- same-day duplicates are merged using valid-fraction-weighted averaging
- negative weights are clamped to `0`; when total weight is `0`, a simple arithmetic mean is used
- usable observations require `valid_fraction >= 0.90`
- non-usable rows remain in the output for review and now also receive filled+smoothed analysis values
- smoothing builds a model-derived analysis curve for NDVI, EVI, NDMI, NDWI, and MNDWI in two phases (`farmtrust_core/preprocess/analysis_curve.py`):
  - **Phase 1 — fill:** `fill_at_observations()` performs linear interpolation across inclusion-gated anchors (observations with `valid_fraction >= 0.30`), producing `*_filled` values for every observed timestamp.
  - **Phase 2 — smooth:** `build_analysis_curves()` solves a quality-weighted **Whittaker–Eilers** smoother on a regular **daily grid** (`(W + lambda * DᵀD) z = W y`, 2nd-order difference penalty, banded SPD solve), then samples that daily curve back to the observation timestamps to produce `*_smoothed`. `lambda` is derived from a ~45-day phenology smoothing timescale (`lambda = (T / 2*pi)^4 ≈ 2631`) — an agronomic constant, not a per-AOI fit.
- a synthetic **daily** grid is created for the analysis curve only; `ndvi_smoothed.csv` still carries exactly one row per observed timestamp
- the strict `valid_fraction >= 0.90` usable gate is unchanged and still drives gap/evidence metrics; the analysis curve uses a looser `>= 0.30` inclusion gate with `valid_fraction` weights
- the smoothing method name is `weighted_whittaker_eilers_daily_grid`
- `interpolation_policy` is `linear_fill_between_inclusion_gated_anchors_then_whittaker`
- the daily curve is also persisted as `season_analysis_curve.csv`; filled/smoothed values form a model-derived analysis curve, not direct observation evidence

Current smoothed signals:

- `ndvi_smoothed`
- `evi_smoothed`
- `ndmi_smoothed`
- `ndwi_smoothed`
- `mndwi_smoothed`

Main outputs:

- `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
- `data/preprocess/<aoi_id>/quality_metrics.json`
- `data/preprocess/<aoi_id>/season_analysis_curve.csv` — daily-grid Whittaker analysis curve (`date`, `day_offset`, `is_observed_day`, `analysis_weight`, `*_curve`); consumed by the detector and the diagnostics

`ndvi_smoothed.csv` fields:

- `timestamp`
- `ndvi_raw`
- `ndvi_p95_raw`
- `ndvi_spread_raw`
- `ndvi_filled` — linear interpolation from inclusion-gated anchors (all rows have this)
- `ndvi_smoothed` — daily Whittaker–Eilers analysis curve sampled at this timestamp (all rows have this)
- `evi_raw`
- `evi_p95_raw`
- `evi_filled`
- `evi_smoothed`
- `ndmi_raw`
- `ndmi_p95_raw`
- `ndmi_filled`
- `ndmi_smoothed`
- `ndwi_raw`
- `ndwi_p95_raw`
- `ndwi_filled`
- `ndwi_smoothed`
- `mndwi_raw`
- `mndwi_p95_raw`
- `mndwi_spread_raw`
- `mndwi_filled`
- `mndwi_smoothed`
- `valid_fraction`
- `is_usable` — evidence flag; all rows now have filled+smoothed values regardless
- `source_row_count`

Important quality fields:

- `aoi_id`
- `total_observation_count`
- `merged_observation_count`
- `usable_observation_count`
- `dropped_observation_count`
- `gap_ratio`
- `max_gap_days`
- `median_gap_days`
- `smoothing_method`
- `interpolation_policy`
- `fill_policy`
- `creates_synthetic_timestamps`
- `smooths_only_usable_observations`
- `analysis_curve_source`
- `analysis_curve_direct_evidence`
- `usable_valid_fraction_threshold`
- `whittaker_difference_order`
- `lambda_selection_method`
- `target_smoothing_days`
- `selected_lambda`
- `lambda_selection_reason`
- `analysis_inclusion_valid_fraction`
- `weighting_policy`
- `gap_risk`
- `confidence_penalty`
- `gap_risk_reason`
- `confidence_inputs`
- `long_gap_count`
- `long_gap_windows`

`long_gap_windows` records explicit high-caution continuity windows using the current preprocessing
threshold logic. This is intentionally visible output, not hidden internal state.

`gap_ratio` is the sum of gap days beyond expected cadence divided by the usable-series span, bounded to `[0, 1]`.

Evidence coverage interpretation:

- Raw gap metrics describe satellite observation quality, not land or farmer quality.
- Internal fields such as `gap_risk`, `confidence_penalty`, and `gap_risk_reason` are pipeline interpretation helpers; they should not be shown as land risk flags.
- User-facing wording should use `satellite_evidence_coverage`, `evidence limitations`, and `assessment confidence`.
- Assessment confidence means confidence in FarmTrust's conclusion, given satellite coverage, observation continuity, activity-window clarity, and signal strength. It does not mean confidence in the land itself.
- Cloud gaps or weak coverage can lower assessment confidence, but they should not by themselves create a land risk flag such as abandonment, salinity, waterlogging, or encroachment.

Interpretation layers:

- Raw metrics: `valid_fraction`, `total_observation_count`, `usable_observation_count`, `dropped_observation_count`, `max_gap_days`, `median_gap_days`, `gap_ratio`, `long_gap_count`, `long_gap_windows`.
- Internal continuity classification: `gap_risk`, `confidence_penalty`, and `gap_risk_reason` describe how observation gaps affect evidence reliability.
- User-facing interpretation: `satellite_evidence_coverage` should be communicated as `good`, `fair`, `limited`, or `insufficient`.
- Assessment reliability: assessment confidence should be communicated as `high`, `medium`, or `low`, with a short reason tied to evidence coverage, activity-window clarity, and signal strength.

Current interpretation policy:

- `good` coverage: enough usable observations and no important long gaps; proceed normally.
- `fair` coverage: some gaps exist but they do not dominate the assessment window; proceed with normal labels and clear evidence notes.
- `limited` coverage: important gaps exist; proceed only with caution wording and lower assessment confidence.
- `insufficient` coverage: usable observations are too sparse or gaps dominate critical periods; assessment should be incomplete, retried with a different window/source, or sent to manual review.

Threshold note:

- The current code classifies continuity with `gap_risk` thresholds below.
- Final thresholds for user-facing `satellite_evidence_coverage` and the `insufficient` branch still need product/validation review before they become portal/report contract fields.

Operational notes:

- downstream activity-window analysis uses populated smoothed analysis-curve values across observed timestamps; `is_usable` remains an evidence/support flag for confidence and gap interpretation
- changes to `valid_fraction_threshold`, smoothing method, or expected cadence can shift activity-window boundaries and should be re-reviewed visually
- daily duplicate handling matters because overlapping tiles and scene variants can produce repeated observation days

### 3. Activity-window analysis

Entrypoint:

```powershell
python scripts/seasonal_analysis.py --aoi-id <aoi_id>
```

Primary responsibilities:

- detect vegetation activity windows from model-derived smoothed NDVI analysis values at observed timestamps
- estimate crossing/start/peak/end dates for the detected activity window and expose boundary provenance/support
- label activity windows as `good`, `interrupted`, or `weak`
- confirm activity windows using EVI/NDMI/NDWI support signals
- record whether each activity window overlaps long observation gaps

Main code:

- `scripts/seasonal_analysis.py`
- `farmtrust_core/seasonal/seasons.py`

Input contract:

- input directory: `data/preprocess/<aoi_id>/`
- required files: `ndvi_smoothed.csv`, `quality_metrics.json`
- required CSV columns: `timestamp`, `ndvi_smoothed`, `evi_smoothed`, `ndmi_smoothed`, `ndwi_smoothed`, `is_usable`, `valid_fraction`, `source_row_count`
- required quality keys: `aoi_id`, `usable_observation_count`, `gap_ratio`, `max_gap_days`, `gap_risk`

Detector behavior:

- detection uses the smoothed/model-derived NDVI analysis curve as the activity-shape signal
- output field names remain season-oriented for compatibility, but `season` means detected vegetation activity window, not an agronomic crop season
- detector model is `deterministic_peak_trough_relative_amplitude_phenology`
- detection runs on the dense **daily** Whittaker analysis curve (rebuilt from the smoothed observations, or read from `season_analysis_curve.csv`); strict usable observations remain the evidence/support layer for gap analysis and confidence — model-derived values are not direct evidence
- peaks and troughs are found with `scipy.signal.find_peaks` on the daily curve, with minimum peak separation enforced in **real days** (not observation count)
- each cycle uses **per-limb** baselines and **asymmetric** amplitude thresholds: start-of-season at `baseline_left + ALPHA_START * (peak - baseline_left)` (`ALPHA_START = 0.20`, rising limb) and end-of-season at `baseline_right + ALPHA_END * (peak - baseline_right)` (`ALPHA_END = 0.35`, falling limb — senescence/harvest reads at a higher fraction)
- a **slope-confirmation** gate requires the daily slope to be sustained for `SLOPE_CONFIRM_STEPS = 3` steps before accepting a crossing (rejects rain-flush false starts)
- **sub-peak merging:** a trough splits two peaks into separate cycles only if it descends past `CYCLE_SPLIT_AMPLITUDE_FRACTION = 0.50` of the lower neighbouring amplitude; otherwise the sub-peaks merge into one cycle (a berseem multi-cut sawtooth stays a single cycle)
- `detection_status` (confirmed/borderline) compares cycle amplitude to a single robust noise estimate plus an absolute floor; a window needs at least `4` observations and at least `20` days of observed duration
- peak date is the daily-curve maximum inside the retained window; `season_id` is sequenced across the combined confirmed+borderline list
- lifecycle status is by **crossing-reachability**: `complete`, `open_right` (falling crossing not reached before the series end), `open_left` (rising crossing not reached before the series start), or `open_both`
- `is_open` is right-edge-only (`open_right`/`open_both`); `open_left` is surfaced via `lifecycle_status` + `provisional = true` + `start_boundary_certainty = "open"`
- `activity_detection_model` records `input_signal=model_derived_analysis_curve_at_observed_timestamps`, `boundary_method=peak_trough_per_cycle_amplitude_fraction`, `alpha_start`, `alpha_end`, `slope_confirm_steps`, `cycle_split_amplitude_fraction`, and `gap_confidence_source=real_usable_observation_timestamps`

Quality labels:

- `good` means a complete window has peak NDVI `>= 0.50` and confirmation `strong`
- `interrupted` describes a large one-step NDVI drop relative to the window amplitude
- `weak` describes confirmed activity with weaker or provisional signal shape
- EVI/NDMI/NDWI confirmation is relative to each signal's own window behavior; it does not use fixed EVI/NDMI/NDWI cutoffs and does not by itself rewrite the NDVI shape label

Maximum drop is the largest one-step decrease between consecutive smoothed observations inside the activity window.

Main output:

- `data/seasonal/<aoi_id>/season_windows.json`

Top-level fields:

- `aoi_id`
- `season_count`
- `complete_window_count`
- `open_window_count`
- `borderline_window_count`
- `activity_detection_model`
- `seasons`
- `borderline_windows`

Important season fields:

- `season_id`
- `start_date`
- `peak_date`
- `end_date`
- `is_open`
- `peak_ndvi`
- `duration_days`
- `quality_label`
- `confirmation_level`
- `gap_overlap_count`
- `gap_overlap_risk`
- `gap_overlap_stage`
- `evidence_summary`
- `lifecycle_status`
- `detection_status`
- `season_calendar_label` — broad `summer`/`winter`/`transition` calendar descriptor from the peak month (not a crop label)
- `greenup_rate` — mean rising-limb slope of the daily curve
- `senescence_rate` — mean falling-limb slope of the daily curve
- `integrated_ndvi` — area under the daily curve above baseline over the cycle (model-derived; distinct from scoring's observation-based `auc_ndvi`)
- `cycle_split_merged` — true when sub-peaks were merged into this cycle
- `daily_curve_lambda` — the Whittaker lambda used for the analysis curve
- `prominence_ndvi`
- `noise_floor_ndvi`
- `prominence_to_noise_ratio`
- `season_confidence_note`
- `window_type`
- `provisional`
- `baseline_ndvi`
- `amplitude_ndvi`
- `boundary_threshold_ndvi`
- `usable_observation_count`
- `start_boundary_certainty`
- `peak_certainty`
- `end_boundary_certainty`
- `internal_gap_count`
- `start_boundary_source`
- `peak_source`
- `end_boundary_source`
- `start_nearest_real_observation_date`
- `peak_nearest_real_observation_date`
- `end_nearest_real_observation_date`
- `start_nearest_real_observation_days`
- `peak_nearest_real_observation_days`
- `end_nearest_real_observation_days`

Top-level terminology field:

- `terminology.season`: `detected vegetation activity window, not an agronomic crop season`

Activity-window boundaries should be reviewed with clear separation between adjacent windows rather than duplicated start/end boundary markers.

Gap context:

- observation gap classification does not directly create land or farming risk flags
- activity-window outputs record whether detected windows overlap long observation gaps
- onset zone is the first third of the observed window
- peak zone is `peak_date ± max(6 days, duration_days / 6)`
- tail zone is the last third of the observed window
- long gaps near onset/tail make boundary certainty limited and set `provisional = true`
- long gaps near peak set `peak_certainty = "limited"`
- internal long gaps increment `internal_gap_count`
- interpretation should become more cautious when satellite evidence coverage is limited or when long gaps overlap important activity-window stages

### 4. Land assessment

Entrypoint:

```powershell
python scripts/land_assessment.py --aoi-id <aoi_id>
```

Primary responsibilities:

- aggregate preprocessing and activity-window evidence
- classify interval-level `land_status`
- classify interval-level `trend_2y`
- determine latest activity-window performance in the compatibility field `latest_season_performance`
- emit conservative `risk_flags`
- compute assessment confidence, meaning confidence in the assessment reliability

Main code:

- `scripts/land_assessment.py`
- `farmtrust_core/scoring/rules.py`
- `farmtrust_core/scoring/evidence.py`

Input files:

- `data/<aoi_id>/run_metadata.json`
- `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
- `data/preprocess/<aoi_id>/quality_metrics.json`
- `data/seasonal/<aoi_id>/season_windows.json`

Main outputs:

- `data/assessment/<aoi_id>/land_assessment.json`
- `data/assessment/<aoi_id>/report_evidence_packet.json` — built during the worker's `report_generation` phase; see section 5 for full details

Backend handoff:

- `land_assessment.json` is an internal pipeline artifact.
- FastAPI runs or triggers the pipeline, reads this artifact, maps it into API response DTOs, and sends those shaped responses to the portal.
- The frontend should not depend on the raw file path or file name.

Top-level fields:

- `aoi_id`
- `interval`
- `land_status`
- `trend_2y`
- `history_coverage`
- `absence_assessment`
- `season_count`
- `latest_season_performance`
- `risk_flags`
- `satellite_evidence_coverage`
- `confidence`
- `evidence`
- `metrics_summary`

Assessment policy notes:

- `land_status` is inferred from observed interval-level vegetation activity and evidence/absence gates, not from one latest point
- one good observed activity cycle can support current `active` status, but history remains `limited_history` until enough cycles exist
- `absence_assessment` distinguishes `activity_present`, `absence_supported`, `absence_uncertain`, `not_assessed`, and `insufficient_evidence`
- no activity/inactivity/idle/abandonment wording is issued unless the absence gate passes
- `trend_2y` is derived from activity-window strength summaries such as peak NDVI and window AUC, but remains `uncertain` when there are fewer than two usable activity windows
- `latest_season_performance` uses the latest closed activity window when available; otherwise it uses the latest open activity window and marks it provisional
- risk flags stay conservative and should prefer `uncertain` or lower assessment confidence when continuity or activity-window clarity is weak
- assessment confidence surfaces component levels for satellite evidence coverage, activity-window clarity, and signal strength in addition to the final level
- satellite evidence limitations should be documented as evidence limitations, not as land/farmer problems
- crop category is skipped in the current build

Important assessment diagnostics:

- `metrics_summary.long_gap_count`
- `metrics_summary.long_gap_windows`
- `metrics_summary.season_strength[].gap_overlap_count`
- `metrics_summary.season_strength[].gap_overlap_risk`
- `metrics_summary.interval_max_ndvi_p95`
- `metrics_summary.interval_median_ndvi_spread`
- `metrics_summary.interval_median_mndwi`
- `metrics_summary.season_strength[].peak_ndvi_p95`
- `metrics_summary.season_strength[].median_ndvi_spread`
- `metrics_summary.season_strength[].median_mndwi`

### 5. Report evidence packet

A grounded aggregation layer that the polished report surface and the bounded report assistant consume. It does not compute new evidence: it is a deterministic projection over the already-written assessment, season, and quality artifacts. The shipped assistant (T-04 / Layer 7) reads this packet's per-claim provenance to keep its narration grounded; see docs/TASKS/T-04-ai-report-assistant.md.

Main code:

- `farmtrust_core/report/evidence_packet.py` (`build_report_evidence_packet`, `write_report_evidence_packet`)

Input files:

- `data/assessment/<aoi_id>/land_assessment.json`
- `data/seasonal/<aoi_id>/season_windows.json`
- `data/preprocess/<aoi_id>/quality_metrics.json`
- `data/<aoi_id>/run_metadata.json`

Main output:

- `data/assessment/<aoi_id>/report_evidence_packet.json`

Built during the worker's `report_generation` phase, after the land assessment is written. A packet failure is non-fatal: the assessment is already saved.

Top-level fields:

- `packet_version`, `schema`, `aoi_id`, `assessment_status`, `source_artifacts`, `interval`
- `headline` — cautious `state_label`, `cropping_intensity` (provisional), `overall_confidence`, plain-language `summary`
- `claims` — typed list organised as `Observed -> Interpreted -> Confidence -> Watch`; each claim carries `layer`, `confidence`, `rests_on`, and per-claim provenance (`claim_type`, `provenance_level`, `source`, `method`, `allowed_use`, `restriction`)
- `layers` — projection mapping each layer to its claim ids
- `activity_record` — per-cycle dates, calendar label, lifecycle status, peak NDVI
- `track_record` — seasons observed toward a certifiable trend (provisional framing)
- `risk_register` — split into `land_risk` and `evidence_limitation` items
- `limitations`, `boundaries` (fixed "what this does NOT tell you" exclusions)
- `indicators` (cautious pass-through), `local_context`

Packet policy notes:

- per-claim provenance is attached by a deterministic post-pass (`_apply_provenance`, packet `v1.1`): `claim_type`, `provenance_level` (0–4), `source`, `method`, `allowed_use`, `restriction` — additive, so the Layer 6 card is unaffected and the assistant (T-04) consumes them
- cautious vocabulary only: one good cycle is `Active — limited history`, never single/double-cropped, stable, or trending
- no crop identity; `season_calendar_label` is a summer/winter calendar descriptor only
- yield, income, price, pest, and legal terms appear only inside the fixed `boundaries` exclusions
- no monitoring or neighbour-baseline sections
- no wall-clock timestamp, so the artifact is byte-deterministic for the same inputs

Surfaces:

- API: `GET /lands/{land_id}/evidence-packet` returns the packet as the `EvidencePacketResponse` DTO (`api/schemas.py`); 404 until it is generated.
- Portal: rendered as a lender-facing report card at `/lands/{id}/packet` (`portal/src/components/report/`), separate from the PDF export.
- Assistant (T-04 / Layer 7): `POST /lands/{land_id}/assistant/{narrate,chat}` narrate/answer over this packet, deterministic-first with Azure `gpt-4o` layered on top (`api/assistant/`); rendered on the "Ask the assistant" tab of the same report-card page.

## Current decision rules

### Observation continuity classification

`gap_risk` is the current internal field name for observation continuity classification. It describes satellite evidence reliability, not land risk.

Current preprocessing cadence assumption:

- `EXPECTED_CADENCE_DAYS = 5.0`

Current classification logic:

- `high` if `max_gap_days > 15` or `gap_ratio > 0.30`
- `moderate` if `max_gap_days > 10` or `gap_ratio > 0.15`
- `low` otherwise

Important note:

- the system does **not** blindly fill long gaps in the current build
- instead, it exposes them explicitly and lowers assessment confidence conservatively
- user-facing surfaces should not label this as `gap risk`; they should explain satellite evidence coverage and assessment reliability

### Land status

Current behavior:

- uses interval-level vegetation activity-window behavior, active-observation fraction, history coverage, and absence-gate status
- does **not** decide status from the latest point alone
- one good recent observed activity cycle can be `active` with `limited_history`
- no detected activity becomes `inactive` only when the absence gate supports a cautious absence/inactivity claim

Current labels:

- `active`
- `intermittent`
- `inactive`

Related coverage fields:

- `history_coverage.status`: `sufficient_history`, `limited_history`, or `insufficient_history`
- `absence_assessment.status`: `activity_present`, `absence_supported`, `absence_uncertain`, `not_assessed`, or `insufficient_evidence`

### Trend

Current behavior:

- compares activity-window strength across the interval
- currently uses peak NDVI and activity-window AUC as conservative strength summaries

Current labels:

- `improving`
- `stable`
- `declining`
- `uncertain`

### Latest activity-window performance

Current behavior:

- uses the latest closed activity window if available
- otherwise uses the latest open activity window and marks it provisional

Current labels:

- `good`
- `interrupted`
- `weak`

## Recommended execution order

For a clean AOI rerun:

```powershell
uv sync --extra data
```

```powershell
uv run ingest-aoi --config scripts/ingest_demo.json
python scripts/preprocess_timeseries.py --aoi-id aoi_demo_01
python scripts/seasonal_analysis.py --aoi-id aoi_demo_01
python scripts/land_assessment.py --aoi-id aoi_demo_01
```

## What was intentionally removed

The repo previously contained older exploratory artifacts around ingestion path exploration, satellite fallback exploration, and ad hoc diagnostics. Those were useful during early experimentation, but they are not part of the current canonical build path.

The current-build surface should stay focused on:

- one ingestion entrypoint
- one preprocessing entrypoint
- one activity-window entrypoint
- one assessment entrypoint

## Current limitations

- gap-risk thresholds are still static
- preprocessing smooths model-derived analysis values over a synthetic regular daily grid, then samples back to observed timestamps; the daily grid is model-derived, not direct observation evidence
- land status is rule-based, not region-calibrated
- crop category is deferred
- activity-window detection remains NDVI-primary
- NDRE/MSAVI, neighbour baselines, monitoring alerts, weather integration, and full pixel maps are deferred
- CLI fixture input and portal/API polygon input both need validation when contracts change

These are acceptable for the current build as long as confidence and evidence remain explicit.
