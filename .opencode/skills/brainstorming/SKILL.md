---
name: brainstorming
description: You MUST use this before implementing something new or scaffolding a new project; produces an approved direction plus a plan and docs/README scaffold.
---

# Brainstorming

## Overview
Turn a rough idea into an approved direction, then scaffold the planning + docs artifacts needed to execute.
Use one Work Packet as the living ground-truth document for role split, tasks, feedback, and knowledge capture.

**Announce at start:** "I'm using the brainstorming skill to explore this idea with you."

<HARD-GATE>
Do NOT write code, scaffold files, or take implementation action until you have presented a direction and the user has approved it.
This applies even if the change seems simple.
</HARD-GATE>

## Checklist
Complete these in order:
1. Explore context (repo structure, existing patterns)
2. Clarify success criteria (what "done" means)
3. Identify constraints (time, compatibility, performance, security)
4. Ask clarifying questions (ONE at a time; multiple choice preferred)
5. Propose 2-3 approaches (trade-offs)
6. Recommend one approach (why)
7. Get explicit approval
8. Scaffold plan + docs (no code changes)

## Key Principles
- One question per message
- 2-3 options only; recommendation required
- No TDD enforcement
- Make assumptions explicit

## Output Contract
When direction is clear, produce this exact structure:

Bottom line: (2-3 sentences)

Options:
1) ...
2) ...
3) ... (optional)

Recommendation: ...

Action plan (<= 7 steps):
1) ...

Assumptions:
- ...

Open question (0-1): ...

## Scaffolding (After Approval)
After the user approves the recommendation, create/update these artifacts:

1) Plan document
- Use one active Work Packet in `docs/PLANS/P-xx-*.md`.
- Create `docs/PLANS/` if missing.
- Write/update `docs/PLANS/P-xx-<topic>.md` containing:
  - Goal
  - Scope (IN/OUT)
  - Role Split (`driver`, `reviewer`, `curator`; roles may interleave)
  - Chosen approach (1-2 paragraphs)
  - Build Plan
    - organize by phases when useful
    - use checklist items for tasks
    - use checkboxes (`- [ ]` / `- [x]`) when status is known
  - Feedback Log (iteration notes and decisions from reviews)
  - Decisions
  - Open Questions / questions asked by user for later answering
  - Knowledge to Keep (durable insights worth preserving)
  - Done Summary (compact closeout after completion)

2) README/documentation scaffold
- If project has `README.md`: add/update a short section relevant to the change (setup/usage/notes).
- If no `README.md`: create one with: Overview, Quick Start, How to Verify, Notes.
- If the project uses `docs/`: add `docs/` entry point or note.

3) Work Packet hygiene
- Keep the Work Packet concise and current as work progresses.
- Before commit and when a task/plan is finished, clean it up:
  - mark completed checklist items
  - remove stale or duplicate tasks
  - compact verbose notes into short, factual bullets
  - move durable knowledge to README/docs/ADR/backlog as appropriate

## Integration
- If you are unfamiliar with the repo, run `onboarding` first.
- Use `guidance` for commits/testing/debugging/security guardrails while executing.
