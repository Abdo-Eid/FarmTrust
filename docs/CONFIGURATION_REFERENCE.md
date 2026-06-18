# FarmTrust Configuration Reference

## Purpose

This document summarizes the important variables, thresholds, constants, and output fields used in FarmTrust's current satellite-only assessment logic. It focuses on evidence confidence, gap-aware smoothing, and vegetation activity-window detection.

The goal is to make the field-facing interpretation rules auditable without requiring reviewers to read the full codebase.

## Scope

This reference covers:

- T-03 Evidence Confidence Gate
- T-04 Gap-Aware Signal Smoothing
- T-05 Vegetation Activity Window Detection

It is intended for technical reviewers, professors, and domain evaluators. It documents current implementation behavior, not scientific validation or final agronomic calibration.

Primary source files:

- `farmtrust_core/scoring/rules.py`
- `farmtrust_core/preprocess/smoothing.py`
- `farmtrust_core/preprocess/gaps.py`
- `farmtrust_core/preprocess/pipeline.py`
- `farmtrust_core/seasonal/seasons.py`
- `api/schemas.py`
- `api/assessment_mapper.py`
- `contracts/schemas/land-result.json`
- `portal/src/lib/types.ts`
- `docs/DECISIONS.md`
- `docs/PIPELINE.md`

## Key Interpretation Rules

- Missing satellite observations are evidence limitations, not land or farmer risk.
- `land_status` is derived only from observed land signals.
- Evidence gaps can lower assessment confidence or require manual review.
- Smoothing reduces noise but must not hide evidence gaps.
- Activity windows are observed vegetation activity windows, not verified agronomic crop seasons.
- The system does not infer planting date, harvest date, crop type, or yield.

## T-03 Evidence Confidence Gate Parameters

Source files: `farmtrust_core/scoring/rules.py`, `api/schemas.py`, `api/assessment_mapper.py`, `contracts/schemas/land-result.json`, `portal/src/lib/types.ts`, `docs/DECISIONS.md`, `docs/PIPELINE.md`.

| Parameter / Field | Value / Threshold | Source | Meaning | Effect on Output |
|---|---:|---|---|---|
| `usable_observation_count` | Integer count | `quality_metrics.json`, `rules.py` | Number of usable satellite observations after preprocessing. | Drives `satellite_evidence_coverage` and assessment confidence. |
| `gap_ratio` | `0.0` to `1.0` | `gaps.py`, `rules.py` | Excess gap days beyond expected cadence divided by usable-series span. | High values reduce coverage tier and confidence. |
| `max_gap_days` | Days | `gaps.py`, `rules.py` | Largest gap between adjacent usable observations. | Large gaps reduce coverage tier and confidence. |
| `long_gap_count` | Integer count | `gaps.py`, `rules.py` | Number of usable-observation gaps greater than `10.0` days. | Frequent long gaps reduce coverage tier. |
| `gap_risk` | `low`, `moderate`, `high` | `gaps.py`, `rules.py` | Internal evidence-continuity classification, not land risk. | Helps classify `satellite_evidence_coverage`; should not become a land risk flag. |
| `satellite_evidence_coverage` | `good`, `fair`, `limited`, `insufficient` | `rules.py`, `api/schemas.py` | Public evidence coverage band. | Explains whether satellite evidence is adequate for automated interpretation. |
| `assessment_confidence` / `confidence` | `high`, `medium`, `low` | `rules.py`, `api/schemas.py` | Confidence in FarmTrust's conclusion, not confidence in the land. | Capped by evidence coverage tier. |
| `assessment_status` | `complete`, `manual_review_required` | `rules.py`, `api/schemas.py` | Whether automated outputs can be presented as final. | `manual_review_required` suppresses final automated land outputs. |
| `review_required` | Not present as a separate field | `api/schemas.py`, `contracts/schemas/land-result.json` | Manual review is represented by `assessment_status = "manual_review_required"`. | No separate `review_required` boolean exists in the current API. |
| `land_status` | `active`, `intermittent`, `inactive`, `encroachment`; nullable in API | `rules.py`, `api/schemas.py` | Observed land activity/status. | Set to `null` in public API when evidence is insufficient. |
| `risk_flags` / public `flags` | Internal codes mapped to `waterlogging`, `salinity`, `abandonment`, `encroachment` | `rules.py`, `assessment_mapper.py`, `api/schemas.py` | Land/farming issue flags only. | Evidence gaps must not create these flags; cleared for manual review results. |
| `trend_2y` | `improving`, `stable`, `declining`; internal may also use `uncertain`; nullable in API | `rules.py`, `api/schemas.py` | Conservative trend from activity-window strength summaries. | Set to `null` in public API when evidence is insufficient or trend is uncertain. |
| `season_performance` | `good`, `interrupted`, `weak`; nullable in API | `rules.py`, `api/schemas.py` | Compatibility field for latest vegetation activity-window performance. | Set to `null` when evidence is insufficient. |
| `risk_tier` | `low`, `medium`, `high`; nullable in API | `assessment_mapper.py`, `api/schemas.py` | Public aggregate risk tier from land risk flag severities. | Set to `null` when evidence is insufficient. |

