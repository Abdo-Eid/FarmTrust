# T-02 — End-to-End Validation

## Goal

Validate that the current-build lender-facing risk-report flow works from portal polygon input through FastAPI, background worker execution, pipeline artifacts, job polling, and final land result/report rendering.

## Scope

IN:
- Smoke-test polygon ingestion using the demo AOI converted to GeoJSON polygon input.
- Submit a real land through FastAPI, poll the job until completion, and fetch the result.
- Verify portal polygon draw submission returns a real job and reaches a result page.
- Verify the result presents current risk-report outputs: Land Status, 2-Year Trend, Last Activity Window, Risk Tier, land risk flags, satellite evidence coverage, and assessment confidence.
- Verify confidence/evidence limitations stay separate from land risk and do not read as automated loan approval.
- Record verification commands, results, failures, and fixes needed.

OUT:
- New backend features.
- Queue/broker integration.
- Production database migration.
- UI redesign beyond fixes required to complete validation.
- Monitoring-layer implementation.
- AI assistant implementation.

## Role Split

- Driver: run the E2E paths and capture failures.
- Reviewer: confirm outputs match contracts and expected user flow.
- Curator: promote durable findings into `ENGINEERING.md` or `DECISIONS.md` only if they change shared truth.

## Chosen Approach

Run one focused validation pass using existing current-build architecture: portal routes proxy real submissions to FastAPI, FastAPI launches the direct worker path, and the worker produces `land_assessment.json` for mapped API/report responses.

The validation target is the first-product anchor: a conservative farm risk report that supports lender review. Monitoring and AI are follow-up layers, not blockers for this E2E task.

## Task List

- [ ] Polygon ingestion smoke test: run demo AOI as GeoJSON polygon input and confirm output structure.
- [ ] Backend E2E: start FastAPI, POST a real land, poll job until `succeeded` or actionable failure, then GET land result.
- [ ] Portal E2E: draw polygon, submit, confirm real job ID polling, and verify result page with real assessment data.
- [ ] Report-output check: confirm Risk Tier, risk flags, evidence coverage, assessment confidence, and report summary are present when assessment status is complete.
- [ ] Manual-review check: confirm insufficient evidence hides final automated land status, trend, season performance, Risk Tier, and land risk flags.
- [ ] Language check: confirm current wording stays conservative and does not imply loan approval/rejection.
- [ ] Capture any failures with logs and decide whether each is a fix-now bug or a separate follow-up.

### Evidence packet (T-11 Layer 5 — backend artifact)

- [ ] After a real worker run, confirm `data/assessment/<aoi_id>/report_evidence_packet.json` is written during the `report_generation` phase, the job still reaches `succeeded`, and a packet failure only logs `[WARN]` (assessment already saved) instead of failing the job.
- [ ] Validate packet structure: `headline`, `claims[]` (each with `layer`/`confidence`/`rests_on`), `layers` projection matches `claims`, `activity_record`, `track_record` (incl. `provisional`), `risk_register` (split `land_risk`/`evidence_limitation`), `limitations`, `boundaries`, `indicators`, `local_context`.
- [ ] Claim discipline in the packet JSON: no crop identity / yield / income / legal claims outside the fixed `boundaries`; cautious state vocabulary (one good cycle stays `Active — limited history`); `season_calendar_label` is summer/winter only; no monitoring/neighbour section.
- [ ] Determinism: rebuild the packet from the same artifacts and confirm a byte-identical file.
- [ ] Multi-AOI + units: each land in a batch gets its own packet, and `area_feddan` flows from the `Land` record (small-parcel limitation fires below ~0.7 feddan, worded in feddan not hectares).

### Report/UI surface (T-11 Layer 6 — verify when finished)

- [ ] API: `GET /lands/{id}/evidence-packet` returns the packet for a completed land, 404s before generation and for an unknown land, and the DTO matches the artifact on disk.
- [ ] Portal: the polished HTML/card renders the four layers, the track-record gauge, the split risk register, the boundaries block, and the cautious indicators from the packet — distinct from the PDF export.
- [ ] Claim discipline holds in the rendered surface (no crop/yield/loan wording; the `status_so_far` value is always shown inside its provisional framing).
- [ ] Edge cases render safely: manual-review, fallow/absence-gated, and limited-history parcels show cautious wording and no false abandonment.

## Feedback Log

- 2026-06-16: User chose one follow-up task for the remaining unchecked E2E verification items from the completed backend implementation work.
- 2026-06-27: Product direction clarified: risk assessment first, monitoring second, AI explanation alongside both, data-company expansion later. Current wording such as Risk Tier remains preferred.
- 2026-06-30: Added evidence-packet (T-11 Layer 5) verification items now that the artifact ships, plus a Report/UI (Layer 6) block to run once that surface is built — so the full chain can be validated in one pass when Layer 6 finishes.

## Decisions

- Backend implementation work is closed; remaining unchecked work is validation-only and tracked here.
- This task validates the current risk-report product anchor; monitoring and AI feature work are separate follow-up tasks.

## Open Questions

- [clarification needed] If Planetary Computer is slow or unavailable during validation, should a cached/local fixture path count as partial acceptance or should validation wait for a live run?

## Knowledge to Keep

- Current-build architecture diagram lives in `ENGINEERING.md`; this task should not duplicate long-lived architecture truth.
- `OPEN_ITEMS.md` is for unresolved questions/decisions, not unchecked implementation tasks.

## Done Summary

- Pending.
