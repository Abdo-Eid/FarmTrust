# T-05 — Vegetation Activity Window Detection

## Goal

Replace over-confident season interpretation with conservative vegetation activity-window detection for FarmTrust's current satellite-only assessment use case.

FarmTrust should detect observed vegetation activity from Sentinel-2 evidence, not claim exact crop seasons, planting dates, or harvest dates without crop calendars, crop type, or ground-truth validation.

## Scope

IN:
- Rename current user-facing and durable-doc concepts from `season` to `vegetation activity window` where the claim is not agronomically validated.
- Keep code names unchanged only where a larger rename would create unnecessary churn; if retained, document that `season` means detected activity window.
- Replace fixed-threshold-only detection with a conservative activity-window method using local baseline, peak, amplitude, and sustained activity.
- Keep `NDVI` as the main activity curve, with `EVI`, `NDMI`, and `NDWI` used as confirmation/support signals.
- Treat evidence gaps as boundary/confidence limitations, not land risk by themselves.
- Mark open/right-edge windows as provisional.
- Add visual and test validation for activity windows, gap overlap, weak activity, and conflicting signals.

OUT:
- Exact crop phenology labels such as planting, emergence, heading, harvest, or crop-stage names.
- Crop-specific calendars or crop-type models.
- ML-based crop classification or yield prediction.
- Interpolation or synthetic observations to force complete activity curves.
- A large signal-object abstraction unless implementation becomes fragile without a minimal handoff contract.

## Dependencies

- `T-04 — Gap-Aware Signal Smoothing` should be completed first so activity windows are built from trustworthy smoothed signals.
- `T-03 — Evidence Confidence Gate` should inform how limited or insufficient satellite evidence changes assessment confidence and completeness.

## Interfaces

- Input: `data/preprocess/<aoi_id>/ndvi_smoothed.csv` and `quality_metrics.json`.
- Current output affected: `data/seasonal/<aoi_id>/season_windows.json`.
- Current scoring consumer affected: `farmtrust_core/scoring/rules.py`.
- API/report/portal terms may need follow-up updates if output field names change from season-oriented wording.

## Role Split

- Driver: implement activity-window detection and adapt scoring consumers.
- Reviewer: verify the method does not overclaim true agricultural seasons or hide gaps.
- Curator: update durable docs after implementation so product wording matches the detector's real capability.

## Chosen Approach

Use a conservative activity-window detector:

- Detect activity from smoothed `NDVI`, after `T-04` gap-aware smoothing.
- Use local baseline, local peak, and seasonal amplitude instead of relying only on a fixed global threshold.
- Keep a fixed low vegetation floor as a guardrail, not the full definition of activity.
- Require sustained activity with minimum duration and minimum usable observations.
- Treat windows with gaps near onset, peak, or tail as uncertain/provisional rather than forcing precise boundaries.
- Confirm activity strength with `EVI` and moisture/wetness context from `NDMI` and `NDWI`.
- Output language should say `detected vegetation activity window` unless validation later supports stronger season wording.

## Task List

- [x] Define activity-window terminology and update docs/UI copy where current wording overclaims seasons.
- [x] Define dynamic threshold rules: baseline, peak, amplitude fraction, low vegetation floor, and minimum rise.
- [x] Define minimum duration and minimum usable-observation rules for an activity window.
- [x] Define gap handling for onset, peak, tail, and internal gaps.
- [x] Define open/right-edge window behavior and provisional wording.
- [x] Decide whether `MNDWI` should be added downstream for water/wetness confirmation.
- [x] Update detector implementation in `farmtrust_core/seasonal/seasons.py` or introduce a clearly named activity-window module if the rename is worth the churn.
- [x] Update scoring in `farmtrust_core/scoring/rules.py` to consume activity-window outputs without claiming true seasons.
- [x] Add tests for no-activity, weak activity, sustained activity, two activity windows, gap-overlapped activity, and open-window cases.
- [x] Add visual validation artifacts or script output showing raw signals, smoothed signals, gaps, and detected activity windows.
- [x] Run backend verification after implementation.

## Feedback Log

- 2026-06-17: User identified that FarmTrust does not currently have a good way to know true seasons.
- 2026-06-17: User approved opening a task for the best approach for the current use case.
- 2026-06-18: User approved final detector constants, no-MNDWI decision, compatibility field-name policy, added activity-window fields, and validation-script requirement.

## Decisions

- Use `vegetation activity window` as the honest current concept.
- Do not claim exact agronomic seasons without crop calendars, crop type, or ground-truth validation.
- `NDVI` remains the primary activity curve.
- `EVI`, `NDMI`, and `NDWI` support confirmation and context.
- Evidence gaps affect boundary certainty and assessment confidence, not land status by themselves.
- Keep durable/API field names such as `season_count`, `seasons`, `season_id`, `season_performance`, and `season_records` for now; document that `season` means detected vegetation activity window.
- Defer `MNDWI` in T-05 because it is not part of the current preprocessing/seasonal contract.
- Use `BASELINE_METHOD = "local_p20_smoothed_ndvi"` with `BASELINE_WINDOW_DAYS = 90.0`, `BASELINE_PERCENTILE = 20.0`, and `MIN_LOCAL_BASELINE_OBSERVATIONS = 5`.
- Use `PEAK_METHOD = "max_smoothed_ndvi_in_candidate_window"`.
- Use `ACTIVITY_BOUNDARY_AMPLITUDE_FRACTION = 0.35`, `LOW_VEGETATION_FLOOR = 0.18`, `MIN_ACTIVITY_AMPLITUDE = 0.08`, and `GOOD_ACTIVITY_AMPLITUDE = 0.12`.
- Require `MIN_ACTIVITY_WINDOW_DURATION_DAYS = 20.0` and `MIN_ACTIVITY_WINDOW_OBSERVATIONS = 4`.
- Mark right-edge windows as `is_open = true`, `provisional = true`, and `end_boundary_certainty = "open"`.
- Add `terminology.season = "detected vegetation activity window, not an agronomic crop season"` to `season_windows.json`.

## Open Questions

- None for this implementation slice.

## Knowledge to Keep

- Current code detects threshold-based activity periods, not true agronomic seasons.
- Fixed `NDVI >= 0.18` is useful as a simple floor but should not be treated as a complete season model.
- Research-backed phenology methods commonly use smoothed curves, quality weighting, local amplitude thresholds, and validation against crop/region context.
- FarmTrust's current strongest product claim is observed vegetation activity with stated evidence coverage and assessment confidence.
- T-05 keeps the existing `season_*` compatibility fields but adds explicit terminology and per-window activity metadata.
- `scripts/activity_window_validation.py` writes a validation CSV with raw signals, smoothed signals, gap markers, and detected activity-window markers.

## Done Summary

- Implemented conservative vegetation activity-window detection with local baseline/amplitude rules, gap certainty fields, right-edge provisional behavior, and no interpolation/synthetic observations.
- Updated scoring/report/portal wording to avoid agronomic season claims while preserving durable API field names.
- Backend verification: `uv run python -m unittest discover -s tests` passed with 21 tests.
