# P-03 - Seasonal analysis baseline

This plan defines the minimal, testable seasonal-analysis slice for Phase A. It consumes preprocessing outputs, detects season windows from the smoothed NDVI series, assigns a rule-based season quality label, and produces a small JSON handoff for downstream scoring.

## Links

- PROJECT: <PROJECT Section MVP scope>
- ENGINEERING: <ENGINEERING Section Pipeline>
- PLAN: <P-01 - Starter pipeline for three roles>
- PLAN: <P-02 - Time-series preprocessing baseline>

## Ownership & boundaries

**Owner:** ML/seasonal analysis

## Overview of my task

Deliver a file-based seasonal-analysis contract that reads the preprocessing outputs, identifies all season windows in the available span, labels each season as `good`, `interrupted`, or `weak`, and records the key dates and evidence needed by downstream assessment.

## Current status

Implementation baseline is in place and has been run for `aoi_demo_01`.

- Plan file created: `docs/PLANS/P-03-seasonal-analysis.md`
- Seasonal-analysis code created:
    - `farmtrust_core/seasonal/seasons.py`
    - `farmtrust_core/seasonal/__init__.py`
- CLI entrypoint created:
    - `scripts/seasonal_analysis.py`
- Demo output generated:
    - `data/seasonal/aoi_demo_01/season_windows.json`
- Notebook created for review:
    - `notebooks/02-seasonal_review.ipynb`

### In scope

- Read `data/preprocess/<aoi_id>/ndvi_smoothed.csv` and `quality_metrics.json`.
- Use only usable rows with populated `ndvi_smoothed`.
- Detect all season windows from a fixed NDVI activity crossing threshold plus local peaks and backtracked start dates.
- Assign a rule-based season quality label.
- Write the season JSON contract for scoring.
- Provide a notebook view of the smoothed NDVI curve with season overlays.

### Out of scope (explicit non-goals)

- Multi-index primary season detection in v1.
- Learned or adaptive season detectors.
- Credit scoring or lender-facing aggregation.
- Public API/schema changes in `contracts/schemas/`.

## Outcomes (what "done" looks like)

1. Seasonal analysis produces at least one valid season window for the demo AOI.
2. Each detected season records start date, peak date, end date, peak NDVI, duration, quality label, and evidence summary.
3. The seasonal output is ready for the assessment/scoring role without depending on preprocessing internals.
4. A notebook clearly shows the detected season windows on top of the smoothed NDVI curve.

## Role details

