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

- [x] Polygon ingestion smoke test: run demo AOI as GeoJSON polygon input and confirm output structure.
- [x] Backend E2E: start FastAPI, POST a real land, poll job until `succeeded` or actionable failure, then GET land result.
- [x] Portal E2E: draw polygon, submit, confirm real job ID polling, and verify result page with real assessment data.
- [x] Report-output check: confirm Risk Tier, risk flags, evidence coverage, assessment confidence, and report summary are present when assessment status is complete.
- [x] Manual-review check: confirm insufficient evidence hides final automated land status, trend, season performance, Risk Tier, and land risk flags.
- [x] Language check: confirm current wording stays conservative and does not imply loan approval/rejection.
- [x] Capture any failures with logs and decide whether each is a fix-now bug or a separate follow-up.

### Evidence packet (T-11 Layer 5 — backend artifact)

- [ ] After a real worker run, confirm `data/assessment/<aoi_id>/report_evidence_packet.json` is written during the `report_generation` phase, the job still reaches `succeeded`, and a packet failure only logs `[WARN]` (assessment already saved) instead of failing the job.
- [ ] Validate packet structure: `headline`, `claims[]` (each with `layer`/`confidence`/`rests_on`), `layers` projection matches `claims`, `activity_record`, `track_record` (incl. `provisional`), `risk_register` (split `land_risk`/`evidence_limitation`), `limitations`, `boundaries`, `indicators`, `local_context`.
- [ ] Claim discipline in the packet JSON: no crop identity / yield / income / legal claims outside the fixed `boundaries`; cautious state vocabulary (one good cycle stays `Active — limited history`); `season_calendar_label` is summer/winter only; no monitoring/neighbour section.
- [ ] Determinism: rebuild the packet from the same artifacts and confirm a byte-identical file.
- [ ] Multi-AOI + units: each land in a batch gets its own packet, and `area_feddan` flows from the `Land` record (small-parcel limitation fires below ~0.7 feddan, worded in feddan not hectares).

### Report/UI surface (T-11 Layer 6 — verify when finished)

- [x] API: `GET /lands/{id}/evidence-packet` returns the packet for a completed land, 404s before generation and for an unknown land, and the DTO matches the artifact on disk.
- [x] Portal: the polished HTML/card renders the four layers, the track-record gauge, the split risk register, the boundaries block, and the cautious indicators from the packet — distinct from the PDF export.
- [x] Claim discipline holds in the rendered surface (no crop/yield/loan wording; the `status_so_far` value is always shown inside its provisional framing).
- [x] Edge cases render safely: manual-review, fallow/absence-gated, and limited-history parcels show cautious wording and no false abandonment.

### Bounded report assistant (T-11 Layer 7 / T-04 — verify the grounded path)

- [x] Packet provenance: every claim in `report_evidence_packet.json` carries `claim_type` (∈ the 7-type vocab), `provenance_level` 0–4, `source`, `method`, non-empty `allowed_use`, and a `restriction` (packet `v1.1`); the Layer 6 card still renders unchanged (fields are additive).
- [x] Deterministic fallback (no `AZURE_API_KEY`): `POST /lands/{id}/assistant/narrate` and `.../chat` return `source_mode: "deterministic"`, `fallback_used: true`, fully claim-typed lines, and write one `AssistantMessage` audit row each; the brief never contains crop/yield/loan wording. *(Covered by `tests/test_assistant_service.py`; not re-run live since the key was set.)*
- [x] LLM path (`AZURE_API_KEY` set): narrate returns structured typed lines and chat a bounded answer, both `source_mode: "llm"`; the key is never logged. Grounding is by prompt only (no output guardrail scan). Asking for yield/income or a loan decision is refused; naming a crop the user did NOT provide is refused.
- [x] Expert reasoning: when the user declares the crops/rotation, the assistant treats them as ground truth, maps them onto the activity-record cycles, and reasons about consistency (it has the per-cycle summer/winter timeline + the `api/assistant/knowledge.md` field knowledge). Editing `knowledge.md` changes its reasoning without a restart.
- [x] Rendering: chat renders Markdown (no raw `**`, no inline `[claim_type]` tags); replies follow the user's language; mixed Arabic/English reads correctly (per-paragraph direction, numbers/acronyms not scrambled).
- [x] Portal: the "Report / Ask the assistant" tab on `/lands/[id]/packet` renders narration claim-type pills, the source-mode indicator, suggested chips, and the decision-support disclaimer; mock lands narrate offline; an errored send shows the error bubble (no misleading "Deterministic brief" badge).
- [x] Explanation value vs unsupported claims (carried from T-11): the assistant adds genuine explanation value while refusing unsupported assessment claims (crop identity from satellite alone, yield/income, loan calls) — confirmed in live testing.

## Feedback Log

- 2026-06-16: User chose one follow-up task for the remaining unchecked E2E verification items from the completed backend implementation work.
- 2026-06-27: Product direction clarified: risk assessment first, monitoring second, AI explanation alongside both, data-company expansion later. Current wording such as Risk Tier remains preferred.
- 2026-06-30: Added evidence-packet (T-11 Layer 5) verification items now that the artifact ships, plus a Report/UI (Layer 6) block to run once that surface is built — so the full chain can be validated in one pass when Layer 6 finishes.
- 2026-06-30: Added a Layer 7 (bounded assistant / T-04) verification block now that the assistant ships. Dev-level checks already pass (43 backend tests, portal typecheck + build, live Azure narrate/chat, 4-lens adversarial review); these items are for the full real-worker e2e pass.
- 2026-07-01: User verified on a real land — **core pipeline E2E, the Report-card render block, and the assistant block are all checked off**. The **Evidence-packet (Layer 5) block is intentionally kept open** for a future dedicated real-worker pass (packet-on-disk internals: byte determinism, `[WARN]` non-fatal behavior, multi-AOI/feddan). Also folded in T-11's "compare report/LLM explanation value vs unsupported claims" as a validation item here (confirmed live).

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
