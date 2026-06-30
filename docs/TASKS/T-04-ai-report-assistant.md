# T-04 — Grounded AI Report Assistant

## Goal

Plan and implement the grounded AI assistant layer for FarmTrust reports: on-demand report narration plus a bounded analyst/chat interface over FarmTrust evidence.

The assistant should help users understand existing evidence, visuals, score reasons, confidence notes, local context, and report limitations. It can answer user questions as a bounded analyst over the FarmTrust evidence packet and supporting data. It must not create the assessment, change scores, silently override deterministic outputs, infer unsupported facts, or behave like an automated loan decision engine.

## Scope

IN:
- Define an AI input packet built only from existing report/assessment data: land metadata, land status, trend, season performance, risk tier, flags, evidence coverage, assessment confidence, chart summaries, report summary, and monitoring events when available.
- Consume the T-11 grounded evidence packet/report data when available: Observed, Interpreted, Confidence, Watch, Limitations, local context, boundaries, track record, risk/watch register, and per-claim confidence.
- Define supported audiences for explanation tone: lender first, with investor, farmer, and cooperative language as optional follow-ups.
- Add a backend service boundary for grounded report narration and bounded analyst/chat over FarmTrust-owned evidence.
- Add provider/config handling only if an LLM provider is selected; otherwise use a deterministic brief composer as the first safe implementation path.
- Add a portal surface for report narration and a bounded chat/explanation panel near the report/summary flow.
- Add guardrails and tests that prevent unsupported claims, loan approval language, exact yield claims, pest diagnosis, and evidence fabrication.
- Add claim typing in responses: measured evidence, deterministic pipeline result, user-provided/local context, hypothesis, or unknown.
- Use `outputs/exploration/AI_ASS~1.HTM` as the current assistant feature-design reference for UX, flow, rollout, and wording boundaries.

OUT:
- AI-generated risk scoring or changes to pipeline assessment results.
- Automated financing approval, rejection, or loan recommendation.
- Open-ended chatbot over arbitrary user-uploaded documents or external content not represented in the FarmTrust evidence packet.
- Raw satellite-image interpretation by the LLM.
- Crop type, yield, pest, or legal survey claims.
- Data-company analytics or model training from assistant conversations.

## Role Split

- Driver: define assistant contract, implement backend/portal integration, and verify grounded outputs.
- Reviewer: challenge hallucination risk, unsupported language, role-specific wording, and lender-safety guardrails.
- Curator: promote durable assistant boundaries and provider decisions into canonical docs only after implementation choices are confirmed.

## Chosen approach

Use a grounded packet-first assistant. The shipped assistant surface includes on-demand report narration and bounded analyst/chat, but both must be constrained by the same FarmTrust evidence packet, claim typing, and guardrail tests.

The first implementation should generate grounded narration from the report/evidence DTO and expose bounded follow-up Q&A over the same packet. It should cite or reference the specific fields it used and include confidence/evidence limitations. Chat can analyze and connect observations with local context, but it must label hypotheses and unknowns instead of presenting them as facts.

If no LLM provider is configured, the system should still produce a deterministic report brief from the same evidence packet. This keeps the report stable and prevents the assistant from becoming a dependency for the core risk-report workflow.

Design reference: `outputs/exploration/AI_ASS~1.HTM`.

Key principles from the design reference:

- Free to ask, bounded in what the assistant may assert.
- Deterministic pipeline -> evidence packet -> read-only AI narrator/analyst -> report + chat.
- Local context can inform reasoning, but remains context, not automatic truth.
- Assistant lives beside the deterministic report, never in place of it.
- Every generated line should expose claim type and source/reference.
- Unsupported answers fall back to the plain deterministic summary.
- Every generated surface carries decision-support wording, not loan-decision wording.
- V1 target: on-demand narration plus bounded analyst chat, English, lender audience.

## Task List

