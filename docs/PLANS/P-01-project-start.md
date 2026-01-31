# P-01 — project-start
Purpose: one-file plan for Phase A enablement and structure.

## Links
- PROJECT section: PROJECT §MVP scope
- ENGINEERING section: ENGINEERING §Repo structure; ENGINEERING §Contracts; ENGINEERING §Interfaces
- DECISIONS entry: 2026-01-27 — Decision: Phase A repo layout + contracts source of truth

## Ownership & boundaries
- Owner: Tech lead
- In scope:
  - Phase A enablement (2-week plan) and onboarding clarity.
  - Repo structure creation and minimal dev workflow for team start.
  - Contracts: AOI input, job status, results payload, report export.
  - Demo path definition: draw AOI -> submit -> job list -> land summary -> PDF.
  - Single-job worker flow for Phase A; queue/broker deferred.
  - Direct worker dev path (default) for ingestion/ML iteration; API path used for demos.
- Out of scope:
  - Model tuning, feature engineering beyond Phase A indicator set.
  - Advanced portal UX, auth, or production ops.

## Interfaces & dependencies
- Interfaces owned:
  - Contracts in `contracts/schemas/` (source of truth).
  - API endpoints and job lifecycle definition.
  - Demo workflow scripts and expected outputs.
- Dependencies:
  - Role leads for ingestion, ML/time-series preprocessing, ML/seasonal analysis, ML/scoring, frontend.
  - Data access credentials and AOI sample geometry.
  - Decision confirmations for any scope changes.

## Plan
- Phase 1 (Week 1):
  - Create repo structure and placeholder packages.
  - Draft contracts and schema versioning rules.
  - Document API endpoints and job lifecycle.
  - Define demo path and success criteria.
- Phase 2 (Week 2):
  - Implement UI slice demo flow.
  - Implement API + worker skeletons that return schema-valid payloads.
  - Add scripts for local demo run and sample job seed.
  - Run first end-to-end demo with one land.

## Checklist (definition of done)
- [ ] Repo structure created with `api/`, `worker/`, `portal/`, `contracts/`, `shared/`, `infra/`, `docs/`.
- [ ] Contracts exist for AOI input, job status, land results, report payload.
- [ ] API endpoints documented and aligned to schemas.
- [ ] Job states and phases implemented in API + worker.
- [ ] Portal UI slice supports polygon draw, submission, and summary view.
- [ ] Demo scripts start services, seed AOI, submit job, print URLs + job id.
- [ ] First end-to-end demo completed within Phase A.

## Execution Gate
- Gate: boundaries + plan/checklist + dependencies present.
- Boundaries: tech lead owns enablement and interfaces.
- Plan/checklist: Phase A week-by-week tasks defined.
- Dependencies: role leads and data access identified.
