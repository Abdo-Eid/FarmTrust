# AGENTS.md — Aha!Kit
Tagline: Turn ideas into a buildable truth.

## Kit overview (Aha!Kit)
Aha!Kit is a project-first documentation and execution kit for ambiguous projects.
It keeps a single product truth, a single engineering truth, and a lightweight decision log,
so workstreams can execute without drift or document sprawl.

## Prime directive
Prefer clarity over code. Preserve intent. Keep the project coherent.

## Doc authority (truth levels)
- `docs/inbox.md`: raw capture only (non-authoritative). Never restructure or “clean” it.
- `docs/PROJECT.md`: product truth (authoritative).
- `docs/ENGINEERING.md`: engineering truth (authoritative).
- `docs/DECISIONS.md`: decision log that records the rationale behind truth (authoritative, append-only).
- `docs/WORKSTREAMS/*.md`: execution truth for a slice; must promote shared-truth changes.

## One-file default (truth ripple exception)
Update exactly ONE canonical file per request by default:
- Product/scope/roadmap/options/open questions → `docs/PROJECT.md`
- Architecture/ops/interfaces/pipeline/risks → `docs/ENGINEERING.md`
- Decisions/commitments → `docs/DECISIONS.md`
- Execution detail for a slice → one `docs/WORKSTREAMS/WS-xx-*.md`
Touch a second file only for a truth ripple that must be reflected elsewhere.

## Two-layer writing (avoid mixed levels)
- `PROJECT.md`: intent-level (*what/why/who/scope/outputs/roadmap*).
- `ENGINEERING.md`: deep technical detail (*how*: architecture, pipeline, ops, interfaces).
If a note is contextual but technical, keep a 1–2 line abstract in `PROJECT.md` and link to details in `ENGINEERING.md`.

## Promotion workflow
- Inbox → promote to `PROJECT.md`, `ENGINEERING.md`, or a `WORKSTREAM` file.
- Any committed decision → add a `DECISIONS.md` entry and patch the relevant truth doc(s).

## Gates (lightweight convergence)
### Exploration Gate (lives in `PROJECT.md`)
- MVP scope written
- Top open questions prioritized
- Options capped with evidence and decision triggers

### Execution Gate (lives in each workstream file)
- Boundaries + interfaces declared
- Plan + checklist present
- Dependencies noted
- Uncertainty explicitly marked

## Workstream rules
- Each WS file declares boundaries, interfaces, and dependencies.
- Each WS file has an append-only changelog section.
- Shared-truth changes must update `PROJECT.md`/`ENGINEERING.md` and add a `DECISIONS.md` entry if it is a decision.

## Inbox rule (capture-only)
- Do not edit or restructure existing Inbox text.
- You may append a new entry.
- You may append a single line after promotion:
  `Promoted to: <file>#<section>`
Nothing else.

## Uncertainty markers
Use:
- `[clarification needed]`
- `[assumption]`
- `[option]`
- `[risk]`

## Options discipline (avoid infinite exploration)
- Cap options to 2–3 per topic.
- Each option includes: tradeoff, evidence needed, decision trigger, kill condition.

## Required behaviors
- Clarification-options: when a user says they don’t understand next steps or asks for clarification, respond with 2–4 options. For each option include what it means, when to pick it, and what the agent will do next if chosen.
- README bootstrap: when starting work in a NEW project repo using Aha!Kit, first update `README.md` with a short project overview, the note “This repo uses Aha!Kit,” and starter instructions (inbox, PROJECT, ENGINEERING, DECISIONS, how to start a workstream, minimal dev workflow).

## Aha!Kit Commands (Protocol)
These slash commands are conventions, not tooling features.
They are instruction shortcuts understood by the agent when used in this repository.
All other Aha!Kit behaviors are enforced automatically by AGENTS.md and do NOT require commands.

Only the commands below exist.

---

### /ahakit start

Purpose:
First-run bootstrap + initial structuring.

Behavior:
- Ensure repo onboarding is correct:
  - README.md contains a short project overview + note it uses Aha!Kit + starter instructions.
  - docs/index.md links to all canonical docs and workstreams template.
- If docs/inbox.md has content, run the same behavior as `/ahakit promote`:
  - Promote Inbox content into:
    - docs/PROJECT.md (product truth)
    - docs/ENGINEERING.md (engineering truth)
    - docs/DECISIONS.md (decisions if any are explicitly committed)
  - Do not modify the Inbox text.
- If Inbox is empty:
  - Do not invent content.
  - Ask the user to paste notes into Inbox, or suggest the minimal structure to start PROJECT.md.

Notes:
- Idempotent: safe to run multiple times.
- Prefer updating exactly one canonical doc per user request after bootstrap (one-file default rule).


### /ahakit promote

Purpose:
Explicitly move from raw capture to structured truth.

Behavior:
- Read the latest entry in `docs/inbox.md` (or `inbox.xml` if used).
- Promote its content into the correct canonical doc(s):
  - product intent, scope, roadmap, options, open questions → `docs/PROJECT.md`
  - technical architecture, pipeline, ops, interfaces → `docs/ENGINEERING.md`
  - execution-specific details → the relevant WORKSTREAM file
- Do NOT modify, clean, or annotate the Inbox entry.
- Link between docs instead of duplicating content.
- Preserve uncertainty markers: `[clarification needed]`, `[assumption]`, `[option]`, `[risk]`.

When to use:
- After dumping ideas or drafts into Inbox.
- When you are ready to turn raw thinking into structured project truth.

---

### /ahakit clarify

Purpose:
Resolve ambiguity and align before proceeding.

Behavior:
- Scan the current canonical docs:
  - `docs/PROJECT.md`
  - `docs/ENGINEERING.md`
  - `docs/DECISIONS.md`
  - relevant WORKSTREAM files (if any)
- Extract ALL unresolved or ambiguous points, including:
  - explicit markers: `[clarification needed]`, `[assumption]`
  - implicit ambiguities or multiple interpretations
  - missing scope boundaries or unclear responsibilities
- Group ambiguities into a short list of clarification topics.

For each clarification topic:
- Present 2–4 resolution options.
- For each option, explain:
  - What this option means
  - When it is the right choice
  - Trade-offs and risks
  - What will concretely change in the docs if chosen

Interaction rule:
- Ask the user to choose one option per topic (or explicitly defer it).
- Do NOT proceed with implementation or restructuring until:
  - the ambiguity is resolved, or
  - the user explicitly defers it.

After resolution:
- Apply the chosen options.
- Update `docs/PROJECT.md` and/or `docs/ENGINEERING.md` as needed.
- Record committed decisions in `docs/DECISIONS.md`.

## Compact style
Dense, scannable, consistent headings. Tight bullets. No fluff.

## When asked to code
Update docs first. Don’t code unless gates are satisfied or explicitly requested.