- **Inputs**
    - `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
    - `data/preprocess/<aoi_id>/quality_metrics.json`
- **Responsibilities**
    - Validate the preprocessing contract.
    - Detect all season windows from the smoothed NDVI series.
    - Assign rule-based quality labels from curve shape.
    - Produce the minimal season JSON handoff.
- **Code location**
    - `farmtrust_core/seasonal/` for reusable logic
    - `scripts/seasonal_analysis.py` for the local entrypoint
- **Outputs**
    - `data/seasonal/<aoi_id>/season_windows.json`
    - `notebooks/02-seasonal_review.ipynb`
- **Fast test**
    - Run seasonal analysis on `aoi_demo_01` and confirm that at least one season window is generated with a non-empty quality label and can be inspected visually in the notebook.

## Workflow

1. **Load preprocessing outputs**
   Validate required files, columns, and keys.
2. **Filter seasonal input rows**
   Keep only rows with `is_usable = true` and a populated `ndvi_smoothed`.
3. **Detect candidate active windows**
   Use a fixed NDVI activity threshold to identify crossing-based active periods, then backtrack each retained season start to the earlier local low that begins the sustained rise.
4. **Derive season boundaries**
   Record start, local peak, and end for each retained season window, and mark end-of-series windows as open when the latest active season is still ongoing.
5. **Assign quality labels**
   Classify each season as `good`, `interrupted`, or `weak` from NDVI shape and duration.
6. **Write seasonal output**
   Persist the season JSON handoff for scoring.
7. **Visual review**
   Plot smoothed NDVI, the activity threshold, and the detected season spans in a notebook.

## Implementation details

### Entrypoint behavior

- CLI file: `scripts/seasonal_analysis.py`
- Input resolution:
    - `--aoi-id <id>` resolves inputs from `data/preprocess/<aoi_id>/`
    - `--input-dir <path>` overrides the default preprocessing input directory
- Output resolution:
    - default output directory is `data/seasonal/<aoi_id>/`
    - `--output-dir <path>` overrides the default seasonal output directory
- Required input files:
    - `ndvi_smoothed.csv`
    - `quality_metrics.json`
- Failure behavior:
    - missing files raise `FileNotFoundError`
    - missing required CSV columns raise `ValueError`
    - missing required quality-metrics keys raise `ValueError`
    - no usable smoothed observations raise `ValueError`
    - no retained season windows after detection raise `ValueError`

### Core detector structure

- Reusable logic lives in `farmtrust_core/seasonal/seasons.py`
- CLI orchestration lives in `scripts/seasonal_analysis.py`
- The detector consumes preprocessing outputs only; it does not depend on ingestion internals directly

### Input filtering logic

- Required preprocessing CSV columns:
    - `timestamp`
    - `ndvi_smoothed`
    - `evi_raw`
    - `ndmi_raw`
    - `ndwi_raw`
    - `is_usable`
    - `valid_fraction`
    - `source_row_count`
- Required `quality_metrics.json` keys:
    - `aoi_id`
    - `usable_observation_count`
    - `gap_ratio`
    - `max_gap_days`
    - `gap_risk`
- Seasonal detector keeps only rows where:
    - `is_usable = true`
    - `ndvi_smoothed` is populated
- Timestamps are normalized to UTC and sorted before detection

### Threshold and active-period detection

- Fixed activity threshold:
    - `0.18`
- Detector meaning:
    - threshold is used to confirm activity crossing
    - threshold is not treated as the literal agronomic season start
- Active periods are segmented as contiguous runs of usable smoothed observations where:
    - `ndvi_smoothed >= 0.18`
- Each segment records:
    - the first crossing index
    - the active rows that stay above threshold until the run ends

### Backtracked season start logic

- After the detector finds the first threshold crossing for a segment, it walks backward through the series
- Backtracking rule:
    - keep moving backward while the previous NDVI value is less than or equal to the current value
- Result:
    - `crossing_date` captures where the series first crossed the activity threshold
    - `start_date` captures the earlier local low that starts the sustained rise into the season
- This is the key rule that prevents visually late season starts from being reported as the true onset

### Left-edge exclusion logic

- A segment is excluded as a partial left-edge tail when:
    - it begins at the first observation in the available series
    - its peak occurs at that first observation
- Why:
    - this pattern means the dataset likely starts in the decline of an earlier season
    - the detector should not report that as a full season with an in-window onset

### Retention rules

- A segment must satisfy both:
    - at least `4` active observations above threshold
    - at least `20.0` days of retained season duration
- Duration is measured from backtracked `start_date` to retained `end_date`

### Peak and quality-label logic

- Peak date:
    - chosen as the timestamp with maximum `ndvi_smoothed` inside the retained season window
- Quality rules:
    - `weak` if `peak_ndvi < 0.24` or duration `< 20` days
    - `interrupted` if the maximum single-step drop is `>= 0.05`
    - `good` if `peak_ndvi >= 0.30` and rise gain from start to peak is `>= 0.08`
    - otherwise `weak`
- Rise gain:
    - `peak_ndvi - start_ndvi`
- Maximum drop:
    - largest one-step decrease between consecutive smoothed observations in the retained season window

### Open-season handling

- A season is marked open when its retained end is also the last usable observation in the available series
- Output field:
    - `is_open`
- Meaning:
    - the season is still active at the right edge of the available data
    - it should not be interpreted as a fully closed season
- Evidence behavior:
    - evidence summary is extended with a note that the season is still active at the end of the available series

### Gap-risk context from preprocessing

- Seasonal analysis reads preprocessing gap context from `quality_metrics.json`
- Current required upstream field:
    - `gap_risk`
- Current season-level confidence field:
    - `season_confidence_note`
- Current behavior:
    - season boundary detection does not change directly from `gap_risk`
    - season interpretation becomes more cautious when preprocessing continuity risk is moderate or high
    - this prevents fake certainty without forcing synthetic gap filling

### Output writing behavior

- `season_windows.json` top-level fields:
    - `aoi_id`
    - `season_count`
    - `seasons`
- Per-season output fields:
    - `season_id`
    - `crossing_date`
    - `start_date`
    - `peak_date`
    - `end_date`
    - `is_open`
    - `peak_ndvi`
    - `duration_days`
    - `quality_label`
    - `confirmation_level`
    - `evidence_summary`
    - `season_confidence_note`
- JSON is written through `safe_write_text(...)`

### Current demo behavior

- Demo AOI:
    - `aoi_demo_01`
- Current detector behavior on that AOI:
    - left-edge decline-only segment is excluded
    - one retained season remains
    - `crossing_date = 2025-10-07`
    - `start_date = 2025-09-24`
    - `peak_date = 2025-12-31`
    - `is_open = true`
- This means the current baseline now distinguishes:
    - threshold crossing
    - backtracked onset
    - ongoing right-edge season state

## Operational notes

- The seasonal detector is sensitive to:
    - preprocessing threshold choices
    - smoothing behavior
    - usable-observation gaps
- If preprocessing changes:
    - `valid_fraction_threshold`
    - smoothing method
    - gap behavior
  then season boundaries should be re-reviewed in the notebook.

- The review notebook is intended to verify:
    - whether `crossing_date` looks plausible
    - whether `start_date` is too early or too late
    - whether an `is_open = true` season is visually still active
    - whether quality labels match the shape of the curve

## Example run

```powershell
python scripts\seasonal_analysis.py --aoi-id aoi_demo_01
```

```powershell
python scripts\seasonal_analysis.py --input-dir data\preprocess\aoi_demo_01 --output-dir data\seasonal\aoi_demo_01
```

## Files, inputs, and outputs

### Files created

- `farmtrust_core/seasonal/seasons.py`
  - Purpose: load preprocessing output, detect seasons, assign quality labels, and assemble the JSON payload.
- `scripts/seasonal_analysis.py`
  - Purpose: local CLI entrypoint for seasonal analysis.
- `data/seasonal/aoi_demo_01/season_windows.json`
  - Purpose: demo output file for detected season windows.
- `notebooks/02-seasonal_review.ipynb`
  - Purpose: visualize smoothed NDVI with detected season windows, threshold line, and annotated start/peak/end markers.

### Input contract

- Input directory:
    - `data/preprocess/<aoi_id>/`
- Required input files:
    - `ndvi_smoothed.csv`
    - `quality_metrics.json`
- Required CSV columns:
    - `timestamp`
    - `ndvi_smoothed`
    - `is_usable`
    - `valid_fraction`
    - `source_row_count`
- Required quality-metrics keys:
    - `aoi_id`
    - `usable_observation_count`
    - `gap_ratio`
    - `max_gap_days`

### Output contract

- Output directory:
    - `data/seasonal/<aoi_id>/`
- Output file: `season_windows.json`
    - Top-level fields:
        - `aoi_id`
        - `season_count`
        - `seasons`
    - Per-season fields:
        - `season_id`
        - `crossing_date`
        - `start_date`
        - `peak_date`
        - `end_date`
        - `is_open`
        - `peak_ndvi`
        - `duration_days`
        - `quality_label`
        - `evidence_summary`

### What changed in seasonal analysis

- Detection uses **smoothed NDVI only** in v1.
- All detected seasons are returned, not just the latest season.
- Active periods are confirmed by a fixed NDVI crossing threshold `0.18`.
- Season `start_date` is backtracked from the first threshold crossing to the earlier local low that begins the rise into the season.
- Left-edge partial tails are excluded when the available series starts already above the threshold and shows no in-window onset before decline.
- End-of-series active windows are still emitted as seasons when they satisfy the minimum checks, but they are marked `is_open = true` instead of being treated as fully closed seasons.
- Quality labels are assigned in this stage, not deferred to scoring.

## R&D approach

- Keep the detector deterministic and explainable.
- Prefer simple threshold-crossing and local-peak rules before introducing change-point models.
- Promote wider season-policy changes to ENGINEERING only after agreement.

## Plan & milestones

### Milestone 1 - Seasonal contract + detector

**Deliverables**

- `farmtrust_core/seasonal/seasons.py`
- `scripts/seasonal_analysis.py`

**Acceptance**

- Required preprocessing columns and keys are validated before processing.
- Detector uses only usable rows with non-empty `ndvi_smoothed`.
- Candidate seasons are identified from threshold crossings plus local peaks.
- Short noise windows are ignored by a minimum-duration rule.

### Milestone 2 - Season output file

**Deliverables**

- `data/seasonal/<aoi_id>/season_windows.json`

**Acceptance**

- JSON contains `aoi_id`, `season_count`, and `seasons`.
- Each season contains start date, peak date, end date, peak NDVI, duration, quality label, and evidence summary.
- At least one season window is generated for the current 12-24 month demo span.

### Milestone 3 - Notebook visualization

**Deliverables**

- `notebooks/02-seasonal_review.ipynb`

**Acceptance**

- Notebook loads one AOI seasonal output and the matching preprocessing file.
- Notebook plots the smoothed NDVI curve and the detector activity threshold.
- Notebook shades each detected season span.
- Notebook marks season start, peak, and end dates on the plot.
- Notebook shows the quality label for each season in the visual review.

## Checklist (Definition of Done)

- [X] Seasonal contract implemented
    - [X] Required preprocessing files validated
    - [X] Required CSV columns validated
    - [X] Required quality-metrics keys validated
    - [X] Usable smoothed rows filtered
- [X] Season detector implemented
    - [X] Activity-threshold segmentation implemented
    - [X] Peak extraction implemented
    - [X] Minimum-duration filtering implemented
    - [X] Rule-based quality labeling implemented
- [X] Seasonal output generated for one AOI
    - [X] `season_windows.json` written
    - [X] At least one season detected for `aoi_demo_01`
    - [X] Each season includes a non-empty quality label and evidence summary
- [X] Notebook review layer created
    - [X] Seasonal review notebook created
    - [X] Smoothed NDVI plot prepared
    - [X] Threshold line prepared
    - [X] Season span overlays prepared
    - [X] Start/peak/end markers prepared

## Findings & learnings

2026-04-30 - End-of-series seasons must be handled explicitly
The demo AOI contains an active late-season rise that is still increasing at the end of the available NDVI series. The baseline detector must keep these windows instead of requiring a closed decline, otherwise the latest season would be dropped before scoring.
