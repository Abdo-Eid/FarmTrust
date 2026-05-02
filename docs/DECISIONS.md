# DECISIONS
Purpose: append-only decision log that records the rationale behind truth.

## Links
- PROJECT section: <PROJECT §...>
- ENGINEERING section: <ENGINEERING §...>
- PLAN: <P-xx — name>

## Format
YYYY-MM-DD — Decision: <what we chose>
Why: <reasoning / constraints>
Alternatives: <A/B/C considered>
Consequences: <implications / tradeoffs>
Links: <PROJECT §... | ENGINEERING §... | PLAN: P-xx>

---

YYYY-MM-DD — Decision: ...
Why: ...
Alternatives: ...
Consequences: ...
Links: ...

2026-01-25 — Decision: Satellite-only assessment (no ground sensors/field visits)
Why: Core constraint for speed, scale, and cost in early deployment.
Alternatives: Add field surveys; hybrid satellite + IoT sensing.
Consequences: Higher uncertainty in some indicators; must include confidence and conservative flags.
Links: PROJECT §MVP scope | ENGINEERING §Data & signals

2026-01-25 — Decision: MVP is decision support, not automated financing
Why: Trust and interpretability are required; early models may be imperfect.
Alternatives: Automated approval/rejection rules.
Consequences: Outputs must explain reasons and confidence; users remain in control.
Links: PROJECT §Outputs (what the user sees)

2026-01-25 — Decision: MVP gap handling uses smoothing + light interpolation with confidence penalty
Why: Simple, fast, explainable approach for early deployment.
Alternatives: Multi-source fusion or model-based imputation.
Consequences: Long gaps may still mislead; confidence must be conservative.
Links: ENGINEERING §Pipeline

2026-01-25 — Decision: Include broad crop category in MVP; yield bands deferred
Why: Adds decision value with lower label burden; yield bands need stronger validation.
Alternatives: Defer crop categories; introduce yield bands early.
Consequences: Crop outputs remain coarse; yield insight postponed until evidence is stronger.
Links: PROJECT §MVP scope

2026-01-25 — Decision: MVP scope boundaries and workflow
Why: Aligns early delivery with trust, coverage, and operational simplicity.
Alternatives: Pilot-only geography; larger plot size bounds; request-centric workflow; aggressive flags.
Consequences: National scope with 1–200 feddan focus; lands-only portal; conservative risk flags; weak-label validation with optional public-area review.
Links: PROJECT §MVP scope

2026-01-25 — Decision: Data sources use Sentinel-2 with Landsat fallback
Why: Improves continuity while staying on open data sources.
Alternatives: Sentinel-2 only; add commercial sources.
Consequences: Handle cross-sensor consistency in processing and confidence.
Links: ENGINEERING §Data & signals

2026-01-27 — Decision: Phase A repo layout with shared contracts folder
Why: Enables parallel work while keeping schema truth centralized.
Alternatives: Split repos; flat services-only without shared contracts.
Consequences: Contracts must be maintained and validated across services.
Links: ENGINEERING §Repo structure (Phase A) | ENGINEERING §Contracts (source of truth)

2026-01-27 — Decision: Phase A schema tooling stack
Why: Enforceable payload contracts across API and portal with minimal overhead.
Alternatives: Pydantic-only; OpenAPI-first without JSON Schema; no contract validation.
Consequences: Schemas are authoritative; generated types are disposable.
Links: ENGINEERING §Contracts (source of truth)

2026-01-27 — Decision: Phase A demo entry point uses scripts (no Docker required)
Why: Faster, Windows-friendly demo for team onboarding.
Alternatives: Docker-only demo; manual multi-command setup.
Consequences: Maintain scripts for starting services, seeding AOI, and printing URLs.
Links: ENGINEERING §Ops & scaling

2026-01-27 — Decision: Phase A indicator set locked to minimal outputs
Why: Reduce model scope and focus on demo-ready, explainable signals.
Alternatives: Full indicator suite; include crop classes or yield bands in Phase A.
Consequences: Limited outputs but faster integration and lower risk.
Links: ENGINEERING §Data & signals

2026-01-29 — Decision: Phase A role breakdown adjusted
Why: Reduce Phase A scope by deferring governance/QA/versioning and split seasonal analysis for parallel delivery.
Alternatives: Keep storage/curation as a dedicated role; keep ML/time-series as a single role.
Consequences: Ingestion owns minimal persistence; seasonal analysis is a distinct handoff to scoring.
Links: PROJECT §Phase 1 ownership | ENGINEERING §Phase scope notes

2026-01-29 — Decision: Phase A uses direct worker flow, queue deferred
Why: POC scope does not require multi-user concurrency; faster setup and debugging.
Alternatives: Introduce queue/broker in Phase A.
Consequences: Limited concurrency and reliability in Phase A; queue added in Phase B.
Links: PROJECT §MVP scope | ENGINEERING §Ops & scaling

2026-03-07 — Decision: Use `farmtrust_core/` as the single top-level importable Python package
Why: Keep reusable pipeline logic in one place so worker and API consume the same implementation and avoid duplication.
Alternatives: Keep logic inside service-specific folders; split reusable logic across multiple utility packages.
Consequences: Cleaner long-term reuse and simpler imports; requires disciplined boundaries so service-specific concerns do not leak into core.
Links: ENGINEERING §Repo structure (Phase A) | PLAN: P-01 — Starter pipeline for three roles

2026-03-12 — Decision: Use lean default dependency install with `data` extra for ingestion
Why: Keep default environment small for faster onboarding and lower install friction while preserving a clear opt-in path for heavy geospatial dependencies.
Alternatives: Keep ingestion/geospatial dependencies in main dependencies so `uv sync` installs everything by default.
Consequences: Ingestion contributors must run `uv sync --extra data`; docs and runbooks must point to extra-based setup to avoid missing-package errors.
Links: ENGINEERING §Dev workflow (Phase A) | README §Python environment (uv)
