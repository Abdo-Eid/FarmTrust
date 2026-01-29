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
   - `docs/index.md`

2) Declare your role and scope:
   - Post your role (e.g., “ML/time-series preprocessing”, “ML/seasonal analysis”, “Data ingestion”, “Frontend portal”).
   - Confirm which outputs/interfaces you own.

3) If using an AI agent, use this onboarding prompt:
```
You are onboarding to FarmTrust. Read `docs/PROJECT.md`, `docs/ENGINEERING.md`,
`docs/DECISIONS.md`, and `docs/index.md`. Summarize:
- project goal, MVP scope, and non-goals
- key decisions already made
- open questions that affect my role
Ask me to confirm my role if unclear.
```

4) Then use this role-specific plan prompt:
```
I am the <ROLE> for FarmTrust. Based on this role, draft a short execution plan
with milestones, dependencies, and risks, and include a role-specific checklist.
Store the plan in a workstream file.
Only propose doc updates if it changes shared scope or technical truth.
```

5) Create a workstream:
   - Copy `docs/WORKSTREAMS/WS-00-template.md` → `WS-01-<name>.md`

## Where to write/read
- Dump raw notes: `docs/inbox.md`
- Product truth: `docs/PROJECT.md`
- Engineering truth: `docs/ENGINEERING.md`
- Decisions: `docs/DECISIONS.md`
- Workstreams: `docs/WORKSTREAMS/WS-xx.md`
- Docs index: `docs/index.md`

## Workstreams
Create a workstream by copying `docs/WORKSTREAMS/WS-00-template.md` → `WS-01-<name>.md`.

## Dev workflow
TBD.

Note: README stays short. The source of truth lives in `/docs`.
