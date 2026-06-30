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

- [x] Planning: define exact assistant purpose: explain evidence, not create evidence.
- [x] Planning: choose first user role for implementation; default recommendation is lender.
- [x] Planning: define AI input packet fields and excluded fields.
- [x] Planning: define forbidden language and required disclaimers.
- [x] Planning: align with T-11 evidence packet fields and local-context document.
- [x] Planning: translate `outputs/exploration/AI_ASS~1.HTM` into implementation requirements for UX, claim typing, fallback, and rollout.
- [x] Planning: define claim-type schema for measured evidence, deterministic output, user/local context, hypothesis, and unknown.
- [x] Planning: define bounded chat scope: FarmTrust report/evidence only; no arbitrary uploads or unsupported raw satellite interpretation.
- [x] Planning: decide provider/config and deterministic fallback behavior for report narration and chat.
- [x] Backend: add assistant request/response schemas or internal DTOs. (`AssistantLine/AssistantResponse/ChatRequest` in `api/schemas.py`.)
- [x] Backend: add service that builds the grounded evidence packet from an existing land/report result. (`api/assistant/service.py` loads the packet via `report_evidence_packet_path`.)
- [x] Backend: add deterministic brief composer and/or LLM adapter behind explicit configuration. (`farmtrust_core/report/brief.py` + `api/assistant/{config,prompt,llm,guardrails}.py`.)
- [x] Backend: add endpoint for report narration if needed by the portal. (`POST /lands/{id}/assistant/narrate`.)
- [x] Backend: add endpoint for bounded report chat if needed by the portal. (`POST /lands/{id}/assistant/chat`.)
- [x] Backend: add tests for manual-review, low-confidence, high-risk, and no-risk examples. (`tests/test_assistant_*.py` + packet cases.)
- [~] Backend: add ship-blocking guardrail tests for crop identity, yield, pest diagnosis, financing decision, legal/survey claims, fabricated evidence, hidden uncertainty, and untyped hypotheses. **V1 ships the LIGHT scan** (`api/assistant/guardrails.py`, `tests/test_assistant_guardrails.py`); the heavy code-enforced per-line validator is a deferred pre-production follow-up (see Decisions).
- [x] Portal: add an AI brief/explanation panel without changing current Risk Tier wording. (`components/assistant/AssistantPanel.tsx`.)
- [x] Portal: add bounded chat UI connected to current report/evidence context. (tabbed onto `/lands/[id]/packet`.)
- [x] Portal: show evidence limitations and decision-support disclaimer near generated text.
- [x] Portal: show claim types or citations/references enough for users to see why the assistant said something. (per-line claim-type pills + source.)
- [x] Verification: run typecheck/tests for API and portal changes.
- [x] Verification: review generated text against forbidden claims and pitch-safe positioning. (4-lens adversarial review; 6 fixes applied.)
- [~] Verification: require guardrail tests to pass before assistant/chat ships. (Light-scan guardrail tests pass and gate V1; the heavy validator gate is deferred to pre-production.)
- [x] Documentation: promote durable provider/config/guardrail choices only after the first implementation is selected.

## Implementation Plan (V1) — approved 2026-06-30

Deterministic-first, packet-grounded. The assistant works fully with no LLM (a deterministic brief is the always-on narration and the fallback); the Azure LLM is layered on top with the brief as automatic fallback. Implementation is a coordinated pass after this plan — not yet started.

### Part A — Packet provenance enrichment (foundation)

T-11 specifies a per-claim metadata schema deferred from Layer 5. Add it in `farmtrust_core/report/evidence_packet.py` as a **post-pass** over the already-built claims (avoids touching the ~14 `_claim()` call sites):