### Evidence Coverage Threshold Policy

Thresholds are ordered first match wins in `farmtrust_core/scoring/rules.py`.

| Coverage Tier | Exact Rule | Output Meaning |
|---|---|---|
| `insufficient` | `usable_observation_count < 12`, or `gap_ratio > 0.60`, or `max_gap_days > 90`, or `long_gap_count > 12` | Automated assessment requires manual review. |
| `limited` | `usable_observation_count < 30`, or `gap_risk == "high"`, or `gap_ratio > 0.30`, or `max_gap_days > 45`, or `long_gap_count > 6` | Automated interpretation is possible but low confidence. |
| `fair` | `usable_observation_count < 60`, or `gap_risk == "moderate"`, or `gap_ratio > 0.15`, or `max_gap_days > 10`, or `long_gap_count > 0` | Evidence is usable but thinner than preferred. |
| `good` | None of the above | Evidence is continuous enough for normal automated output. |

### Confidence Cap Policy

| Evidence Coverage | Confidence Cap | Effect |
|---|---|---|
| `good` | No cap | Computed confidence is preserved. |
| `fair` | Maximum `medium` | `high` confidence is reduced to `medium`. |
| `limited` | Maximum `low` | Confidence is capped at `low`. |
| `insufficient` | `low` | Confidence is `low` and `assessment_status` becomes `manual_review_required`. |

For `insufficient` coverage, the public API/report does not present final automated `land_status`, `risk_tier`, `trend_2y`, or `season_performance`. It preserves evidence coverage and confidence context.

## T-04 Gap-Aware Signal Smoothing Parameters

Source files: `farmtrust_core/preprocess/smoothing.py`, `farmtrust_core/preprocess/gaps.py`, `farmtrust_core/preprocess/pipeline.py`, `docs/PIPELINE.md`.

| Parameter / Constant | Value | Source | Meaning | Effect on Output |
|---|---:|---|---|---|
| `MAX_SMOOTHING_GAP_DAYS` | `12.0` days | `smoothing.py` | Maximum usable-observation gap allowed inside one smoothing segment. | Gaps greater than `12.0` days break smoothing continuity. |
| `LOCAL_WINDOW_DAYS` | `12.0` days | `smoothing.py` | Local smoothing window around each real usable observation. | Uses observations within `+/-12` days inside the same segment. |
| `MIN_LOCAL_NEIGHBORS` | `2` | `smoothing.py` | Minimum neighbor count, excluding the center point. | Points with fewer neighbors keep raw values. |
| `valid_fraction` | `0.0` to `1.0` | `pipeline.py` | Fraction of usable pixels in the AOI observation. | Determines whether an observation is usable and weights smoothing. |
| Usability gate | `valid_fraction >= 0.90` | `pipeline.py` | Minimum usable-pixel fraction for smoothing/scoring. | Rows below this remain in output but receive blank smoothed values. |
| `NDVI` | Raw and smoothed | `pipeline.py` | Main vegetation signal. | Smoothed NDVI drives activity-window detection and scoring. |
| `EVI` | Raw and smoothed | `pipeline.py` | Supporting vegetation signal. | Smoothed EVI supports activity-window confirmation. |
| `NDMI` | Raw and smoothed | `pipeline.py` | Moisture support signal. | Smoothed NDMI supports activity-window confirmation and risk interpretation. |
| `NDWI` | Raw and smoothed | `pipeline.py` | Wetness / non-water support signal. | Smoothed NDWI supports activity-window confirmation and risk interpretation. |
| Raw values | `ndvi_raw`, `evi_raw`, `ndmi_raw`, `ndwi_raw` | `pipeline.py` | Unsmoothened merged same-day signal values. | Preserved for audit/debug comparison. |
| Smoothed values | `ndvi_smoothed`, `evi_smoothed`, `ndmi_smoothed`, `ndwi_smoothed` | `pipeline.py`, `smoothing.py` | Gap-aware smoothed signal values. | Used by seasonal/activity-window and scoring consumers. |
| `smoothing_method` | `gap_aware_local_median_weighted_mean` | `smoothing.py` | Method metadata in `quality_metrics.json`. | Makes the smoothing method auditable. |
| Weighting policy | `valid_fraction / (1 + abs(delta_days) / LOCAL_WINDOW_DAYS)` | `smoothing.py` | Time-distance and quality weighted mean in pass 2. | Closer, higher-quality observations receive greater weight. |
| Interpolation policy | `none` | `smoothing.py` | No values are invented between observations. | Prevents false continuity across missing evidence. |
| Synthetic timestamp policy | `creates_synthetic_timestamps = false` | `smoothing.py` | No artificial dates are created. | Preserves real observation timing. |
| Unusable observation behavior | Keep row, blank smoothed values | `pipeline.py` | Rows below usability threshold remain visible. | Output preserves evidence gaps and rejected observations. |
| `EXPECTED_CADENCE_DAYS` | `5.0` days | `gaps.py` | Expected Sentinel-2 usable cadence assumption for gap metrics. | Used to compute `gap_ratio` and excess gap days. |
| `MODERATE_GAP_DAYS` | `10.0` days | `gaps.py` | Internal moderate continuity threshold. | Gaps above this are recorded in `long_gap_windows`. |
| `HIGH_GAP_DAYS` | `15.0` days | `gaps.py` | Internal high continuity threshold. | Helps set `gap_risk = "high"`. |

