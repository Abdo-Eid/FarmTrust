# T-04 — Grounded AI Report Assistant

## Goal

Plan and implement the first grounded AI assistant layer for explaining FarmTrust reports and monitoring evidence.

The assistant should help users understand existing evidence, visuals, score reasons, confidence notes, and monitoring changes. It must not create the assessment, change scores, infer unsupported facts, or behave like an automated loan decision engine.

## Scope

IN:
- Define an AI input packet built only from existing report/assessment data: land metadata, land status, trend, season performance, risk tier, flags, evidence coverage, assessment confidence, chart summaries, report summary, and monitoring events when available.
- Define supported audiences for explanation tone: lender first, with investor, farmer, and cooperative language as optional follow-ups.
- Add a backend service boundary for grounded report briefs and follow-up explanations.
- Add provider/config handling only if an LLM provider is selected; otherwise use a deterministic brief composer as the first safe implementation path.
- Add a portal surface for an AI brief or explanation panel near the report/summary flow.
- Add guardrails and tests that prevent unsupported claims, loan approval language, exact yield claims, pest diagnosis, and evidence fabrication.

OUT:
- AI-generated risk scoring or changes to pipeline assessment results.
- Automated financing approval, rejection, or loan recommendation.
- Open-ended chatbot over arbitrary user-uploaded documents.
- Raw satellite-image interpretation by the LLM.
- Crop type, yield, pest, or legal survey claims.
- Data-company analytics or model training from assistant conversations.

## Role Split

- Driver: define assistant contract, implement backend/portal integration, and verify grounded outputs.
- Reviewer: challenge hallucination risk, unsupported language, role-specific wording, and lender-safety guardrails.
- Curator: promote durable assistant boundaries and provider decisions into canonical docs only after implementation choices are confirmed.

## Chosen approach

Use a brief-first assistant, not an open chatbot first.

The first implementation should generate a grounded explanation from the existing report DTO. It should cite or reference the specific fields it used and include confidence/evidence limitations. Follow-up Q&A can come after the brief contract is safe.

If no LLM provider is configured, the system should still produce a deterministic report brief from the same evidence packet. This keeps the demo stable and prevents the assistant from becoming a dependency for the core risk-report workflow.

## Task List

- [ ] Planning: define exact assistant purpose: explain evidence, not create evidence.
- [ ] Planning: choose first user role for implementation; default recommendation is lender.
- [ ] Planning: define AI input packet fields and excluded fields.
- [ ] Planning: define forbidden language and required disclaimers.
- [ ] Planning: decide whether first version is deterministic brief only, LLM-backed brief, or deterministic fallback plus optional LLM.
- [ ] Backend: add assistant request/response schemas or internal DTOs.
- [ ] Backend: add service that builds the grounded evidence packet from an existing land/report result.
- [ ] Backend: add deterministic brief composer and/or LLM adapter behind explicit configuration.
- [ ] Backend: add endpoint for report brief generation if needed by the portal.
- [ ] Backend: add tests for manual-review, low-confidence, high-risk, and no-risk examples.
- [ ] Portal: add an AI brief/explanation panel without changing current Risk Tier wording.
- [ ] Portal: show evidence limitations and decision-support disclaimer near generated text.
- [ ] Verification: run typecheck/tests for API and portal changes.
- [ ] Verification: review generated text against forbidden claims and pitch-safe positioning.
- [ ] Documentation: promote durable provider/config/guardrail choices only after the first implementation is selected.

## Feedback Log

- 2026-06-27: Direction from pitch is that AI supports risk reports and monitoring; AI is not the product by itself.
- 2026-06-27: Current app wording should stay conservative; do not rename Risk Tier to Credit-Readiness Tier.

## Decisions

- [assumption] First assistant surface is a grounded report brief, not a general chatbot.
- [assumption] The assistant consumes existing FarmTrust evidence and must not invent new assessment facts.
- [assumption] The core report remains usable without the assistant.

## Open Questions

- [clarification needed] Which LLM provider should be used, if any, and how should credentials be configured?
- [clarification needed] Should the first version support English only, Arabic only, or both?
- [clarification needed] Should generated briefs be stored with reports or generated on demand each time?
- [clarification needed] Should follow-up questions be included in the first version, or deferred until generated briefs are validated?
- [clarification needed] Which audiences matter for the first build: lender only, or lender plus farmer/investor/cooperative variants?

## Knowledge to Keep

- Product truth to promote later: AI explains report evidence and monitoring changes; it does not create risk evidence.
- Engineering truth to promote later: evidence-packet contract, provider boundary, endpoint shape, and fallback behavior.
- Decision truth to promote later: selected provider, storage policy, supported languages, and whether chat is in scope.

## Done Summary

- Pending.
