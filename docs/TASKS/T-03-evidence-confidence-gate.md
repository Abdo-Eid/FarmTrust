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

## Task List

- [ ] Confirm the exact threshold policy for `good`, `fair`, `limited`, and `insufficient` using existing metrics: `usable_observation_count`, `gap_ratio`, `max_gap_days`, `long_gap_count`, and `gap_risk`.
- [ ] Decide insufficient-evidence behavior: no final status, provisional status, or manual review required.
- [ ] Update backend scoring so evidence coverage and completeness gates are deterministic and testable.
- [ ] Update API schemas/contracts if the chosen behavior needs a field such as `assessment_status`, `review_required`, or `status_provisional`.
- [ ] Update portal summary/table/PDF to render the chosen insufficient-evidence state without implying land risk.
- [ ] Add focused backend fixtures/tests for good, limited, and insufficient coverage cases.
- [ ] Add portal typecheck/build verification after UI contract changes.

## Feedback Log

- 2026-06-17: User asked whether the diagram point should remain; recommendation was to keep and enhance it because it prevents evidence gaps from being treated as land or farmer risk.
- 2026-06-17: User clarified the concern is implementation behind the diagram, not only diagram wording.
- 2026-06-17: User requested a dedicated task for this implementation point.

## Decisions

- Existing policy direction: evidence gaps reduce assessment reliability, not land status by themselves.
- Existing implementation baseline: backend emits `satellite_evidence_coverage`; portal displays it separately from assessment confidence; gap continuity is no longer mapped to land risk flags.

## Open Questions

- [clarification needed] What exact thresholds define `good`, `fair`, `limited`, and `insufficient` evidence coverage?
- [clarification needed] For `insufficient` evidence, should the backend return no `land_status`, a provisional `land_status`, or a manual-review-required result?
- [clarification needed] Should the API expose assessment completeness as a separate field, for example `assessment_status: complete | provisional | incomplete`, or keep it implicit in `satellite_evidence_coverage` and `assessment_confidence`?

## Knowledge to Keep

- Missing observations are evidence limitations, not land/farmer risk.
- `land_status` can change only when observed land signals support the change.
- `satellite_evidence_coverage` and `assessment_confidence` should remain separate user-facing concepts.
- Durable threshold and completeness decisions should be promoted to canonical docs after implementation.

## Done Summary

- Pending.
