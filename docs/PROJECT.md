# PROJECT
Purpose: single place for product truth (vision, scope, current roadmap, open questions).

## Links
- DECISIONS entry: <YYYY-MM-DD — Decision: ...>
- ENGINEERING section: <ENGINEERING §...>
- PLAN: <P-xx — name>

## Vision
- Provide banks and agri-financiers with objective, explainable land visibility from satellite time
  series so financing decisions are faster and better informed without field visits.

## Working principles
- Protect core scope and technical truth, while encouraging optional improvements that help the team or user outcomes.
- Use judgment: if an improvement changes shared truth, reflect it in the relevant canonical doc.

## Problem
- Financiers lack continuous, objective visibility into land activity and risk; they rely on
  paperwork or one-off visits and cannot see multi-year trends or operational issues.

## Users
- Loan officers and agri-finance analysts evaluating financing requests.
- Portfolio managers monitoring land performance over time.

## Outputs (what the user sees)
- Land status: active / intermittent / inactive.
- 2-year trend: improving / stable / declining.
- Last-season performance: good / interrupted / weak, with short reasons.
- Risk flags: waterlogging, salinity likelihood, abandonment, encroachment / land-use change.
- Confidence level (high/medium/low) per output.
- Smoothed evidence graphs for the most valuable time-series signals (NDVI, EVI, NDMI, NDWI).
- Season count across the selected interval, with season boundaries explained visually.
- PDF report export for lender review.

## MVP scope (what we ship first)
- Satellite-only assessment for a single land polygon.
- AOI input via polygon draw: the user clicks land corners on a map to define the analysis area.
- Geography: Egypt national coverage in MVP.
- Plot size bounds: 1–200 feddan.
- Two-year behavior + trend indicators and last-season performance summary.
- Simple, explainable report suitable for financing review.
- Lightweight portal: lands-only list, one-page land summary, optional map tab.
- Current-build assessment must be based on interval-level evidence, not a single latest observation.
- Validation approach: weak labels only; add public-area qualitative reviews when feasible.
- Risk flags use conservative thresholds to protect trust in MVP outputs.
- Current-build execution uses a single-job worker path; queue/broker is deferred until multi-user needs.

## Current Build ownership (6 roles)
- Product/Tech lead: scope, interfaces, decision reviews, demo readiness.
- Data ingestion: satellite access, AOI mapping, time-series extraction, and minimal persistence.
- ML/time-series preprocessing: gap handling, smoothing, confidence inputs.
- ML/seasonal analysis: historical pattern + seasonal analysis outputs for scoring.
- ML/scoring: status/trend/season, flags, evidence, and assessment confidence.
- Frontend: AOI input UI, summary view, evidence display, PDF export.

## R&D working rules
Problem this solves: frequent back-and-forth and overlapping work cause drift, rework, and integration churn.
- Time-boxed research spikes (3-5 days): each role runs short experiments; outcomes are either (a) ready to integrate, (b) needs more time with a clear next hypothesis, or (c) dropped.
- Optional improvements are welcome and encouraged when they help the team; preserve scope/technical truth and record any shared-truth changes.
- Decision authority: lead by default for scope/timeline decisions; group for research-method decisions.
- Flexible schema: no hard freeze, but any schema change must be announced before weekly integration, include a migration note (what changed + why), and update the relevant truth doc section.
- Prototype policy: R&D outputs must be labeled "prototype/throwaway" until promoted; production use requires an explicit decision.
- Risk ownership: top 3 risks get an owner and a mitigation note, reviewed weekly.
- Validation cadence: role-level validation weekly; cross-team integration review at weekly checkpoint.

## Non-goals
- Automated financing decisions.
- Exact crop type labeling or numeric yield prediction.
- Field surveys or ground sensors as core inputs.

## Big picture (end-to-end)
Inputs → Processing → Outputs → Workflow.
- Inputs: land polygon drawn on a map; time window (last 24 months).
- Processing: satellite time-series indicators → interpretation rules → confidence scoring.
- Outputs: land status, trend, season performance, risk flags, report.
- Workflow: pre-financing review → monitoring during financing → post-season review.

## Open questions
- [clarification needed] Should season segmentation cap cycles per year (e.g., 1–3) or be fully data-driven?
- [clarification needed] What numeric false-alarm threshold defines "very low" for pilot use?

## Future ideas
- Non-committed future ideas are parked in `FUTURE.md`; they are not scope, roadmap, or architecture truth.

## Roadmap
- Current Build: land assessment + lands-only portal + PDF export; minimal persistence only; pilot validation with low confusion and very low false alarms.
- Future ideas are intentionally isolated in `FUTURE.md` and must be re-evaluated before becoming scope or a live plan.

## Exploration Gate
- MVP scope written
- Top open questions prioritized
- Active options capped with evidence and decision triggers; non-committed ideas parked in `FUTURE.md`
