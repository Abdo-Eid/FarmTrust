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

This repo uses a project-first documentation workflow with:

- one product truth (`docs/PROJECT.md`)
- one engineering truth (`docs/ENGINEERING.md`)
- one decision log (`docs/DECISIONS.md`)

## After you clone

1. Read these first (in order):
    - `docs/PROJECT.md`
    - `docs/ENGINEERING.md`
    - `docs/DECISIONS.md`
    - `docs/index.md`

2. Declare your role and scope:
    - Post your role (e.g., “ML/time-series preprocessing”, “ML/seasonal analysis”, “Data ingestion”, “Frontend portal”).
    - Confirm which outputs/interfaces you own.

3. If using an AI agent, use this onboarding prompt:

```
You are onboarding to FarmTrust. Read `docs/PROJECT.md`, `docs/ENGINEERING.md`,
`docs/DECISIONS.md`, and `docs/index.md`. Summarize:
- project goal, MVP scope, and non-goals
- key decisions already made
- open questions that affect my role
Ask me to confirm my role if unclear.
```

4. Then use this role-specific task prompt:

```
I am the <ROLE> for FarmTrust. Based on this role, draft a short execution task
with milestones, dependencies, and risks, and include a role-specific checklist.
Store the task in a TASK file.
Only propose doc updates if it changes shared scope or technical truth.
```

5. Create a task:
    - Copy `docs/TASKS/T-00-template.md` → `T-XX-<name>.md`

## Where to write/read

- Product truth: `docs/PROJECT.md`
- Engineering truth: `docs/ENGINEERING.md`
- Decisions: `docs/DECISIONS.md`
- Tasks: `docs/TASKS/T-xx.md`
- Docs index: `docs/index.md`

## Tasks

Create a task by copying `docs/TASKS/T-00-template.md` → `T-XX-<name>.md`. `docs/TASKS/` contains only active or pending work; closed tasks are removed after durable knowledge is promoted.

## Python environment (uv)

Install and sync dependencies with `uv`.

Dependency split model:

- Main dependencies: minimal runtime dependencies required by `farmtrust_core` code (FastAPI/uvicorn plus `numpy`, `pandas`, and `scipy`; `scipy` powers the Whittaker analysis-curve banded solve and `find_peaks` in seasonal analysis).
- Optional extra `data`: ingestion and geospatial stack.
- Optional extra `ml`: placeholder for a later ML framework decision (intentionally empty).
- Dev group: local developer tooling.

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

## Running locally

**Backend** (FastAPI + pipeline, port 8000):

```bash
uv run fastapi dev
```

**Frontend** (Next.js portal, port 3000):

```bash
cd portal && bun dev
```

Both must be running for the portal to work. The portal proxies API calls to `http://localhost:8000` via `portal/.env.local`.

## Dev commands

```bash
# Run the standalone ingestion script
uv run ingest-aoi --config scripts/ingest_demo.json

# Type-check backend
uv run python -m compileall farmtrust_core scripts api -q

# Type-check frontend
cd portal && bun run typecheck
```

## License

Proprietary. Copyright (c) 2026 the FarmTrust Team; Menoufia University holds no
rights in it. Code is all-rights-reserved; research material
(`notebooks/`, `outputs/exploration/`, `outputs/diagnostics/`, `outputs/tools/`,
`docs/documentations/`) is CC BY-NC-SA 4.0. See [`LICENSE`](./LICENSE) and
[`NOTICE`](./NOTICE) for the third-party carve-outs.

Note: README stays short. The source of truth lives in `/docs`.
