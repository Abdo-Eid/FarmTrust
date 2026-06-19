# T-04 — Gap-Aware Signal Smoothing

## Goal

Replace order-based signal smoothing with a time-aware, gap-aware method that fits FarmTrust's explainable satellite-assessment use case.

Smoothing must reduce scene-level noise without hiding evidence gaps, inventing observations, or creating false vegetation continuity. Any gap greater than 12 days must break smoothing continuity.

## Scope

IN:
- Replace the current fixed 3-observation smoother with a timestamp-aware smoother.
- Do not smooth across usable-observation gaps greater than 12 days.
- Smooth only real usable observations; do not interpolate or create synthetic dates.
- Keep unusable observations present in outputs with blank/null smoothed values.
- Preserve raw values for audit/debug comparison.
- Align seasonal confirmation and scoring to use the same smoothed vegetation/moisture signal policy.
- Store only the minimal smoothing/evidence metadata needed for audit and downstream consistency.
- Add focused tests for spike reduction, gap blocking, no interpolation, and edge handling.

OUT:
- New satellite data sources.
- ML-based smoothing or crop-type-specific models.
- Portal redesign beyond any label/metadata changes needed to explain smoothing behavior.
- Changing evidence coverage thresholds beyond the 12-day smoothing break rule.
- A new large signal-object abstraction, unless implementation shows the existing handoff becomes unclear or fragile.

## Role Split

- Driver: implement the smoother, update preprocessing call sites, and add tests.
- Reviewer: verify the method cannot bridge evidence gaps or create false activity.
- Curator: promote durable smoothing policy to `PIPELINE.md` or `ENGINEERING.md` after implementation is verified.

## Chosen Approach

Use a conservative gap-aware time-window smoother:

- Keep the existing `valid_fraction >= 0.90` usability gate.
- Split usable observations into continuous segments where adjacent usable observations are no more than 12 days apart.
- Smooth only within each segment.
- For each usable observation, use nearby observations inside a local time window, not row-order neighbors across gaps.
- Prefer a robust local median followed by a local mean or weighted mean.
- If a point has too few local neighbors, keep its raw value.
- Store smoothing metadata so downstream outputs remain auditable.
- Do not introduce a formal signal bundle by default. Keep this task focused on smoothing and metadata. If a clearer handoff becomes necessary during implementation, keep it minimal: signals, evidence, and processing metadata only; no hidden scoring, UI labels, or business decisions.

Approved constants and behavior:
- `MAX_SMOOTHING_GAP_DAYS = 12.0`.
- `LOCAL_WINDOW_DAYS = 12.0`, interpreted as `±12` days around each real usable observation.
- `MIN_LOCAL_NEIGHBORS = 2`, excluding the center point.
- Two-pass robust smoother:
  - Pass 1: local median within the same continuous segment and `±12` days.
  - Pass 2: weighted mean over pass-1 values within the same continuous segment and `±12` days.
- Weight: `valid_fraction / (1 + abs(delta_days) / LOCAL_WINDOW_DAYS)`.
- If fewer than 2 neighbor usable observations exist inside the same segment/window, keep raw.
- 1-point and 2-point segments keep raw.
- Gaps greater than 12 days break smoothing continuity; a gap exactly 12 days remains continuous.
- Smooth only real usable observations; do not interpolate or create synthetic dates.

## Task List

- [x] Define final smoothing constants: max smoothing gap `12` days and local window size.
- [x] Update `farmtrust_core/preprocess/smoothing.py` to accept timestamps and valid fractions with each signal value.
- [x] Update `farmtrust_core/preprocess/pipeline.py` to pass timestamped usable observations into smoothing.
- [x] Ensure smoothing never crosses gaps greater than 12 days.
- [x] Ensure smoothing never creates synthetic timestamps or fills unusable rows.
- [x] Align season confirmation to use the intended smoothed `EVI`, `NDMI`, and `NDWI` values consistently.
- [x] Write tests for continuous-segment smoothing, spike reduction, long-gap blocking, edge values, and insufficient-neighbor fallback.
- [x] Update `quality_metrics.json` smoothing metadata with method name, max gap days, local window days, and interpolation policy.
- [x] Avoid a new large signal-object abstraction unless needed to prevent unclear field passing.
- [x] Run backend verification after implementation.

## Feedback Log

- 2026-06-17: User rejected keeping the current smoother as a baseline and asked why not implement the correct method for the use case.
- 2026-06-17: User requested a task and specified the gap break should be more than 12 days.
- 2026-06-17: User questioned whether a signal object would help or just add logic; scope now avoids a large abstraction unless it is clearly needed.
- 2026-06-18: User approved constants, weighted two-pass smoothing, no interpolation/synthetic dates, metadata, smoothed seasonal confirmation, and backend verification command.

## Decisions

- Smoothing must be gap-aware and time-aware.
- Gaps greater than 12 days break smoothing continuity.
- Smoothing must not interpolate or synthesize observations.
- Raw values remain available for audit.
- Do not create a large signal object as part of this task by default; use minimal metadata and only add a small handoff contract if the implementation becomes fragile without it.
- 2026-06-18: Use a two-pass local median then weighted-mean smoother with `MAX_SMOOTHING_GAP_DAYS = 12.0`, `LOCAL_WINDOW_DAYS = 12.0`, and `MIN_LOCAL_NEIGHBORS = 2`.
- 2026-06-18: 1-point and 2-point continuous segments keep raw values; observations with fewer than 2 local neighbors keep raw.
- 2026-06-18: Weight smoothed local mean by `valid_fraction / (1 + abs(delta_days) / LOCAL_WINDOW_DAYS)`.

## Open Questions

- Resolved: local smoothing window is `±12` days.
- Resolved: weighted mean uses both time distance and `valid_fraction`.
- Resolved: two-point segments keep raw values.

## Knowledge to Keep

- Current smoothing method is `rolling_median_3_then_mean_3`, which is order-based and can smooth across long evidence gaps.
- The corrected method must preserve evidence gaps because FarmTrust separates signal interpretation from evidence coverage and assessment confidence.
- A useful signal handoff is a boundary, not extra scoring logic: it should describe observed signals, evidence quality, and processing metadata only.
- This task should fix smoothing first; expanding a first-class vegetation/moisture/activity signal layer is future work only if the code needs it.
- Implemented smoothing method is `gap_aware_local_median_weighted_mean`.
- Seasonal confirmation and scoring now consume the same smoothed EVI, NDMI, and NDWI policy from preprocessing output.

## Done Summary

- Replaced order-based smoothing with timestamp-aware, gap-aware smoothing over real usable observations only.
- Preserved unusable rows with blank smoothed values and raw values for audit/debug comparison.
- Added smoothing metadata to quality metrics.
- Updated seasonal confirmation to use smoothed EVI, NDMI, and NDWI.
- Promoted durable smoothing policy and metadata fields to `PIPELINE.md`.
- Added focused backend tests for spike reduction, gap blocking, exact 12-day continuity, no interpolation/synthetic dates, unusable rows, edge handling, 1/2-point fallback, insufficient-neighbor fallback, metadata, and seasonal confirmation.
- Verification: `uv run python -m unittest discover -s tests` passed.