Implementation notes:

- Gaps greater than `12.0` days break smoothing continuity.
- Gaps exactly `12.0` days remain continuous.
- Smoothing only uses real usable observations.
- Unusable rows stay in `ndvi_smoothed.csv` with blank smoothed values.
- Raw values are preserved for audit/debug comparison.
- The smoother uses two passes: local median, then weighted mean over pass-1 values.
- One-point and two-point continuous segments keep raw values.

Important `quality_metrics.json` smoothing metadata:

- `smoothing_method`
- `max_smoothing_gap_days`
- `local_window_days`
- `minimum_local_neighbors`
- `minimum_local_neighbors_excludes_center`
- `weighting_policy`
- `interpolation_policy`
- `creates_synthetic_timestamps`
- `smooths_only_usable_observations`
- `usable_valid_fraction_threshold`

## T-05 Vegetation Activity Window Detection Parameters

Source files: `farmtrust_core/seasonal/seasons.py`, `farmtrust_core/scoring/rules.py`, `api/assessment_mapper.py`, `docs/PIPELINE.md`.

| Parameter / Field | Value / Threshold | Source | Meaning | Effect on Output |
|---|---:|---|---|---|
| `BASELINE_METHOD` | `local_p20_smoothed_ndvi` | `seasons.py` | Local NDVI baseline method. | Activity amplitude is measured against local baseline. |
| `BASELINE_WINDOW_DAYS` | `90.0` days | `seasons.py` | Time window for local baseline. | Uses smoothed NDVI within `+/-90` days. |
| `BASELINE_PERCENTILE` | `20.0` | `seasons.py` | Percentile used for local baseline. | Conservative low reference level for activity. |
| `MIN_LOCAL_BASELINE_OBSERVATIONS` | `5` | `seasons.py` | Minimum local observations for baseline. | Falls back to full-series p20 when local support is sparse. |
| `PEAK_METHOD` | `max_smoothed_ndvi_in_candidate_window` | `seasons.py` | Peak method. | Peak date/value come only from real usable observations. |
| `ACTIVITY_BOUNDARY_AMPLITUDE_FRACTION` | `0.35` | `seasons.py` | Fraction of amplitude used for boundaries. | Boundary threshold is `max(0.18, baseline + 0.35 * amplitude)`. |
| `LOW_VEGETATION_FLOOR` | `0.18` | `seasons.py` | Minimum NDVI floor. | Observations below this cannot start or sustain an activity window. |
| `ACTIVITY_THRESHOLD` | `0.18` | `seasons.py`, `rules.py` | Alias of `LOW_VEGETATION_FLOOR`. | Used in active-observation fraction during scoring. |
| `MIN_ACTIVITY_AMPLITUDE` | `0.08` | `seasons.py` | Minimum peak minus baseline. | Candidate windows below this are ignored as no detected activity window. |
| `GOOD_ACTIVITY_AMPLITUDE` | `0.12` | `seasons.py` | Stronger amplitude threshold for labeling. | Required for `good` quality label. |
| `MIN_ACTIVITY_WINDOW_DURATION_DAYS` | `20.0` days | `seasons.py` | Minimum observed duration. | Shorter candidates are rejected. |
| `MIN_ACTIVITY_WINDOW_OBSERVATIONS` | `4` | `seasons.py` | Minimum real usable observations per window. | Sparse candidates are rejected. |
| `GOOD_PEAK_THRESHOLD` | `0.30` NDVI | `seasons.py` | Peak threshold for `good` label. | Helps classify strong activity windows. |
| `INTERRUPTED_DROP_THRESHOLD` | `0.05` NDVI | `seasons.py` | Maximum single-step drop threshold. | Can label observed signal as `interrupted`. |
| `EVI_CONFIRMATION_MIN` | `0.20` | `seasons.py` | EVI support threshold. | EVI confirms when max smoothed EVI in window is at least `0.20`. |
| `NDMI_CONFIRMATION_MIN` | `0.05` | `seasons.py` | Moisture support threshold. | NDMI supports when median smoothed NDMI in window is at least `0.05`. |
| `NDWI_CONFIRMATION_MAX` | `0.20` | `seasons.py` | Wetness/non-water support threshold. | NDWI supports when median smoothed NDWI in window is at most `0.20`. |
| `confirmation_level` | `strong`, `moderate`, `weak` | `seasons.py` | Multi-index support level. | `strong` means all EVI/NDMI/NDWI checks pass; `moderate` means any 2 pass; `weak` means 0 or 1 pass. Weak confirmation caps quality at `weak`. |
| `window_type` | `vegetation_activity` | `seasons.py` | Explicit semantic type. | Clarifies that the record is not a verified crop season. |
| `provisional` | Boolean | `seasons.py` | Boundary or right-edge uncertainty flag. | `true` for open windows or onset/tail gap uncertainty. |
| `baseline_ndvi` | Number | `seasons.py` | Local baseline at detected peak. | Supports review of amplitude calculation. |
| `amplitude_ndvi` | Number | `seasons.py` | `peak_ndvi - baseline_ndvi`. | Explains why a candidate passed detection. |
| `boundary_threshold_ndvi` | Number | `seasons.py` | `max(0.18, baseline + 0.35 * amplitude)`. | Determines observed start/end rows for the activity window. |
| `usable_observation_count` | Integer | `seasons.py` | Number of real usable observations inside the window. | Documents evidence support for the window. |
| `start_boundary_certainty` | `clear`, `limited` | `seasons.py` | Certainty of observed start boundary. | `limited` when a long gap overlaps the onset zone. |
| `peak_certainty` | `clear`, `limited` | `seasons.py` | Certainty of observed peak. | `limited` when a long gap overlaps the peak zone. |
| `end_boundary_certainty` | `clear`, `limited`, `open` | `seasons.py` | Certainty of observed end boundary. | `open` for right-edge active windows; `limited` when a long gap overlaps the tail zone. |
| `internal_gap_count` | Integer | `seasons.py` | Count of long gaps internal to a window and away from onset/peak/tail. | Evidence limitation only; not a land risk flag. |
| `is_open` | Boolean | `seasons.py` | Window reaches latest usable observation. | Open windows are provisional; no harvest/end claim is made. |
| `season_count` | Integer | `season_windows.json` | Compatibility field for activity-window count. | Counts detected vegetation activity windows. |
| `seasons` | Array | `season_windows.json` | Compatibility field for activity-window records. | Contains one object per detected activity window. |
| `season_id` | `season_01`, `season_02`, ... | `seasons.py` | Compatibility identifier. | Stable record ID inside `season_windows.json`. |
| `crossing_date` | Date string | `seasons.py` | First retained observed boundary date. | Does not mean planting date. |
| `start_date` | Date string | `seasons.py` | Observed start boundary date. | Does not mean planting date. |
| `peak_date` | Date string | `seasons.py` | Date of maximum smoothed NDVI in the window. | Real observation date only. |
| `end_date` | Date string | `seasons.py` | Observed end boundary date or latest usable date for open windows. | Does not mean harvest date. |
| `peak_ndvi` | Number | `seasons.py` | Maximum smoothed NDVI in the window. | Supports label, trend, and report summaries. |
| `duration_days` | Number | `seasons.py` | Days between observed start and end. | Must be at least `20.0` for retained windows. |
| `quality_label` | `good`, `interrupted`, `weak` | `seasons.py` | Conservative signal-quality label. | Feeds `season_performance` compatibility field. |
| `evidence_summary` | Text | `seasons.py` | Explanation of peak, amplitude, confirmation, and gap overlap. | Used in report/API anomaly wording. |
| `gap_overlap_count` | Integer | `seasons.py` | Number of long gaps overlapping the window. | Evidence limitation for the activity window. |
| `gap_overlap_risk` | `low`, `moderate`, `high` | `seasons.py` | Internal severity of gap overlap. | Reduces confidence; does not create land risk flags. |
| `gap_overlap_stage` | `none`, `onset`, `peak`, `tail`, `middle`, `multiple` | `seasons.py` | Dominant activity-window zone touched by long gaps. | Explains boundary or peak uncertainty. |
| `season_confidence_note` | Text | `seasons.py` | Gap-risk note from quality metrics. | Adds evidence coverage context to each window record. |
| `terminology` | `{ "season": "detected vegetation activity window, not an agronomic crop season" }` | `seasons.py` | Top-level semantic clarification. | Prevents compatibility field names from overclaiming agronomic seasons. |

