# DECISIONS
Purpose: append-only decision log that records the rationale behind truth.

## Links
- PROJECT section: <PROJECT §...>
- ENGINEERING section: <ENGINEERING §...>
- WORKSTREAM: <WS-xx — name>

## Format
YYYY-MM-DD — Decision: <what we chose>
Why: <reasoning / constraints>
Alternatives: <A/B/C considered>
Consequences: <implications / tradeoffs>
Links: <PROJECT §... | ENGINEERING §... | WS-xx>

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