- `_apply_provenance(claims)`: attach `claim_type`, `provenance_level`, `source`, `method`, `allowed_use`, `restriction` from a `CLAIM_PROVENANCE` table keyed by claim id, with per-layer defaults and dynamic handling for `watch_<code>` ids. Mapping: detector outputs → `deterministic_pipeline_result` / L4; curve-derived (lifecycle, calendar, intensity) → `model_derived_analysis` / L4; coverage → `measured_observation` / L4; `allowed_use=["report","chat","status_explanation"]`; `restriction="do_not_infer_crop_identity_or_yield"` (yield lines → `yield_not_observable`). `confidence` already exists.
- Bump `PACKET_VERSION` → `"1.1"` (additive, backward-compatible). Carry the 6 fields onto `PacketClaim` in `api/schemas.py` + `portal/src/lib/types.ts` as optional (Layer 6 card ignores them).
- Extend `tests/test_report_evidence_packet.py`: every claim has valid `claim_type` (7-type vocab), `provenance_level` ∈ 0–4, non-empty `allowed_use`, a `restriction`.

### Part B — Deterministic brief + assistant service (backend)

- `farmtrust_core/report/brief.py` (new, pure): `build_deterministic_brief(packet) -> list[BriefLine]` — narrates headline → key claims → boundaries, each line `{text, claim_type, source, confidence}`, reusing the packet's wording. The no-LLM narration AND the fallback.
- `api/assistant/` package (new):
  - `config.py` — `AZURE_API_KEY`, `AZURE_OPENAI_ENDPOINT` (default `https://enova-ai-3080-resource.services.ai.azure.com`), `AZURE_OPENAI_DEPLOYMENT` (`gpt-4o`), `AZURE_OPENAI_API_VERSION` (`2024-02-15-preview`) via `os.environ.get`; `is_llm_configured()` true only when `AZURE_API_KEY` set.
  - `prompt.py` — `PROMPT_VERSION` + grounded system prompt from the packet (typed claims, boundaries, claim-type rules, labelled local-context from `docs/documentations/05-local-interpretation-context.md` marked `user_provided_local_context`). Rules: answer only from the packet, tag every line, say `unknown` if absent, never loan/yield/crop/pest.
  - `llm.py` — one lazy `langchain_openai.AzureChatOpenAI` (temperature 0). `narrate(packet)` → `.with_structured_output(NarrationSchema).invoke([...])` (typed lines); `answer(packet, question, history)` → `.invoke([...])` (free-form). Hybrid output: JSON-structured for narration, free-form for chat. On missing config / any error → `None` (caller falls back). LangChain isolated to this file.
  - `guardrails.py` (light) — `check(text)` forbidden-phrase scan (loan approve/reject/recommend; yield/income/price assertions; crop names reusing the Layer-5 token set; pest/disease). Fail → deterministic-brief fallback.
  - `service.py` — load packet via `report_evidence_packet_path` + `_load_json`, `packet_hash = sha256(bytes)`; LLM-if-configured → prompt → llm → guardrail; pass → LLM (`source_mode="llm"`), else deterministic brief (`fallback_used=true`). Persist an `AssistantMessage`. Return the structured response.
- `api/routers/assistant.py` (new): `POST /lands/{land_id}/assistant/narrate` + `.../chat` (`{question, history?}`); 404 if land/packet missing. Register in `api/main.py`.
- `api/schemas.py`: `AssistantLine`, `AssistantResponse {lines[], source_mode, fallback_used, model?, guardrail?}`, `ChatRequest`.
- `api/models.py`: `AssistantMessage` table `{id, land_id, aoi_id, kind, question?, response_text, source_mode, model_name?, prompt_version, packet_hash, guardrail_result, created_at}`; add column-create in `database.py::_migrate_db()`.
- `pyproject.toml`: add `langchain-openai` (pulls `langchain-core`). Install with `uv add langchain-openai` or edit + `uv sync --extra ml --extra data` (never sync with one extra — it prunes the other).

### Part C — Portal assistant tab