Additional behavior:

- Existing `season_*` fields are retained for API and file compatibility.
- In current FarmTrust meaning, those fields represent detected vegetation activity windows, not true agronomic crop seasons.
- Open/right-edge windows are provisional.
- Evidence gaps affect boundary certainty, provisional state, and assessment confidence; they do not create land risk flags.
- MNDWI is deferred in T-05. It is produced upstream where available but is not part of the current preprocessing/activity-window/scoring contract.

Gap zones for activity-window uncertainty:

- Onset zone: first third of observed window.
- Peak zone: `peak_date +/- max(6 days, duration_days / 6)`.
- Tail zone: last third of observed window.
- Long gap in onset: `start_boundary_certainty = "limited"` and `provisional = true`.
- Long gap in peak zone: `peak_certainty = "limited"`.
- Long gap in tail: `end_boundary_certainty = "limited"` and `provisional = true`.
- Internal long gaps increment `internal_gap_count`.

## Output Behavior Summary

| Situation | Output Behavior |
|---|---|
| Evidence is `good` | Automated assessment can be complete. Confidence is not capped by evidence coverage. |
| Evidence is `fair` | Automated assessment can be complete. Confidence is capped at `medium`. |
| Evidence is `limited` | Automated assessment can be complete, but confidence is capped at `low`. |
| Evidence is `insufficient` | `assessment_status = "manual_review_required"`; public API/report suppresses final automated `land_status`, `trend_2y`, `season_performance`, `risk_tier`, and land risk flags. |
| Activity window is open | `is_open = true`, `provisional = true`, `end_boundary_certainty = "open"`; no harvest/end claim is made. |
| Activity window overlaps evidence gaps | Gap overlap is recorded in boundary/peak/internal fields and confidence reasons. It does not create land/farming risk flags by itself. |

