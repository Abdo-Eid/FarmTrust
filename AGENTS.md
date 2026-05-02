# AGENTS.md — Aha!Kit
Tagline: Turn ideas into a buildable truth.

## Kit overview (Aha!Kit)
Aha!Kit is a project-first documentation and execution kit for ambiguous projects.
It keeps a single product truth, a single engineering truth, and a lightweight decision log,
so PLANs can execute without drift or document sprawl.

## Prime directive
Prefer clarity over code. Preserve intent. Keep the project coherent.

## Doc authority (truth levels)
- `docs/inbox/*.md` (except `docs/inbox/README.md`): inbox source docs (non-authoritative). Use metadata; only docs that must stay verbatim should set `keep_as_user: true`.
- `docs/inbox.md`: legacy raw capture archive (non-authoritative, read-only except promotion pointer append).
- `docs/PROJECT.md`: product truth (authoritative).
- `docs/ENGINEERING.md`: engineering truth (authoritative).
- `docs/DECISIONS.md`: decision log that records rationale behind truth (authoritative, append-only).
- `docs/PLANS/*.md`: execution truth for a slice; must promote shared-truth changes.

## One-file default (truth ripple exception)
Update exactly ONE canonical file per request by default:
- Product/scope/roadmap/options/open questions -> `docs/PROJECT.md`
- Architecture/ops/interfaces/pipeline/risks -> `docs/ENGINEERING.md`
- Decisions/commitments -> `docs/DECISIONS.md`
- Execution detail for a slice -> one `docs/PLANS/P-xx-*.md`
Touch a second file only for a truth ripple that must be reflected elsewhere.

## Two-layer writing (avoid mixed levels)
- `PROJECT.md`: intent-level (*what/why/who/scope/outputs/roadmap*).
- `ENGINEERING.md`: deep technical detail (*how*: architecture, pipeline, ops, interfaces).
If a note is contextual but technical, keep a 1-2 line abstract in `PROJECT.md` and link to details in `ENGINEERING.md`.

## Promotion workflow
- Inbox -> promote to `PROJECT.md`, `ENGINEERING.md`, or a `PLAN` file.
- Any committed decision -> add a `DECISIONS.md` entry and patch relevant truth doc(s).

## Gates (lightweight convergence)
### Exploration Gate (lives in `PROJECT.md`)
- MVP scope written
- Top open questions prioritized
- Options capped with evidence and decision triggers

### Execution Gate (lives in each PLAN file)
- Boundaries + interfaces declared
- Plan + checklist present
- Dependencies noted
- Uncertainty explicitly marked

## PLAN rules
- Each PLAN file declares boundaries, interfaces, and dependencies.
- Shared-truth changes must update `PROJECT.md`/`ENGINEERING.md` and add a `DECISIONS.md` entry if it is a decision.

## Workflow defaults
- If unfamiliar with this repo, run `onboarding` first.
- For any creative change (feature, architecture, behavior change) or scaffolding a new project, run `brainstorming` first.
- For raw notes, idea dumps, scratchpads, or inbox-style content that needs merge/adapt/extract, run `inbox-triage` first using `docs/inbox/*.md` (exclude `docs/inbox/README.md`) and inbox metadata.
- Keep one live Work Packet in `docs/PLANS/P-xx-*.md` as the minimal ground-truth source for the current initiative.
- Use lightweight role split per cycle (`driver`, `reviewer`, `curator`); roles may interleave and switch.
- After brainstorming approval, scaffold a plan and docs/README as instructed by `brainstorming`.
- After inbox triage approval, apply accepted extractions into the right docs, plans, issues, or follow-up proposals.
- Before commit, and again when a plan/task is finished, compact and clean the Work Packet: update task status, remove stale notes, preserve durable knowledge.
- No TDD requirement. Prefer running existing tests; add tests when risk is high.
- Prefer small, reversible changes.
- Conventional commits when committing.

## Work Packet protocol
- Treat the Work Packet as the single source of truth for active work.
- Work Packet location: one active `docs/PLANS/P-xx-*.md` for the current slice.
- Required sections:
  - Goal
  - Scope (IN/OUT)
  - Role Split (`driver`, `reviewer`, `curator`; flexible/interleaved)
  - Chosen approach
  - Build Plan (checkbox tasks)
  - Feedback Log (iteration notes)
  - Decisions
  - Open Questions
  - Knowledge to Keep
  - Done Summary
- Keep it compact and current; do not let completed or obsolete tasks linger.
- During closeout, extract long-lived knowledge to durable docs (README, ADR, architecture docs, roadmap, backlog) and keep only a concise summary in the Work Packet.

## Inbox rules (flat source docs)
- Put new intake docs directly in `docs/inbox/*.md`.
- Use YAML front matter metadata in each inbox doc.
- Only docs that must remain verbatim should include `keep_as_user: true`.
- Working docs (without `keep_as_user: true`) use stage metadata: `stage: added -> adapted|discussed|clarification`, then delete the doc after extraction/promotion is complete.
- If a source doc is large or mixed, split it into multiple titled docs before adapting each part.
- For `keep_as_user: true` docs and legacy `docs/inbox.md`, only append `Promoted to: <file>#<section>` after promotion.
- Keep `docs/inbox.md` as a legacy archive; do not restructure it.

