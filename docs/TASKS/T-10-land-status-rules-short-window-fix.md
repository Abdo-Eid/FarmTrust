# T-10 — Land Status Rules: Short-Window & Abandonment Fix

## Links

- PROJECT: §Outputs (what the user sees) | §Current-build scope
- ENGINEERING: §Modeling approach (by output)
- DECISIONS: 2026-06-24 — Pipeline correction — fill+smooth preprocessing, hybrid-threshold activity detection | 2026-06-17 — Insufficient satellite evidence requires manual review

## Goal

Fix the rule-based scoring so that a short assessment window (e.g. 6 months) with one recent healthy season is not classified as `abandonment` or treated as insufficient evidence of activity.

## Scope

### IN

- Diagnose the exact rule path that produces `abandonment` from a short window with one good season.
- Fix `_derive_land_status()` in `farmtrust_core/scoring/rules.py` to account for window length.
- Fix `_derive_risk_flags()` so a recent good activity window suppresses `possible_inactivity` / `abandonment` flags.
- Fix `assessment_mapper.py` so that `possible_inactivity` from a short window does not map to `abandonment`.
- Ensure `trend_2y` correctly returns `uncertain` or `None` when the window is too short for a multi-season trend.
- Update portal rendering to suppress/hide abandonment flags when they derived from short-window inactivity.
- Validate on the user's 6-month dataset.

### OUT

- Changes to agro-phenology calendars (if needed, handled by T-09).
- Changes to ingestion, preprocessing, or seasonal analysis stages.
- Portal UI redesign beyond flag display.
- Changes to the file-based `land_assessment.json` schema without clear rationale.

## Role Split

- Driver: implement rule changes, run validation, capture before/after assessment outputs.
- Reviewer: confirm fix does not break the existing 24-month demo-AOI result.
- Curator: if the fix changes how abandonment is defined, update `ENGINEERING.md` §Modeling approach and add a `DECISIONS.md` entry.

## Chosen Approach

*Proposed; confirm during execution.*

### Root cause path (confirmed)

1. `api/worker.py:133` — `end = date.today()`, `start = end - lookback_days`. A 6-month window produces ~6 months of observations.
2. `rules.py:237` — `_derive_land_status()`: with one recent season and `activity_coverage_fraction < 0.35`, returns `intermittent` (line 256). If `activity_coverage_fraction < 0.18`, returns `inactive` (line 262).
3. `rules.py:545` — `_derive_risk_flags()`: `intermittent` status → `possible_inactivity` (moderate, line 557). `inactive` → `possible_inactivity` (high, line 548).
4. `assessment_mapper.py:57` — `_risk_flags()`: maps `"inactivity"` code to `"abandonment"` API flag.

**Result**: a short window with one good recent season produces `intermittent` + `possible_inactivity` → portal shows `abandonment` flag. This is wrong — a single recent good season in a short window is not abandonment.

### Proposed fix

1. **`_derive_land_status()`**: add a window-length factor. If the assessment interval is less than 12 months, require proportionally less coverage for `active` or allow `unknown / insufficient_history` as an intermediate status instead of `intermittent`.
2. **`_derive_risk_flags()`**: if the latest season has `quality_label == "good"` and is recent (within the last 90 days of the window), suppress `possible_inactivity` flags. A good recent season contradicts inactivity.
3. **`_derive_trend()`**: if less than two complete seasons are available, return `uncertain` instead of forcing `stable`/`declining`/`improving`.
4. **`assessment_mapper.py:_risk_flags()`**: do not map `possible_inactivity` to `abandonment` unless the flag severity is `high` AND the assessment interval is >= 12 months. Short-window inactivity should surface as `insufficient_history` or similar, not `abandonment`.
5. **Portal**: if the only risk flag is `abandonment` derived from a short-window inactivity rule, consider hiding or annotating it with a "not enough history" note.

## Task List

- [ ] Confirm the root cause path by re-reading `rules.py:_derive_land_status()`, `_derive_risk_flags()`, and `assessment_mapper.py:_risk_flags()`.
- [ ] Run the user's 6-month dataset and capture the current `land_assessment.json` output as a before-baseline.
- [ ] Implement fix 1: window-length awareness in `_derive_land_status()`.
- [ ] Implement fix 2: suppress `possible_inactivity` when latest season is good and recent.
- [ ] Implement fix 3: return `uncertain` trend when fewer than 2 seasons exist.
- [ ] Implement fix 4: constrain `possible_inactivity` → `abandonment` mapping to intervals >= 12 months.
- [ ] Implement fix 5: portal display adjustments per chosen approach.
- [ ] Run the user's 6-month dataset again and capture the after-baseline.
- [ ] Run the existing 24-month demo AOI and confirm no regression.
- [ ] Verify all existing tests pass.

## Feedback Log

- 2026-06-28: User validated a 6-month run. One healthy season was detected (recent, good quality) but the system flagged it as `abandonment`. Rule logic treats a single season in a short window as intermittent/inactive and maps inactivity risk to abandonment.

## Decisions

*To be filled.*

## Open Questions

- [clarification needed] What is the minimum window length for a meaningful trend? Current: `_derive_trend` already returns `uncertain` if fewer than 2 seasons exist. This may be the right behavior, but is it surfaced to the user?
- [assumption] `abandonment` should require at least 12 months of evidence showing no recent good activity. Under 12 months, flag should be `insufficient_history` or similar, not `abandonment`.
- [assumption] The current `activity_coverage_fraction` threshold (`>= 0.18` for `intermittent`) is calibrated for a 24-month window. For shorter windows, the denominator shrinks, making the same number of active days look worse than it is.

## Knowledge to Keep

- Abandonment signal path: `_derive_land_status()` → `intermittent`/`inactive` → `_derive_risk_flags()` → `possible_inactivity` → `assessment_mapper.py:_risk_flags()` → `abandonment`.
- The mapper (`assessment_mapper.py:57-58`) matches `"inactivity"` substring, so both `possible_inactivity` and any future inactivity-like codes land on `abandonment`. This is too aggressive.
- `api/schemas.py:82` — flags enum includes `abandonment` as a valid literal. Changing this requires a contract update.
- The window length is available in `land.lookback_days` (API) and in `run_metadata` (pipeline artifact). Both can be accessed from scoring.

## Done Summary

- Pending.
