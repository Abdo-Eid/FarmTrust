---
name: inbox-triage
description: triage raw notes, inbox files, idea dumps, scratchpads, and mixed drafts into useful project outputs. use when content is messy, incomplete, speculative, or not yet connected to the current repo. especially useful for files under docs/inbox/ that may contain material to merge into docs, adapt into proposals, convert into tasks, park for later, or discard. ask one focused question at a time until the inbox is clean.
---

# Inbox Triage

Turn messy inbox material into clear next steps.

## Use this skill to
- review files under `docs/inbox/` (exclude `docs/inbox/README.md`)
- triage legacy `docs/inbox.md` only when explicitly requested
- extract useful ideas from raw notes
- decide what belongs in docs, tasks, proposals, or nowhere
- ask focused follow-up questions when judgment is needed
- clean the inbox gradually instead of forcing one big rewrite
- keep the active Work Packet current as minimal ground truth

## Core behavior
- Treat inbox content as raw intake, not final documentation.
- Respect inbox metadata:
  - `keep_as_user: true` means keep verbatim; do not clean/rewrite body.
  - working docs use `stage: added -> adapted|discussed|clarification`, then are deleted after extraction/promotion.
- For `keep_as_user: true` docs and legacy `docs/inbox.md`, only append `Promoted to: <file>#<section>` after promotion.
- Read for relevance to the current repo, docs, architecture, roadmap, and backlog.
- When a note contains several ideas, separate them mentally and handle them one by one.
- If a note is large or mixed, split it into multiple titled docs before adapting each part.
- For each useful part, choose one:
  - **merge**: fits existing docs with little change
  - **adapt**: good idea, but needs reshaping for this project
  - **task**: should become actionable work
  - **park**: maybe useful later
  - **discard**: irrelevant, duplicate, or too vague
- Preserve intent, but rewrite for clarity when extracting.
- Do not silently turn speculation into fact.
- Ask exactly one question at a time when user judgment is needed.
- If some parts are obvious, process those first.
- For accepted items, propose a concrete destination section (for example Work Packet `Build Plan`, `Feedback Log`, `Knowledge to Keep`, or `Open Questions`).
- Keep role handoffs clear: state what `driver`, `reviewer`, or `curator` should do next when relevant.

## Output
Keep the result compact.

### Triage summary
- what seems worth keeping
- what needs a decision
- what should be parked
- what should be discarded

### For each item reviewed
- **label**
- **disposition**: merge / adapt / task / park / discard
- **destination**: where it should go
- **why**
- **proposed extraction**: only if worth keeping

### Work Packet update
- list exact updates to apply in `docs/PLANS/P-xx-*.md`
- prefer compact bullets over long prose
- include closeout cleanup notes if tasks are being completed

## Good destinations
- README
- architecture docs
- ADR
- roadmap
- backlog / issue
- proposal
- research note
- `docs/PLANS/P-xx-*.md` (`Build Plan`, `Feedback Log`, `Knowledge to Keep`, `Open Questions`, `Done Summary`)
- `docs/inbox/parking-lot.md`

## Heuristics
- **merge** when it clearly belongs in existing docs
- **adapt** when the idea is useful but still rough
- **task** when it implies concrete work
- **park** when it is interesting but not ready
- **discard** when it adds no durable value

## Handling `docs/inbox/`
- Treat filenames and headings as hints, not truth.
- Work through the inbox in small pieces.
- Prefer moving useful content to a better destination instead of polishing the inbox file itself.
- Leave unclear or speculative material clearly marked as open questions or parked notes.

## Question style
Ask one focused question at a time.
Prefer concrete choices.
Example:
- Should this become a backlog item or be merged into the roadmap?

## Success condition
The inbox is clean when each note has been:
- merged
- adapted
- turned into a task
- parked intentionally
- discarded intentionally
And the Work Packet has been updated or explicitly marked unchanged.
