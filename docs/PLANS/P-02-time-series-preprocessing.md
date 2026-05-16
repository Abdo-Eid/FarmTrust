# P-02 - Time-series preprocessing baseline

This plan defines the minimal, testable preprocessing slice for Phase A. It turns ingestion output into a cleaned NDVI series plus quality metrics that seasonal and scoring roles can consume without depending on ingestion internals.

## Links

- PROJECT: <PROJECT Section MVP scope>
- ENGINEERING: <ENGINEERING Section Pipeline>
- PLAN: <P-01 - Starter pipeline for three roles>

## Ownership & boundaries

**Owner:** ML/time-series preprocessing

## Overview of my task

Deliver a file-based preprocessing contract that consumes the ingestion CSV, collapses duplicate observation days, filters weak observations, smooths the most valuable metrics, and computes confidence inputs for downstream seasonal and scoring work.

## Current status

Implementation baseline is in place and has been run for `aoi_demo_01`.

- Plan file created: `docs/PLANS/P-02-time-series-preprocessing.md`
- Core preprocessing code created:
    - `farmtrust_core/preprocess/pipeline.py`
    - `farmtrust_core/preprocess/gaps.py`
    - `farmtrust_core/preprocess/smoothing.py`
    - `farmtrust_core/preprocess/__init__.py`
- CLI entrypoint created:
    - `scripts/preprocess_timeseries.py`
- Demo outputs generated:
    - `data/preprocess/aoi_demo_01/ndvi_smoothed.csv`
    - `data/preprocess/aoi_demo_01/quality_metrics.json`
- Notebook created for review:
    - `notebooks/01-preprocessing_ndvi.ipynb`

Current demo result:
- Raw ingestion rows: `98`
- Merged daily rows: `43`
- Usable rows after filter: `40`
- Dropped rows after filter: `3`

### In scope

- Read `data/<aoi_id>/indices_timeseries.csv` and `run_metadata.json`.
- Collapse same-day duplicate observations with valid-fraction-weighted averaging.
- Filter usable observations with a conservative `valid_fraction >= 0.90` rule.
- Smooth NDVI/EVI/NDMI/NDWI with a deterministic baseline method.
- Write preprocessing outputs for downstream handoff.
- Provide a notebook view of raw vs merged vs smoothed NDVI.

### Out of scope (explicit non-goals)

- Multi-index preprocessing beyond NDVI in v1.
- Interpolation that fabricates new timestamps.
- Public API/schema changes in `contracts/schemas/`.
- Seasonal window detection or scoring logic.

## Outcomes (what "done" looks like)

1. Preprocessing produces smoothed NDVI/EVI/NDMI/NDWI series for one AOI from ingestion outputs.
2. Quality metrics expose usable observation count, gap ratio, and max gap days.
3. A notebook clearly shows before/after preprocessing behavior for one AOI.

## Role details

- **Inputs**
    - `data/<aoi_id>/indices_timeseries.csv`
    - `data/<aoi_id>/run_metadata.json`
- **Responsibilities**
    - Validate the ingestion contract.
    - Merge same-day duplicates into one effective observation day.
    - Compute usability flags and smoothing inputs.
    - Produce gap/confidence metrics for downstream roles.
- **Code location**
    - `farmtrust_core/preprocess/` for reusable logic