- `lib/types.ts` (assistant types + optional `PacketClaim` provenance fields), `lib/api.ts` (`api.assistant.narrate/chat`), Next proxies `app/api/lands/[id]/assistant/{narrate,chat}/route.ts`, `hooks/useAssistant.ts`.
- `components/assistant/AssistantPanel.tsx` — message list, claim-type tag Badges (measured=green, deterministic=teal, model_derived=indigo, local=slate, hypothesis=amber, unknown=gray), the 3 suggested-question chips, `Textarea`+send, "Narrate this report" action, `source_mode` indicator, decision-support disclaimer. Matches the `EvidencePacketReport` idiom.
- `app/(portal)/lands/[id]/packet/page.tsx` — wrap `EvidencePacketReport` + `AssistantPanel` in Radix `Tabs` ("Report" / "Ask the assistant"); both consume the existing `useEvidencePacket(id)`.

### Part D — Tests

- Extend the packet test (provenance fields); `tests/test_assistant_brief.py` (structure, every line typed, no crop/yield outside boundaries, determinism); `tests/test_assistant_guardrails.py` (forbidden phrases flagged, safe text passes); `tests/test_assistant_service.py` (monkeypatch llm — no live Azure; guardrail + persistence + response shape; clean fallback when unconfigured). Portal `tsc` + `next build`.

### Verification

- pytest (packet + assistant suites) green; scratch end-to-end with the LLM unconfigured → deterministic, typed, claim-disciplined response + an `AssistantMessage` row; portal typecheck + build clean. Live Azure path is config-gated (set `AZURE_*` to exercise; not in CI). Adversarial review pass after implementation.

### Out of scope (flagged)

