# P-02 — End-to-End Validation

## Goal

Validate that the current-build polygon submission path works from portal input through FastAPI, background worker execution, pipeline artifacts, job polling, and final land result rendering.

## Scope

IN:
- Smoke-test polygon ingestion using the demo AOI converted to GeoJSON polygon input.
- Submit a real land through FastAPI, poll the job until completion, and fetch the result.
- Verify portal polygon draw submission returns a real job and reaches a result page.
- Record verification commands, results, failures, and fixes needed.

OUT:
- New backend features.
- Queue/broker integration.
- Production database migration.
- UI redesign beyond fixes required to complete validation.

## Role Split

- Driver: run the E2E paths and capture failures.
- Reviewer: confirm outputs match contracts and expected user flow.
- Curator: promote durable findings into `ENGINEERING.md` or `DECISIONS.md` only if they change shared truth.

## Chosen Approach

Run one focused validation pass using existing current-build architecture: portal routes proxy real submissions to FastAPI, FastAPI launches the direct worker path, and the worker produces `land_assessment.json` for mapped API responses.

## Build Plan

- [ ] Polygon ingestion smoke test: run demo AOI as GeoJSON polygon input and confirm output structure.
- [ ] Backend E2E: start FastAPI, POST a real land, poll job until `succeeded` or actionable failure, then GET land result.
- [ ] Portal E2E: draw polygon, submit, confirm real job ID polling, and verify result page with real assessment data.
- [ ] Capture any failures with logs and decide whether each is a fix-now bug or a separate follow-up.

## Feedback Log

- 2026-06-16: User chose one follow-up plan for the remaining unchecked E2E verification items from the completed backend implementation work.

## Decisions

- Backend implementation work is closed; remaining unchecked work is validation-only and tracked here.

## Open Questions

- [clarification needed] If Planetary Computer is slow or unavailable during validation, should a cached/local fixture path count as partial acceptance or should validation wait for a live run?

## Knowledge to Keep

- Current-build architecture diagram lives in `ENGINEERING.md`; this plan should not duplicate long-lived architecture truth.
- `OPEN_ITEMS.md` is for unresolved questions/decisions, not unchecked implementation tasks.

## Done Summary

- Pending.