- `scripts/preprocess_timeseries.py` for the local entrypoint
- **Outputs**
    - `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
    - `data/preprocess/<aoi_id>/quality_metrics.json`
    - `notebooks/01-preprocessing_ndvi.ipynb`
- **Fast test**
    - Run preprocessing on `aoi_demo_01` and confirm the output files and before/after plots are usable.

## Workflow

1. **Load ingestion outputs**
   Validate required columns and load AOI metadata.
2. **Collapse same-day duplicates**
   Merge duplicate observation days with valid-fraction-weighted averaging.
3. **Filter usable observations**
   Mark rows usable when `valid_fraction >= 0.90`.
4. **Smooth core metrics**
   Apply a centered rolling median of 3 observations, followed by a centered rolling mean of 3 observations, to NDVI/EVI/NDMI/NDWI usable series.
5. **Compute quality metrics**
   Produce usable observation count, gap ratio, max gap days, median gap days, and confidence inputs.
6. **Visual review**
   Plot raw, merged, and smoothed NDVI in a notebook for one AOI.

## Implementation details

### Entrypoint behavior

- CLI file: `scripts/preprocess_timeseries.py`
- Input resolution:
    - `--aoi-id <id>` resolves inputs from `data/<aoi_id>/`
    - `--input-dir <path>` overrides the default input directory
- Output resolution:
    - default output directory is `data/preprocess/<aoi_id>/`
    - `--output-dir <path>` overrides the default output directory
- Runtime parameter:
    - `--valid-fraction-threshold` defaults to `0.90`
- Required input files:
    - `indices_timeseries.csv`
    - `run_metadata.json`
- Failure behavior:
    - missing files raise `FileNotFoundError`
    - invalid or incomplete CSV structure raises `ValueError`
    - no usable observations after filtering raises `ValueError`

### Core pipeline structure

- Reusable logic lives in `farmtrust_core/preprocess/pipeline.py`
- Gap metrics live in `farmtrust_core/preprocess/gaps.py`
- Smoothing logic lives in `farmtrust_core/preprocess/smoothing.py`

### Input parsing and validation

- The preprocessing pipeline requires the ingestion CSV columns:
    - `item_id`
    - `timestamp`
    - `valid_fraction`
    - `ndvi_mean`
- Timestamps are parsed with `datetime.fromisoformat(...)`
- Naive timestamps are normalized to UTC
- Observations are sorted by timestamp before any merge or filter step

### Same-day duplicate merge logic

- Duplicate observations are grouped by UTC calendar day, not by exact timestamp
- Each merged day keeps:
    - the earliest timestamp from that day
    - valid-fraction-weighted average `valid_fraction`
    - valid-fraction-weighted average `ndvi_raw`
    - `source_row_count`
- Weight handling:
    - negative weights are clamped to `0`
    - if total weight is `0`, the pipeline falls back to a simple arithmetic mean

### Usability filter logic

- A merged observation is marked usable when:
    - `valid_fraction >= valid_fraction_threshold`
- Default threshold:
    - `0.90`
- Non-usable rows remain in the output CSV so downstream review can still inspect them
- Non-usable rows do not receive a smoothed value

### Smoothing logic

- Smoothing is applied only to usable metric values
- The current smoothing method is:
    - centered rolling median with window `3`
    - then centered rolling mean with window `3`
- Method name exposed to downstream roles:
    - `rolling_median_3_then_mean_3`
- Edge handling:
    - window bounds are clipped at the beginning and end of the series
    - no synthetic timestamps are created
    - no interpolation is performed

### Gap metrics and confidence inputs

- Gap metrics are computed only from usable timestamps
- Expected cadence:
    - `5.0` days
- Computed metrics:
    - `gap_ratio`
    - `max_gap_days`
    - `median_gap_days`
    - `gap_risk`
    - `confidence_penalty`
    - `gap_risk_reason`
- `gap_ratio` definition:
    - sum of gap days beyond expected cadence, divided by total usable-series span
    - bounded to `[0, 1]`
- Special cases:
    - no usable timestamps -> pipeline fails before metrics output
    - one usable timestamp -> `gap_ratio = 0`, `max_gap_days = 0`, `median_gap_days = 0`
- Confidence inputs exposed downstream:
    - `usable_observation_count`
    - `gap_ratio`
    - `max_gap_days`
- Gap-risk classification rules:
    - `high` when `max_gap_days > 15` or `gap_ratio > 0.30`
    - `moderate` when `max_gap_days > 10` or `gap_ratio > 0.15`
    - `low` otherwise
- Intended downstream use:
    - seasonal analysis should keep running but lower confidence interpretation when gap risk is `moderate` or `high`
    - later scoring should consume the same risk context instead of assuming all season timing is equally reliable

### Output writing behavior

- `ndvi_smoothed.csv` fields:
    - `timestamp`
    - `ndvi_raw`
    - `ndvi_smoothed`
    - `evi_raw`
    - `evi_smoothed`
    - `ndmi_raw`
    - `ndmi_smoothed`
    - `ndwi_raw`
    - `ndwi_smoothed`
    - `valid_fraction`
    - `is_usable`
    - `source_row_count`
- `quality_metrics.json` fields:
    - `aoi_id`
    - `total_observation_count`
    - `merged_observation_count`
    - `usable_observation_count`
    - `dropped_observation_count`
    - `gap_ratio`
    - `max_gap_days`
    - `median_gap_days`
    - `smoothing_method`
    - `usable_valid_fraction_threshold`
    - `gap_risk`
    - `confidence_penalty`
    - `gap_risk_reason`
    - `confidence_inputs`
- JSON is written through `safe_write_text(...)`

### Current demo behavior

- Demo AOI:
    - `aoi_demo_01`
- Current documented demo counts:
    - raw ingestion rows: `98`
    - merged daily rows: `43`
    - usable rows: `40`
    - dropped merged rows: `3`
- This means the current preprocessing slice is already producing a stable handoff for seasonal analysis.

## Operational notes

- Downstream seasonal analysis currently depends on:
    - `is_usable = true`
    - populated `ndvi_smoothed`
    - quality metrics keys in `quality_metrics.json`
- If the team changes:
    - `valid_fraction_threshold`
    - smoothing method
    - expected cadence
  then downstream season detection behavior may shift and should be re-reviewed.

## Example run

```powershell
python scripts\preprocess_timeseries.py --aoi-id aoi_demo_01
```

```powershell
python scripts\preprocess_timeseries.py --input-dir data\aoi_demo_01 --output-dir data\preprocess\aoi_demo_01
```

## Files, inputs, and outputs

### Files created

- `farmtrust_core/preprocess/pipeline.py`
  - Purpose: main preprocessing flow and output assembly.
- `farmtrust_core/preprocess/gaps.py`
  - Purpose: gap metrics and confidence input helpers.
- `farmtrust_core/preprocess/smoothing.py`
  - Purpose: deterministic smoothing method for usable NDVI rows.
- `scripts/preprocess_timeseries.py`
  - Purpose: local CLI entrypoint for preprocessing one AOI.
- `notebooks/01-preprocessing_ndvi.ipynb`
  - Purpose: visualize raw vs merged vs smoothed NDVI.
- `data/preprocess/aoi_demo_01/ndvi_smoothed.csv`
  - Purpose: demo output file for the processed NDVI series.
- `data/preprocess/aoi_demo_01/quality_metrics.json`
  - Purpose: demo output file for quality and confidence inputs.

### Input contract

- Input directory:
    - `data/<aoi_id>/`
- Required input files:
    - `indices_timeseries.csv`
    - `run_metadata.json`
- Required CSV columns:
    - `item_id`
    - `timestamp`
    - `valid_fraction`
    - `ndvi_mean`

### Output contract

- Output directory:
    - `data/preprocess/<aoi_id>/`
- Output file: `ndvi_smoothed.csv`
    - Fields:
        - `timestamp`
        - `ndvi_raw`
        - `ndvi_smoothed`
        - `valid_fraction`
        - `is_usable`
        - `source_row_count`
- Output file: `quality_metrics.json`
    - Fields:
        - `aoi_id`
        - `total_observation_count`
        - `merged_observation_count`
        - `usable_observation_count`
        - `dropped_observation_count`
        - `gap_ratio`
        - `max_gap_days`
        - `median_gap_days`
        - `smoothing_method`
        - `usable_valid_fraction_threshold`
        - `confidence_inputs`

### What changed in preprocessing

- Duplicate observations are merged by **calendar day**, not only exact timestamp.
- The merge uses **valid-fraction-weighted averaging**.
- Usability is defined as `valid_fraction >= 0.90`.
- Smoothing is:
    - centered rolling median, window 3
    - followed by centered rolling mean, window 3
- Non-usable rows stay in the output, but smoothed fields stay empty for them.

## R&D approach

- Keep the preprocessing contract file-based and narrow.
- Use deterministic, explainable logic before introducing interpolation or model-based smoothing.
- Promote any wider confidence-policy decisions to ENGINEERING only after agreement.

## Plan & milestones

### Milestone 1 - Preprocessing contract + core logic

**Deliverables**

- `farmtrust_core/preprocess/pipeline.py`
- `farmtrust_core/preprocess/gaps.py`
- `farmtrust_core/preprocess/smoothing.py`
- `scripts/preprocess_timeseries.py`

**Acceptance**

- Required ingestion columns are validated before processing.
- Same-day duplicates are collapsed to one observation day.
- Usable observations are marked with `valid_fraction >= 0.90`.
- Smoothing uses:
    - centered rolling median, window 3
    - followed by centered rolling mean, window 3
- No synthetic timestamps are created.

### Milestone 2 - Output files

**Deliverables**

- `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
- `data/preprocess/<aoi_id>/quality_metrics.json`

