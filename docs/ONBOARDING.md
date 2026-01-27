# Onboarding — FarmTrust

This repo uses Aha!Kit: product truth in `docs/PROJECT.md`, engineering truth in `docs/ENGINEERING.md`, decisions in `docs/DECISIONS.md`.

## Quick start (read first)
1) `docs/PROJECT.md`
2) `docs/ENGINEERING.md`
3) `docs/DECISIONS.md`
4) `docs/index.md`

## After you clone
1) Read the docs above.
2) Choose your role and outputs (see below).
3) Declare your role to the lead.
4) Start or follow a workstream.

## How to choose your role
Pick the role based on outputs you can own end-to-end:
- Frontend: owns the portal flow (draw AOI, submit, job list, summary view, PDF download). Interfaces with API contracts and defines the minimum UX for Phase A.
- ML/time-series: owns gap handling, smoothing, and confidence logic. Delivers plot-level time series and quality metrics used by scoring.
- ML/scoring: owns land status/trend/season outputs, risk flags, and short evidence reasons. Consumes time-series features and produces decision-support outputs.
- Data ingestion: owns satellite access, AOI mapping, and extraction of plot-level time series. Delivers cleaned inputs to time-series processing.
- Data storage/curation: owns schema, metadata, QA checks, and versioning of outputs. Ensures results are queryable and stable over time.
- Product/Tech lead: owns scope and interfaces, leads decision reviews, and ensures demo readiness with integration checkpoints.

## Declare your role (required)
Send this to the lead before starting work:
- Role:
- Outputs owned:
- Dependencies:

If using an AI agent for your role, use this prompt:
```
You are onboarding to FarmTrust. Read `docs/PROJECT.md`, `docs/ENGINEERING.md`,
`docs/DECISIONS.md`, and `docs/index.md`. Summarize:
- project goal, MVP scope, and non-goals
- key decisions already made
- open questions that affect my role
Ask me to confirm my role if unclear.
```

Then use this role-specific plan prompt:
```
I am the <ROLE> for FarmTrust. Based on this role, draft a short execution plan
with milestones, dependencies, and risks, and include a role-specific checklist.
Store the plan in a workstream file.
Only propose doc updates if it changes shared scope or technical truth.
```

## Start work
- If a workstream file exists for your role, follow it.
- If none exists, create one from `docs/WORKSTREAMS/WS-00-template.md`.

## Where to write/read
- Dump raw notes: `docs/inbox.md`
- Product truth: `docs/PROJECT.md`
- Engineering truth: `docs/ENGINEERING.md`
- Decisions: `docs/DECISIONS.md`
- Workstreams: `docs/WORKSTREAMS/WS-xx.md`
- Docs index: `docs/index.md`

## Dev workflow
- TBD. Follow your role workstream and check with the lead for runtime setup.

## One message template
```
I am the <ROLE> for FarmTrust.
Outputs I own: <interfaces/artifacts>.
Dependencies: <what I need from others>.
```