- Heavy code-enforced per-line guardrail validator (T-04 ship-blocking, see decision below) — deferred per user; must precede production.
- Streaming; Arabic and farmer/investor/cooperative tones; monitoring/neighbour context (the design's "later").

## Feedback Log

- 2026-06-27: Direction from pitch is that AI supports risk reports and monitoring; AI is not the product by itself.
- 2026-06-27: Current app wording should stay conservative; do not rename Risk Tier to Credit-Readiness Tier.
- 2026-06-29: T-11 audit follow-up migrated assistant/chat implementation ownership here. User confirmed bounded analyst/chat is intended to ship, not remain only a future idea, but it must consume grounded FarmTrust evidence and preserve claim boundaries.
- 2026-06-29: User provided `outputs/exploration/AI_ASS~1.HTM` as the current AI assistant feature-design artifact. It defines the intended UX: on-demand narration, bounded analyst chat, every sentence sourced/typed, local context as context only, deterministic fallback, and decision-support disclaimers.
- 2026-06-30: V1 implementation plan agreed and recorded (see "Implementation Plan (V1)"). User decided: LLM = their Azure AI Services `gpt-4o` via `langchain-openai` `AzureChatOpenAI` (not Anthropic/openai-SDK), reusing their working config; hybrid typed output (JSON-structured narration, free-form chat); persist assistant messages; tab UI on the packet page; English + lender V1; non-streaming. User opted to keep guardrails light for now ("may not need guardrails now") — the heavy code-enforced validator is deferred as a pre-production follow-up. API key pasted into repo-root `.env` (gitignored). Implementation deferred to a later pass; this turn only records the plan.
- 2026-06-30: User said "go ahead and finish the final layer" — V1 implemented end-to-end (Parts A–D). Live Azure `gpt-4o` narrate + chat verified working (typed lines, clean guardrail, no crop/yield/loan leakage); deterministic fallback verified; audit rows persist. A 4-lens adversarial review (claim-discipline, contract/fallback, secret-handling/determinism, portal/UX) confirmed 6 real findings, all fixed: 4 guardrail gaps closed (spelled-out numbers, `creditworthy`/`lend` verdicts, broadened regional crops, disease words) and 2 portal polish items (mock claim-type provenance, honest error-bubble badge).
- 2026-07-01: User tested the live assistant and flagged three rendering problems — raw Markdown (`**`), inline `[claim_type]` tags littering the prose, and broken Arabic/English bidi. Fixed: claim types moved out of the text into the structured pill fields; chat renders Markdown; replies follow the user's language; per-paragraph `unicode-bidi: plaintext`. User confirmed "it looks fine now". Same turn, decided the forbidden-phrase guardrail was not earning its keep (Latin-only, risked blocking correct refusals) and removed it — the grounded prompt is the control.
- 2026-07-01: User found the answers unintelligent — it ignored ground-truth crop labels they provided and could not reason about rotations. Root causes: the prompt omitted the per-cycle activity-record timeline, and it had only cautionary notes (no enabling agronomy knowledge) plus a blunt "never mention crops" rule. Decided **expert mode** that reasons with user-declared crops (see Decisions); yield/income/loan stay excluded.
- 2026-07-01: User's idea — feed their `05-local-interpretation-context.md` to the LLM. Decided a dedicated, runtime-loaded `api/assistant/knowledge.md` (curated/generalized; `05` stays the research log) so they can teach the assistant by editing one file.

## Decisions

- [decision] Assistant scope includes on-demand report narration and bounded analyst/chat over FarmTrust evidence. It is not a chatbot over arbitrary documents or unsupported external content.
- [decision] The assistant consumes existing FarmTrust evidence and T-11 packet fields; it must not invent new assessment facts, change scores, or override deterministic pipeline outputs.
- [decision] The core report remains usable without the assistant through deterministic packet/report rendering.
- [decision] Guardrail tests are ship-blocking for assistant/chat: unsupported crop identity, yield, pest diagnosis, financing decision, legal/survey claims, fabricated evidence, hidden uncertainty, and untyped hypotheses must be blocked or labelled safely before release.
- [decision] Use `outputs/exploration/AI_ASS~1.HTM` as the assistant UX/design reference for V1 unless superseded by a later approved design. The design's core rule is: users may ask freely, but the assistant is bounded in what it may assert.
- [decision] LLM provider/package: the user's **Azure AI Services `gpt-4o`** accessed via **`langchain-openai`'s `AzureChatOpenAI`**, reusing the user's proven config (`azure_endpoint=https://enova-ai-3080-resource.services.ai.azure.com`, `api_version=2024-02-15-preview`, `azure_deployment=gpt-4o`, key from `AZURE_API_KEY`, temperature 0). LangChain is scoped to the chat model + structured output only (no agents/chains/tools/RAG) and isolated in `api/assistant/llm.py`, so the provider is swappable. (2026-06-30)
- [decision] Typed output is hybrid: narration via `.with_structured_output()` (reliable per-line `{text, claim_type, source}`); free chat via `.invoke()` (free-form, tagged with an overall claim type) — don't force a schema on open Q&A. (2026-06-30)
- [decision] Persist assistant interactions in an `AssistantMessage` table with packet hash, model, prompt version, guardrail result, and timestamp (satisfies the T-11 storage requirement). (2026-06-30)
- [decision] UI placement: a Radix tab ("Report" / "Ask the assistant") on the existing `/lands/[id]/packet` report-card page; non-streaming request/response for V1. (2026-06-30)
- [decision] Deviation from the ship-blocking guardrail decision above: per the user, V1 keeps guardrails **light** (grounded system prompt + claim typing + forbidden-phrase scan + deterministic fallback). The heavy code-enforced per-line validator remains required, but is deferred to a pre-production follow-up rather than built in V1. (2026-06-30)
- [decision] **Output guardrail scan removed (supersedes the light-guardrail decision).** After the user tested the live model, the forbidden-phrase scan was deleted (`guardrails.py` + tests): it was Latin-only (blind to Arabic crop names) and risked blocking a *correct* refusal that quotes a crop name (e.g. "crop identity cannot be determined, such as corn or wheat"), forcing a needless deterministic fallback. The grounded system prompt is now the sole control and reliably produces those refusals. The heavy per-line validator stays a documented pre-production consideration. (2026-06-30)
- [decision] **Output formatting:** claim types/sources live ONLY in the structured fields (the per-line pills), never inline in the text; chat answers render as **Markdown** (`react-markdown`, `dir="auto"` for RTL); the assistant **replies in the user's language** (Arabic/English for chat; narration stays English). (2026-06-30)
- [decision] **Expert-analyst mode (2026-07-01).** Live testing showed the assistant was too timid — it refused to engage even when the user supplied ground-truth crop labels, and it could not see its own cycle sequence. Changes: (a) the prompt now includes the full **activity-record timeline** (each cycle's summer/winter label + dates + peak NDVI), so the model can map declared crops onto specific cycles; (b) it carries **regional agronomy knowledge** and reasons like an analyst, not a packet parser; (c) the crop rule is reframed — never assert a crop from satellite alone, BUT treat crops the **user declares** as ground truth, map them onto the cycles, and reason about rotation/consistency. Yield, income, and loan decisions remain hard-excluded. (Chosen via "reason with my labels" + "keep yield/income/loan out".)
- [decision] **Curated field knowledge in a dedicated, runtime-loaded file (2026-07-01).** The assistant's local expertise lives in `api/assistant/knowledge.md` — a clean, generalized distillation of `docs/documentations/05-local-interpretation-context.md` (cropping calendar + interpretation lessons, with parcel-specific numbers and project-process sections stripped). `prompt.py::load_knowledge()` reads it fresh on every call, so editing the `.md` updates the assistant with **no code change or restart**. `05` stays the human research log; the `.md` is the machine-fed source of truth. A compact fallback string keeps the prompt working if the file is missing. `PROMPT_VERSION` → `assistant-prompt-v2-2026-07-01`.
- [decision] **Bidi-safe rendering (2026-07-01).** Mixed Arabic/English answers render each Markdown block with its own `dir="auto"` plus `unicode-bidi: plaintext`, so every paragraph resolves direction from its own content and isolates embedded Latin runs (numbers, acronyms) — fixing the RTL/LTR scrambling. The user's own chat bubble gets the same treatment.

## Open Questions

- [answered] Which LLM provider should be used, if any, and how should credentials be configured? The user's **Azure AI Services `gpt-4o`** via `langchain-openai`; credentials in repo-root `.env` (`AZURE_API_KEY`, gitignored), loaded via `uvicorn --env-file .env` or `python-dotenv`. LLM gated off when the key is absent (deterministic fallback).
- [answered] Should the first version support English only, Arabic only, or both? Initially English-only; **revised 2026-07-01** — chat now **replies in the user's language** (Arabic confirmed working); on-demand narration stays English for now.
- [answered] Should generated briefs be stored with reports or generated on demand each time? Generated on demand, and **stored** for audit in an `AssistantMessage` table (packet hash, model, prompt version, guardrail result, timestamp).
- [answered] Should follow-up questions be included in the first version, or deferred until generated briefs are validated? Include bounded report chat/follow-up questions as a shipped assistant surface, gated by evidence-packet readiness and guardrail tests.
- [answered] Which audiences matter for the first build: lender only, or lender plus farmer/investor/cooperative variants? **Lender only** for V1; investor/farmer/cooperative tones deferred.

## Knowledge to Keep

- Product truth to promote later: AI explains report evidence and monitoring changes; it does not create risk evidence.
- Engineering truth to promote later: evidence-packet contract, provider boundary, endpoint shape, and fallback behavior.
- Decision truth to promote later: selected provider, storage policy, supported languages, claim typing, and bounded chat scope.
- T-11 owns pipeline/report-packet readiness. T-04 owns assistant narration, bounded analyst/chat, provider integration, and guardrail tests.
- `outputs/exploration/AI_ASS~1.HTM` is the current assistant design reference. Preserve its constraints during implementation: downstream-only AI, works without AI, every sentence sourced/typed, local context is not automatic truth, guardrails enforced in code/tests, and decision-support wording on generated surfaces.

## Done Summary

- 2026-06-30: **Planning complete.** All open questions resolved and the V1 approach locked (Azure `gpt-4o` via `langchain-openai`; deterministic-first with brief fallback; light guardrails for V1; `AssistantMessage` persistence; packet provenance enrichment; tab UI; English/lender; non-streaming). The full coordinated plan is recorded under "Implementation Plan (V1)".
- 2026-06-30: **V1 implemented and verified.** The bounded report assistant ships deterministic-first with the Azure `gpt-4o` model layered on top.
  - **Part A — provenance (packet v1.1):** `evidence_packet.py` `_apply_provenance` post-pass attaches `claim_type`, `provenance_level`, `source`, `method`, `allowed_use`, `restriction` per claim (additive; the Layer 6 card ignores them). Carried onto `PacketClaim` (`api/schemas.py`, `portal/src/lib/types.ts`) as optional.
  - **Part B — backend:** `farmtrust_core/report/brief.py` (`build_deterministic_brief` — the no-LLM narration AND the fallback) + `api/assistant/` (`config`, `prompt`, `llm`, `service`). `config.is_llm_configured()` gates the LLM off when `AZURE_API_KEY` is absent (`.env`, gitignored — never logged); `llm.py` lazy-imports `langchain_openai` so the deterministic path runs without it. `service.py` uses the LLM when configured, falls back to the brief on missing-config/error, and persists one `AssistantMessage` audit row (packet hash, model, prompt version). `POST /lands/{id}/assistant/{narrate,chat}` in `api/routers/assistant.py`.
  - **Part C — portal:** `useAssistant` hook + `AssistantPanel` (narration claim-type pills, source-mode indicator, suggested chips, decision-support disclaimer) on a Radix tab of `/lands/[id]/packet`; mock-aware Next proxies so demo lands narrate offline.
  - **Part D — tests/verification:** `tests/test_assistant_{brief,service}.py` + packet provenance assertions; portal `tsc` + `next build` clean; live Azure narrate/chat exercised; a 4-lens adversarial review + a post-test polish pass applied.
  - **Deferred (flagged):** the heavy code-enforced per-line guardrail validator (a documented pre-production consideration), response streaming, and farmer/investor/cooperative tones.
- 2026-06-30: **Post-test refinement (after the user tried it in the browser).** Three output-quality fixes: (1) the model was emitting inline `[measured_observation]` tags and raw `**markdown**` in the prose — fixed by instructing claim types/sources to stay in the structured fields only and rendering chat as Markdown (`react-markdown`, `dir="auto"` for RTL); (2) the output forbidden-phrase **guardrail scan was removed entirely** (`guardrails.py` + its tests deleted) — it was Latin-only and risked blocking a *correct* refusal that quotes a crop name; the grounded prompt is the sole control; (3) chat now **replies in the user's language** (Arabic/English). Verified live: clean narration, English Markdown, clean Arabic, grounded crop/yield/loan refusals; 36 backend tests pass, portal typecheck + build clean.
- 2026-07-01: **Bidi + expert-mode + knowledge file.** (1) **Bidi:** mixed Arabic/English now renders per-paragraph (`unicode-bidi: plaintext` + `dir="auto"` on each Markdown block and the user bubble) so numbers/acronyms stop scrambling — user confirmed it looks right. (2) **Expert mode:** the prompt now includes the per-cycle **activity-record timeline** and **regional agronomy knowledge**, and treats crops the user declares as ground truth (maps them onto cycles, reasons rotation/consistency); yield/income/loan stay hard-excluded. (3) **Knowledge file:** local expertise moved into a dedicated, runtime-loaded `api/assistant/knowledge.md` (curated/generalized from doc 05; edit-and-go, no restart) — `05` stays the human research log. `PROMPT_VERSION` → `assistant-prompt-v2-2026-07-01`. 34 assistant/packet tests pass; portal `tsc` + `next build` clean.
