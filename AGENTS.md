# AGENTS.md
**Tagline:** Turn ideas into a buildable truth. Prefer clarity over code. Preserve intent. Keep the project coherent.

## Stack
- **Backend**: Python 3.12+, FastAPI, SQLModel, Uvicorn
- **Data pipeline**: Planetary Computer, STAC (pystac-client, stackstac), rasterio, xarray, numpy, pandas
- **Frontend**: Next.js 16 + React 19, TypeScript, Tailwind CSS, Radix UI, Leaflet, TanStack Query, better-auth
- **Runtime**: uv (Python), Bun (frontend)

## Doc authority
| File | Role |
|---|---|
| `PROJECT.md` | Product truth: what/why/who/scope/outputs/roadmap |
| `ENGINEERING.md` | Engineering truth: how — architecture, pipeline, ops, interfaces |
| `DECISIONS.md` | Curated decision log; prune superseded entries with references |
| `FUTURE.md` | Non-authoritative idea parking; not scope, roadmap, or architecture truth |
| `PLANS/*.md` | Execution truth per slice; must ripple shared-truth changes |

## Doc routing
Update exactly ONE file per request. Touch a second only for a required truth ripple.
- Product/scope/roadmap/questions → `PROJECT.md` (intent: what/why/who)
- Architecture/ops/interfaces/risks → `ENGINEERING.md` (technical: how)
- Decisions/commitments → `DECISIONS.md`
- Non-committed future ideas/options → `FUTURE.md`; do not treat as scope, roadmap, or architecture truth
- Execution slice → `PLANS/P-xx-*.md`

Keep a 1-2 line abstract in `PROJECT.md`; link to `ENGINEERING.md` for technical-but-contextual detail.

## PLANs
`PLANS/` is not an archive. Keep only active or pending work packets there; git history is the archive for closed plans.

**Convergence gates:**
- *Before exploration ends* (`PROJECT.md`): MVP scope written · top questions prioritized · active options capped with evidence and decision triggers; non-committed ideas parked in `FUTURE.md`.
- *Before execution starts* (each PLAN): boundaries + interfaces declared · checklist present · dependencies noted · uncertainty marked.

Each PLAN declares boundaries, interfaces, and dependencies. Shared-truth changes → update `PROJECT.md`/`ENGINEERING.md` + add `DECISIONS.md` entry. Keep PLAN current: completed work, blockers, verification results, deferred E2E checks.

**Plan closeout protocol:**
- Before closing, review unchecked checklist items with the user.
- Ask whether unchecked items are stale, no longer important, should be finished now, or should become a follow-up plan.
- Do not move unchecked implementation tasks into `OPEN_ITEMS.md`; `OPEN_ITEMS.md` is for unresolved questions or decisions, not task tracking.
- Promote durable knowledge into canonical docs before deleting the plan.
- Promote durable architecture diagrams to `ENGINEERING.md`; do not keep diagrams only in closed plans.
- If follow-up work is real and near-term, create a new plan in `PLANS/`.
- If follow-up work is not near-term, leave it out of `PLANS/`; git history is the archive.
- After durable knowledge is promoted and follow-ups are handled, delete the closed plan file.

**Required Work Packet sections:** Goal · Scope (IN/OUT) · Role Split · Chosen approach · Build Plan · Feedback Log · Decisions · Open Questions · Knowledge to Keep · Done Summary.

During closeout: extract long-lived knowledge to durable docs; keep only a concise summary in the Work Packet.

## Defaults
- Unfamiliar repo → explore and read canonical docs first.
- Creative change/feature → brainstorm direction before implementation.
- One live Work Packet per initiative in `PLANS/`. Role split: `driver` · `reviewer` · `curator` (flexible/interleaved).
- Before commit or plan closeout: compact Work Packet, update task status, remove stale notes, promote durable knowledge.
- Commits: conventional format, small and reversible; verify before committing; no secrets.
- Tests: no TDD requirement; prefer running existing tests; add when risk is high.
- Debug: read logs and trace call path before proposing fixes.
- Security: never expose secrets; validate inputs; prefer least-privilege.
- Frameworks → use current official docs or loaded skill guidance over memory; record choices only when they affect architecture or conventions.
- User intent correction → update active PLAN + affected canonical docs before continuing.
- Docs: use existing canonical docs only; promote only high-signal, current knowledge; `DECISIONS.md` is curated (not append-only): update/remove replaced entries; use `Refines:` for partial changes; include `Supersedes:` or `Refines:` when a decision replaces or adjusts an older one.
- `FUTURE.md` is a non-authoritative parking lot. Use it to preserve ideas without anchoring current work; promote items only after user approval and a canonical-doc update.

## Modes
**Brainstorm:** One question per message, multiple-choice preferred. Explore 2-3 approaches with trade-offs; recommend one. Stop before implementation until direction is approved.

**Clarify** (`/clarify` or when ambiguity blocks): Scan canonical docs for `[clarification needed]`, `[assumption]`, implicit gaps, missing boundaries. Group into topics; present 2-4 options each (meaning, when to pick, trade-offs, doc change). Ask to choose or defer one topic at a time. Do NOT proceed until resolved or deferred. Apply choices; record in `DECISIONS.md`.

**Code:** Update docs first. Do not code unless convergence gates are satisfied or explicitly requested.

## Style & behaviors
**Uncertainty markers:** `[clarification needed]` · `[assumption]` · `[option]` · `[risk]`

**Options discipline:** Cap to 2-3 per topic. Each: tradeoff · evidence needed · decision trigger · kill condition.

**Clarification-options:** When user asks for clarification or says they don't understand next steps → respond with 2-4 options, each with: meaning · when to pick it · what the agent does next.

**Compact style:** Dense, scannable, consistent headings. Tight bullets. No fluff.
