# T-03 — Monitoring Layer

## Goal

Plan and implement the first monitoring layer that starts after a land has a completed risk assessment report.

Monitoring should extend lender confidence over time by re-checking the same land, comparing new evidence against the previous report, and surfacing material changes. It must remain secondary to the initial farm risk report: the first sellable output is still the risk assessment; monitoring is the follow-up workflow.

## Scope

IN:
- Define the first monitoring lifecycle for completed lands: not monitored, monitoring, needs review, and monitoring failed if needed.
- Define what counts as a material monitoring change using existing outputs: land status, 2-year trend, last activity window, risk tier, land risk flags, satellite evidence coverage, and assessment confidence.
- Add a minimal backend path to start a monitoring run for an existing land using its stored polygon and the existing worker/pipeline path.
- Store monitoring run results and change events with enough context for portal display and report history.
- Add portal surfaces for monitoring state, latest monitoring result, and material change events without redesigning the core UI.
- Add tests or smoke checks for monitoring run creation, polling, result comparison, and portal rendering.

OUT:
- Scheduled monitoring jobs, cron infrastructure, or background queue/broker integration.
- Email, SMS, WhatsApp, or push notification delivery.
- Portfolio-wide alert dashboards beyond a minimal land-level monitoring view.
- New satellite sources or SAR/thermal fusion.
- AI-generated monitoring explanations; that belongs to T-04.
- Automated loan approval, rejection, or repayment prediction.

## Role Split

- Driver: define monitoring contract, implement backend/API/portal path, and verify the flow end to end.
- Reviewer: check that monitoring changes are conservative, evidence-grounded, and do not confuse evidence gaps with land risk.
- Curator: update `PROJECT.md`, `ENGINEERING.md`, or `DECISIONS.md` only if the implementation creates durable product or architecture truth.

## Chosen approach

Use on-demand monitoring first.

The first version should let a user trigger a monitoring run for a completed land. The backend reuses the stored geometry and existing pipeline worker, maps the new assessment into the existing result DTO, then compares the new result to the previous completed result. The portal shows the latest monitoring state and any material changes.

This avoids scheduler and notification complexity while proving the product flow: initial report first, monitoring after.

## Task List

- [ ] Planning: confirm monitoring means post-assessment reassessment, not a replacement for the first risk report.
- [ ] Planning: define monitoring states and material-change rules.
- [ ] Planning: decide whether the first monitoring run uses a fresh live satellite pull, cached/local fixture, or both for demo resilience.
- [ ] Planning: define API shape for starting and reading monitoring runs.
- [ ] Backend: add persistence for monitoring runs/events or a minimal equivalent tied to existing lands/jobs.
- [ ] Backend: add endpoint to start a monitoring run for an existing land.
- [ ] Backend: compare previous and new assessment results into conservative change events.
- [ ] Backend: ensure manual-review and insufficient-evidence results do not create false land-risk alerts.
- [ ] Portal: expose monitoring state on the land detail or summary page.
- [ ] Portal: show latest monitoring event with previous/current values and confidence/evidence notes.
- [ ] Portal: preserve current risk-report wording such as Land Status, 2-Year Trend, Last Activity Window, and Risk Tier.
- [ ] Verification: run backend tests or add targeted tests for monitoring comparison logic.
- [ ] Verification: run a smoke E2E path from completed land to monitoring run to updated portal output.
- [ ] Documentation: promote durable API/architecture details only after the code path is chosen and verified.

## Feedback Log

- 2026-06-27: Direction from pitch is risk assessment first, monitoring second, AI alongside both, data-company expansion later.
- 2026-06-27: Current UI/report wording should remain conservative; do not rename Risk Tier to Credit-Readiness Tier.

## Decisions

- [assumption] First monitoring implementation is on-demand, not scheduled.
- [assumption] Monitoring uses existing land assessment outputs before introducing new monitoring-only signals.
- [assumption] Material changes must be conservative and evidence-aware; weak satellite coverage lowers confidence instead of becoming a land-risk alert.

## Open Questions

- [clarification needed] Should a cached/local fixture monitoring run count as demo acceptance if Planetary Computer is slow or unavailable?
- [clarification needed] What exact changes should create a monitoring event: any risk tier change, only worsening changes, new flags, confidence drops, or all of these?
- [clarification needed] Should a monitoring run recompute the full 24-month window or append/check only the newest available scenes?
- [clarification needed] Should monitoring results overwrite the current land summary, or remain as separate report history with the latest result highlighted?

## Knowledge to Keep

- Product truth to promote later: monitoring is a follow-up layer after the first risk report, not the primary product.
- Engineering truth to promote later: selected monitoring endpoints, persistence model, and comparison rules.
- Decision truth to promote later: whether monitoring is on-demand only for the current build or committed as a scheduled product capability.

## Done Summary

- Pending.