## Brainstorming mode (Superpowers-inspired, Prometheus-flavored)
- Ask ONE question per message.
- Prefer multiple-choice questions.
- Explore 2-3 approaches with trade-offs; recommend one.
- Stop before implementation until direction is approved.

## Inbox triage mode
- Use this when input is messy, partial, speculative, or mixed-purpose.
- Run the `inbox-triage` skill as the source of truth for classification/extraction and one-question cadence.
- Intake paths: `docs/inbox/*.md` (exclude `docs/inbox/README.md`) and legacy `docs/inbox.md` when requested.
- Apply the metadata and cleanup rules from "Inbox rules (flat source docs)".
- Continue until every inbox item is intentionally merged/adapted/tasked/parked/discarded.

## Uncertainty markers
Use:
- `[clarification needed]`
- `[assumption]`
- `[option]`
- `[risk]`

## Options discipline (avoid infinite exploration)
- Cap options to 2-3 per topic.
- Each option includes: tradeoff, evidence needed, decision trigger, kill condition.

## Required behaviors
- Clarification-options: when a user says they do not understand next steps or asks for clarification, respond with 2-4 options. For each option include what it means, when to pick it, and what the agent will do next if chosen.
- README bootstrap: when starting work in a NEW project repo using Aha!Kit, first update `README.md` with a short project overview, the note "This repo uses Aha!Kit," and starter instructions (inbox, PROJECT, ENGINEERING, DECISIONS, how to start a PLAN, minimal dev workflow).

## Skill map (project-local)
Use the OpenCode `skill` tool to load these when relevant:
- `onboarding`: get familiar with an unfamiliar repo
- `brainstorming`: decide direction before implementation; scaffold plan + docs/README
- `inbox-triage`: process raw notes/ideas/inbox content; extract, split, classify, and propose merges/adaptations into project docs and plans
- `guidance`: commits, verification, debugging, security guardrails

## Aha!Kit Commands (Protocol)
These slash commands are conventions, not tooling features.
They are instruction shortcuts understood by the agent when used in this repository.
All other Aha!Kit behaviors are enforced automatically by AGENTS.md and do NOT require commands.

Only the commands below exist.

---

### /ahakit promote

Purpose:
Explicitly move from raw capture to structured truth.

Behavior:
- Intake paths:
  - source docs under `docs/inbox/*.md` (default; exclude `docs/inbox/README.md`)
  - latest entry in legacy `docs/inbox.md` when explicitly requested
- Run the `inbox-triage` skill for triage/extraction behavior.
- Keep promote-specific commitments:
  - preserve `keep_as_user: true` docs verbatim; for legacy `docs/inbox.md`, only append `Promoted to: <file>#<section>`
  - docs without `keep_as_user: true` may be adapted/discussed/clarified and then deleted after promotion
- Promote accepted `merge`/`adapt` content into canonical docs:
  - product intent, scope, roadmap, options, open questions -> `docs/PROJECT.md`
  - technical architecture, pipeline, ops, interfaces -> `docs/ENGINEERING.md`
  - execution-specific details -> relevant `docs/PLANS/P-xx-*.md`
- Convert accepted `task` items into actionable checklist entries (PLAN Build Plan or backlog destination).
- Record explicitly committed decisions in `docs/DECISIONS.md`.
- Preserve uncertainty markers: `[clarification needed]`, `[assumption]`, `[option]`, `[risk]`.
- Link between docs instead of duplicating content.

When to use:
- After dumping ideas or drafts into `docs/inbox/*.md` (or legacy `docs/inbox.md`).
- When you are ready to turn raw thinking into structured project truth.

---

### /ahakit clarify

Purpose:
Resolve ambiguity and align before proceeding.

Behavior:
- Scan current canonical docs:
  - `docs/PROJECT.md`
  - `docs/ENGINEERING.md`
  - `docs/DECISIONS.md`
  - relevant `docs/PLANS/P-xx-*.md` files (if any)
- Extract ALL unresolved or ambiguous points, including:
  - explicit markers: `[clarification needed]`, `[assumption]`
  - implicit ambiguities or multiple interpretations
  - missing scope boundaries or unclear responsibilities
- Group ambiguities into a short list of clarification topics.

For each clarification topic:
- Present 2-4 resolution options.
- For each option, explain:
  - What this option means
  - When it is the right choice
  - Trade-offs and risks
  - What will concretely change in docs if chosen

Interaction rule:
- Ask the user to choose one option per topic (or explicitly defer it).
- Do NOT proceed with implementation or restructuring until:
  - ambiguity is resolved, or
  - user explicitly defers it.

After resolution:
- Apply chosen options.
- Update `docs/PROJECT.md` and/or `docs/ENGINEERING.md` as needed.
- Record committed decisions in `docs/DECISIONS.md`.

## Compact style
Dense, scannable, consistent headings. Tight bullets. No fluff.

## When asked to code
Update docs first. Do not code unless gates are satisfied or explicitly requested.
