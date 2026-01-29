# PROJECT
Purpose: single place for product truth (vision, scope, roadmap, open questions, options).

## Links
- DECISIONS entry: <YYYY-MM-DD — Decision: ...>
- ENGINEERING section: <ENGINEERING §...>
- WORKSTREAM: <WS-xx — name>

## Vision
- Provide banks and agri-financiers with objective, explainable land visibility from satellite time
  series so financing decisions are faster and better informed without field visits.

## Problem
- Financiers lack continuous, objective visibility into land activity and risk; they rely on
  paperwork or one-off visits and cannot see multi-year trends or operational issues.

## Users
- Loan officers and agri-finance analysts evaluating financing requests.
- Portfolio managers monitoring land performance over time.

## Outputs (what the user sees)
- Land status: active / intermittent / inactive / encroachment.
- 2-year trend: improving / stable / declining.
- Last-season performance: good / interrupted / weak, with short reasons.
- Risk flags: waterlogging, salinity likelihood, abandonment, land-use change.
- Risk tier: low / medium / high (score later when accuracy is proven).
- Confidence level (high/medium/low) per output.
- PDF report export for lender review.

## MVP scope (what we ship first)
- Satellite-only assessment for a single land polygon or point+area input.
- AOI input via polygon draw or point + approximate area.
- Geography: Egypt national coverage in MVP.
- Plot size bounds: 1–200 feddan.
- Two-year behavior + trend indicators and last-season performance summary.
- Simple, explainable report suitable for financing review.
- Lightweight portal: lands-only list, one-page land summary, optional map tab.
- Broad crop category output (season + water-demand class).
- Validation approach: weak labels only; add public-area qualitative reviews when feasible.
- Risk flags use conservative thresholds to protect trust in MVP outputs.
- Phase A execution uses a single-job worker path; queue/broker is deferred until multi-user needs.

## Phase A ownership (6 roles)
- Product/Tech lead: scope, interfaces, decision reviews, demo readiness.
- Data ingestion: satellite access, AOI mapping, time-series extraction, and minimal persistence.
- ML/time-series preprocessing: gap handling, smoothing, confidence inputs.
- ML/seasonal analysis: historical pattern + seasonal analysis outputs for scoring.
- ML/scoring: status/trend/season, flags, evidence, crop category.
- Frontend: AOI input UI, summary view, evidence display, PDF export.

## R&D working rules
Problem this solves: frequent back-and-forth and overlapping work cause drift, rework, and integration churn.
- Time-boxed research spikes (3-5 days): each role runs short experiments; outcomes are either (a) ready to integrate, (b) needs more time with a clear next hypothesis, or (c) dropped.
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
- Inputs: land polygon (drawn) or point + approximate area; time window (last 24 months).
- Processing: satellite time-series indicators → interpretation rules → confidence scoring.
- Outputs: land status, trend, season performance, risk flags, report.
- Workflow: pre-financing review → monitoring during financing → post-season review.

## Open questions
- [clarification needed] What numeric false-alarm threshold defines "very low" for pilot use?
- [clarification needed] Should season segmentation cap cycles per year (e.g., 1–3) or be fully data-driven?
- [clarification needed] What numeric false-alarm threshold defines "very low" for pilot use?

## Options (2–3 max per topic)
### Topic: Crop signal depth
- [option] Broad crop classes only (season + water demand)
  - Tradeoff: lower precision but more robust in small, mixed plots.
  - Evidence needed: stable class separability in Egyptian time series.
  - Decision trigger: class accuracy and stability exceed agreed threshold.
  - Kill condition: class instability causes frequent contradictions.
- [option] Attempt detailed crop types
  - Tradeoff: higher value if correct, higher risk of error and trust loss.
  - Evidence needed: reliable local ground truth or strong domain adaptation.
  - Decision trigger: access to labels and acceptable validation performance.
  - Kill condition: error rate damages credibility with users.
### Topic: Yield representation
- [option] Yield potential band (low/medium/high)
  - Tradeoff: less precise, safer for trust in early stages.
  - Evidence needed: correlation with outcomes at regional level.
  - Decision trigger: band shows predictive signal across pilot data.
  - Kill condition: no meaningful separation across bands.
- [option] Numeric yield estimate
  - Tradeoff: higher business value, higher trust risk if wrong.
  - Evidence needed: crop- and region-specific ground truth.
  - Decision trigger: validated model with acceptable error bounds.
  - Kill condition: variance too high for decision use.
### Topic: Time-series gaps + confidence
- [option] Smoothing + light interpolation with confidence penalty
  - Tradeoff: simple, fast, explainable; long gaps may still mislead trends.
  - Evidence needed: backtests show stable outputs in cloudy periods.
  - Decision trigger: trends remain consistent on known plots.
  - Kill condition: frequent false alerts in cloudy seasons.
- [option] Multi-source fusion or model-based imputation
  - Tradeoff: better continuity, higher complexity and risk of hallucinated signals.
  - Evidence needed: side-by-side error reduction with uncertainty maintained.
  - Decision trigger: reliable improvement without confidence drift.
  - Kill condition: outputs become less explainable for lenders.
### Topic: Boundary accuracy
- [option] Manual draw + light heuristics
  - Tradeoff: fastest MVP, minimal model training; precision varies by plot.
  - Evidence needed: pilot plots show stable outputs despite boundary noise.
  - Decision trigger: status/trend outputs stay consistent on sampled plots.
  - Kill condition: boundary noise flips decisions or risk flags.
- [option] Segmentation model for boundary refinement
  - Tradeoff: better plot purity, higher data and training cost.
  - Evidence needed: measurable reduction in false flags vs heuristics.
  - Decision trigger: precision gains without label burden stalling MVP.
  - Kill condition: cannot reach needed accuracy without local labels.
### Topic: Monitoring alerts
- [option] Conservative alerts only (high confidence)
  - Tradeoff: protects trust early, may miss subtle risks.
  - Evidence needed: pilot shows low false alarms with acceptable coverage.
  - Decision trigger: lenders accept alert volume and actions.
  - Kill condition: alerts are ignored or require heavy manual review.
- [option] Tiered alerts with severity bands
  - Tradeoff: richer signal, more UX and ops complexity.
  - Evidence needed: user testing shows clear comprehension.
  - Decision trigger: analysts prefer tiered review flow.
  - Kill condition: confusion or inconsistent actions.

## Roadmap
- Phase A: land assessment + lands-only portal + PDF export; minimal persistence only; pilot validation with low confusion and very low false alarms.
- Phase B: schema governance, QA gates, metadata/versioning discipline, regional calibration, confidence tuning, risk tiers, and monitoring readiness.
- Phase C: boundary refinement, crop taxonomy, yield bands, distillation, and advanced models.

## Exploration Gate
- MVP scope written
- Top open questions prioritized
- Options capped with evidence and decision triggers