- [ ] Planning: define exact assistant purpose: explain evidence, not create evidence.
- [ ] Planning: choose first user role for implementation; default recommendation is lender.
- [ ] Planning: define AI input packet fields and excluded fields.
- [ ] Planning: define forbidden language and required disclaimers.
- [ ] Planning: align with T-11 evidence packet fields and local-context document.
- [ ] Planning: translate `outputs/exploration/AI_ASS~1.HTM` into implementation requirements for UX, claim typing, fallback, and rollout.
- [ ] Planning: define claim-type schema for measured evidence, deterministic output, user/local context, hypothesis, and unknown.
- [ ] Planning: define bounded chat scope: FarmTrust report/evidence only; no arbitrary uploads or unsupported raw satellite interpretation.
- [ ] Planning: decide provider/config and deterministic fallback behavior for report narration and chat.
- [ ] Backend: add assistant request/response schemas or internal DTOs.
- [ ] Backend: add service that builds the grounded evidence packet from an existing land/report result.
- [ ] Backend: add deterministic brief composer and/or LLM adapter behind explicit configuration.
- [ ] Backend: add endpoint for report narration if needed by the portal.
- [ ] Backend: add endpoint for bounded report chat if needed by the portal.
- [ ] Backend: add tests for manual-review, low-confidence, high-risk, and no-risk examples.
- [ ] Backend: add ship-blocking guardrail tests for crop identity, yield, pest diagnosis, financing decision, legal/survey claims, fabricated evidence, hidden uncertainty, and untyped hypotheses.
- [ ] Portal: add an AI brief/explanation panel without changing current Risk Tier wording.
- [ ] Portal: add bounded chat UI connected to current report/evidence context.
- [ ] Portal: show evidence limitations and decision-support disclaimer near generated text.
- [ ] Portal: show claim types or citations/references enough for users to see why the assistant said something.
- [ ] Verification: run typecheck/tests for API and portal changes.
- [ ] Verification: review generated text against forbidden claims and pitch-safe positioning.
- [ ] Verification: require guardrail tests to pass before assistant/chat ships.
- [ ] Documentation: promote durable provider/config/guardrail choices only after the first implementation is selected.

## Feedback Log

- 2026-06-27: Direction from pitch is that AI supports risk reports and monitoring; AI is not the product by itself.
- 2026-06-27: Current app wording should stay conservative; do not rename Risk Tier to Credit-Readiness Tier.
- 2026-06-29: T-11 audit follow-up migrated assistant/chat implementation ownership here. User confirmed bounded analyst/chat is intended to ship, not remain only a future idea, but it must consume grounded FarmTrust evidence and preserve claim boundaries.
- 2026-06-29: User provided `outputs/exploration/AI_ASS~1.HTM` as the current AI assistant feature-design artifact. It defines the intended UX: on-demand narration, bounded analyst chat, every sentence sourced/typed, local context as context only, deterministic fallback, and decision-support disclaimers.

## Decisions

- [decision] Assistant scope includes on-demand report narration and bounded analyst/chat over FarmTrust evidence. It is not a chatbot over arbitrary documents or unsupported external content.
- [decision] The assistant consumes existing FarmTrust evidence and T-11 packet fields; it must not invent new assessment facts, change scores, or override deterministic pipeline outputs.
- [decision] The core report remains usable without the assistant through deterministic packet/report rendering.
- [decision] Guardrail tests are ship-blocking for assistant/chat: unsupported crop identity, yield, pest diagnosis, financing decision, legal/survey claims, fabricated evidence, hidden uncertainty, and untyped hypotheses must be blocked or labelled safely before release.
- [decision] Use `outputs/exploration/AI_ASS~1.HTM` as the assistant UX/design reference for V1 unless superseded by a later approved design. The design's core rule is: users may ask freely, but the assistant is bounded in what it may assert.

## Open Questions

- [clarification needed] Which LLM provider should be used, if any, and how should credentials be configured?
- [clarification needed] Should the first version support English only, Arabic only, or both?
- [clarification needed] Should generated briefs be stored with reports or generated on demand each time?
- [answered] Should follow-up questions be included in the first version, or deferred until generated briefs are validated? Include bounded report chat/follow-up questions as a shipped assistant surface, gated by evidence-packet readiness and guardrail tests.
- [clarification needed] Which audiences matter for the first build: lender only, or lender plus farmer/investor/cooperative variants?

## Knowledge to Keep

- Product truth to promote later: AI explains report evidence and monitoring changes; it does not create risk evidence.
- Engineering truth to promote later: evidence-packet contract, provider boundary, endpoint shape, and fallback behavior.
- Decision truth to promote later: selected provider, storage policy, supported languages, claim typing, and bounded chat scope.
- T-11 owns pipeline/report-packet readiness. T-04 owns assistant narration, bounded analyst/chat, provider integration, and guardrail tests.
- `outputs/exploration/AI_ASS~1.HTM` is the current assistant design reference. Preserve its constraints during implementation: downstream-only AI, works without AI, every sentence sourced/typed, local context is not automatic truth, guardrails enforced in code/tests, and decision-support wording on generated surfaces.

## Done Summary

- Pending.