**Acceptance**

- `ndvi_smoothed.csv` contains:
    - `timestamp`
    - `ndvi_raw`
    - `ndvi_smoothed`
    - `valid_fraction`
    - `is_usable`
    - `source_row_count`
- `quality_metrics.json` contains:
    - `aoi_id`
    - `total_observation_count`
    - `merged_observation_count`
    - `usable_observation_count`
    - `dropped_observation_count`
    - `gap_ratio`
    - `max_gap_days`
    - `median_gap_days`
    - `smoothing_method`
    - `usable_valid_fraction_threshold`
    - `confidence_inputs`

### Milestone 3 - Notebook visualization

**Deliverables**

- `notebooks/01-preprocessing_ndvi.ipynb`

**Acceptance**

- Notebook loads one AOI ingestion run.
- Notebook shows duplicate observation days before merge.
- Notebook shows raw NDVI before preprocessing.
- Notebook shows merged and usable observations.
- Notebook shows smoothed NDVI after preprocessing.
- One combined before/after chart is included for quick visual comparison.

## Checklist (Definition of Done)

- [X] Preprocessing contract implemented
    - [X] Required columns validated
    - [X] Same-day duplicate merge implemented
    - [X] Usability filter implemented
    - [X] Smoothing method implemented
- [X] Output files generated for one AOI
    - [X] `ndvi_smoothed.csv` written
    - [X] `quality_metrics.json` written
    - [X] Metrics are non-null and stable on rerun
- [~] Notebook review completed
    - [X] Raw NDVI plot prepared
    - [X] Merged/usable plot prepared
    - [X] Smoothed NDVI plot prepared
    - [X] Before/after comparison plot prepared
    - [ ] Notebook needs end-to-end visual execution in Jupyter

## What still needs to change

- Execute `notebooks/01-preprocessing_ndvi.ipynb` in Jupyter and confirm the plots render as expected.
- Decide whether downstream seasonal analysis should consume:
    - only usable rows, or
    - all rows with `is_usable` as a mask.
- Decide whether the notebook should stay as a review artifact only, or whether a reusable script/PNG export is also needed for demos.
- If this preprocessing contract is accepted as stable shared truth, reflect the finalized handoff details in `docs/ENGINEERING.md`.

## Findings & learnings

2026-04-28 - Daily duplicate handling matters
The ingestion CSV contains repeated observation days from overlapping tiles and scene variants. Merging by calendar day reduced `98` raw rows to `43` effective daily observations for the demo AOI, which makes downstream smoothing and gap metrics more meaningful.
