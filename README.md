# FarmTrust
this is a graduation project for NeuralAlloy team

<img width="240" alt="NeuralAlloy-السبيكه العصبيه" src="https://github.com/user-attachments/assets/5504579a-3575-4b0a-a18a-1684f69c62ac" />

## Project overview
FarmTrust turns satellite time series into clear land assessment signals for banks and agri-finance.
It focuses on Egypt-scale constraints (small plots, mixed crops) to deliver decision support
about land activity, trend, and risk without field visits or ground sensors.
Outputs are designed for fast, explainable financing review, not automated decisions.

Constraints / non-goals: Satellite-only; no ground sensors or field visits. Not optimizing for
best-possible model accuracy in the MVP, only to prove the approach is viable.

This repo uses **Aha!Kit** — a project-first documentation + execution kit with:
- one product truth (`docs/PROJECT.md`)
- one engineering truth (`docs/ENGINEERING.md`)
- one decision log (`docs/DECISIONS.md`)

## After you clone

1) Read these first (in order):
   - `docs/PROJECT.md`
   - `docs/ENGINEERING.md`
   - `docs/DECISIONS.md`
   - `docs/INDEX.md`

2) Declare your role and scope:
   - Post your role (e.g., “ML/time-series preprocessing”, “ML/seasonal analysis”, “Data ingestion”, “Frontend portal”).
   - Confirm which outputs/interfaces you own.

3) If using an AI agent, use this onboarding prompt:
```
You are onboarding to FarmTrust. Read `docs/PROJECT.md`, `docs/ENGINEERING.md`,
`docs/DECISIONS.md`, and `docs/INDEX.md`. Summarize:
- project goal, MVP scope, and non-goals
- key decisions already made
- open questions that affect my role
Ask me to confirm my role if unclear.
```

4) Then use this role-specific plan prompt:
```
I am the <ROLE> for FarmTrust. Based on this role, draft a short execution plan
with milestones, dependencies, and risks, and include a role-specific checklist.
Store the plan in a PLAN file.
Only propose doc updates if it changes shared scope or technical truth.
```

5) Create a plan:
   - Copy `docs/PLANS/P-00-template.md` → `P-01-<name>.md`

## Where to write/read
- Inbox source docs: `docs/inbox/*.md` except `docs/inbox/README.md` (use metadata)
- Keep verbatim docs only: set `keep_as_user: true`
- Working docs lifecycle: `stage: added -> adapted|discussed|clarification`, then delete after promotion/extraction
- Legacy raw archive: `docs/inbox.md` (read-only except promotion pointer append)
- Product truth: `docs/PROJECT.md`
- Engineering truth: `docs/ENGINEERING.md`
- Decisions: `docs/DECISIONS.md`
- Plans: `docs/PLANS/P-xx.md`
- Docs index: `docs/INDEX.md`

## Plans
Create a plan by copying `docs/PLANS/P-00-template.md` → `P-01-<name>.md`.

## Python environment (uv)

Install and sync dependencies with `uv`.

Dependency split model:
- Main dependencies: minimal runtime dependencies required by `farmtrust_core` code.
- Optional extra `data`: ingestion and geospatial stack.
- Optional extra `ml`: placeholder for future ML framework decision (intentionally empty).
- Dev group: notebook and local developer tooling.

Setup commands:

```bash
uv sync
```

Ingestion/data role setup:

```bash
uv sync --extra data
```

Install all extras:

```bash
uv sync --all-extras
```

Team-safe sync (frozen lock):

```bash
uv sync --frozen --extra data
```

## Dev workflow

Common commands:

```bash
uv run ingest-aoi --config worker/scripts/ingest_demo.json
uv run python scripts/ingest_fixtures.py
```

Note: README stays short. The source of truth lives in `/docs`.
