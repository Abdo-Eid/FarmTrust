# T-03 — Evidence Confidence Gate

## Goal

Implement the rule behind the product diagram point: satellite evidence gaps affect evidence coverage, assessment confidence, or completeness, but do not change land status by themselves.

The outcome should make the backend, API contract, and portal behavior explicit enough that cloud/gap limitations cannot be interpreted as land risk or farmer failure.

## Scope

IN:
- Define executable rules for evidence coverage bands: `good`, `fair`, `limited`, `insufficient`.
- Ensure `land_status` is derived only from observed land signals, not from missing observations alone.
- Ensure `assessment_confidence` is lowered when evidence coverage is weak.
- Define backend behavior for insufficient evidence: incomplete/manual review/provisional status.
- Surface the selected behavior through API fields and portal report UI.
- Add focused tests or fixtures for gap-heavy and insufficient-evidence cases.

OUT:
- New satellite providers or new ingestion sources.
- Redesigning the scoring model beyond evidence/completeness gating.
- Portal visual redesign beyond labels, states, and report handling needed for this rule.
- Production queue/database architecture changes.

## Role Split

- Driver: implement scoring/API/portal behavior and verification fixtures.
- Reviewer: challenge whether any gap/cloud condition still leaks into land status or land risk flags.
- Curator: promote durable policy decisions to `DECISIONS.md` or architecture details to `ENGINEERING.md` only after the behavior is chosen and implemented.

## Chosen Approach

Keep the current separation introduced in the codebase:
- `satellite_evidence_coverage` describes the usable satellite evidence.
- `assessment_confidence` describes reliability of FarmTrust's conclusion.
- `land_status` describes observed land behavior.
- `risk_flags` describe land/farming issues only.

Add a gate after evidence coverage is computed and before final API/report presentation. The gate should not rewrite land status for cloud/gap reasons. It should lower confidence, mark the result incomplete, or require review when evidence is insufficient.

Approved policy:
- Add `assessment_status: complete | manual_review_required`.
- For `insufficient` evidence, use `assessment_status = manual_review_required`.
- For `insufficient` evidence, public API/report must not present a final automated `land_status`, `risk_tier`, `trend_2y`, or `season_performance`.
- Evidence/cloud gaps must never create land/farming risk flags.
- `land_status` remains derived only from observed land signals.
- Confidence caps by evidence coverage:
  - `good`: no cap
  - `fair`: max `medium`
  - `limited`: max `low`
  - `insufficient`: `low`

Evidence coverage thresholds, ordered first match wins:
- `insufficient`: `usable_observation_count < 12`, or `gap_ratio > 0.60`, or `max_gap_days > 90`, or `long_gap_count > 12`.
- `limited`: `usable_observation_count < 30`, or `gap_risk == "high"`, or `gap_ratio > 0.30`, or `max_gap_days > 45`, or `long_gap_count > 6`.
- `fair`: `usable_observation_count < 60`, or `gap_risk == "moderate"`, or `gap_ratio > 0.15`, or `max_gap_days > 10`, or `long_gap_count > 0`.
- `good`: none of the above.

## Task List

- [x] Confirm the exact threshold policy for `good`, `fair`, `limited`, and `insufficient` using existing metrics: `usable_observation_count`, `gap_ratio`, `max_gap_days`, `long_gap_count`, and `gap_risk`.
- [x] Decide insufficient-evidence behavior: no final status, provisional status, or manual review required.
- [x] Update backend scoring so evidence coverage and completeness gates are deterministic and testable.
- [x] Update API schemas/contracts if the chosen behavior needs a field such as `assessment_status`, `review_required`, or `status_provisional`.
- [x] Update portal summary/table/PDF to render the chosen insufficient-evidence state without implying land risk.
- [x] Add focused backend fixtures/tests for good, limited, and insufficient coverage cases.
- [x] Add portal typecheck/build verification after UI contract changes.

## Feedback Log

- 2026-06-17: User asked whether the diagram point should remain; recommendation was to keep and enhance it because it prevents evidence gaps from being treated as land or farmer risk.
- 2026-06-17: User clarified the concern is implementation behind the diagram, not only diagram wording.
- 2026-06-17: User requested a dedicated task for this implementation point.
- 2026-06-17: User approved manual-review-required behavior, explicit `assessment_status`, ordered evidence thresholds, and confidence caps by coverage band.

## Decisions

- Existing policy direction: evidence gaps reduce assessment reliability, not land status by themselves.
- Existing implementation baseline: backend emits `satellite_evidence_coverage`; portal displays it separately from assessment confidence; gap continuity is no longer mapped to land risk flags.
- 2026-06-17: Insufficient evidence uses `assessment_status = manual_review_required`; public API/report suppresses final automated land status, risk tier, trend, and season performance.
- 2026-06-17: Evidence coverage thresholds use ordered first-match rules over usable observation count, gap ratio, max gap days, long gap count, and internal gap risk.
- 2026-06-17: Confidence is capped by evidence coverage: no cap for `good`, max `medium` for `fair`, max `low` for `limited`, and `low` for `insufficient`.

## Open Questions

- Resolved: thresholds are recorded in Chosen Approach.
- Resolved: insufficient evidence returns a manual-review-required result.
- Resolved: API exposes `assessment_status: complete | manual_review_required`.

## Knowledge to Keep

- Missing observations are evidence limitations, not land/farmer risk.
- `land_status` can change only when observed land signals support the change.
- `satellite_evidence_coverage` and `assessment_confidence` should remain separate user-facing concepts.
- Durable threshold and completeness decisions were promoted to `DECISIONS.md`.
- Insufficient evidence suppresses final automated public status, trend, season performance, and risk tier while preserving evidence coverage and assessment confidence context.
- Portal/report wording for manual-review results must not say "no risk" as if a final land-risk assessment was completed.

## Done Summary

- Implemented deterministic evidence coverage thresholds, confidence caps, and `assessment_status`.
- Added manual-review-required handling for insufficient evidence in scoring, API mapping, contracts, portal summary/table/evidence/workbench labels, and PDF output.
- Added backend tests for good, limited, insufficient, and public API manual-review suppression.
- Verification: `uv run python -m unittest discover -s tests` passed; `bun run --cwd E:\projects\FarmTrust\portal typecheck` passed; `bun run --cwd E:\projects\FarmTrust\portal build -- --webpack` passed.