## Reviewer Notes

Policy choices:

- Evidence coverage thresholds for `good`, `fair`, `limited`, and `insufficient`.
- Confidence caps by evidence coverage tier.
- Manual-review-required behavior for insufficient evidence.
- Retaining `season_*` field names for compatibility while redefining their current semantics.

Conservative safeguards:

- Missing/cloudy observations are treated as evidence limitations.
- No interpolation or synthetic timestamps are used.
- Smoothing does not cross usable-observation gaps greater than `12.0` days.
- Activity windows require minimum amplitude, duration, and usable observations.
- Open/right-edge windows are marked provisional.
- Weak multi-index confirmation caps activity-window quality at `weak`.

Values that may need calibration with ground truth later:

- `valid_fraction >= 0.90` usability threshold.
- Evidence coverage thresholds based on observation count and gaps.
- `LOW_VEGETATION_FLOOR = 0.18`.
- `MIN_ACTIVITY_AMPLITUDE = 0.08` and `GOOD_ACTIVITY_AMPLITUDE = 0.12`.
- `GOOD_PEAK_THRESHOLD = 0.30`.
- EVI/NDMI/NDWI confirmation thresholds.
- Land-status and trend rules that aggregate activity windows over time.

These values are intentionally conservative for the current satellite-only build. They should not be interpreted as validated crop calendars, crop-stage models, yield models, or regional agronomic truth.
