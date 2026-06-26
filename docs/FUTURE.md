# FUTURE

Purpose: non-authoritative parking lot for possible future directions.

This file is not product scope, not roadmap, and not architecture truth. It preserves ideas without committing the team to them. Anything here must be re-evaluated before promotion into `PROJECT.md`, `ENGINEERING.md`, `DECISIONS.md`, or a live plan.

## Promotion Rules

- Treat every item as a hypothesis, not a commitment.
- Do not use this file to decide current-build scope.
- Promote an item only after user approval, evidence review, and an explicit update to the authoritative doc.
- If a future item becomes near-term work, create a live plan in `PLANS/`.
- If an item becomes a durable decision, record it in `DECISIONS.md`.

## Parked Product Ideas

- Schema governance, QA gates, metadata/versioning discipline, and reproducibility discipline.
- Regional calibration, confidence tuning, risk tiers, and monitoring readiness.
- Boundary refinement, crop taxonomy, yield bands, and advanced modeling.
- Monitoring alerts beyond conservative high-confidence flags.

## Parked Technical Ideas

- Replace some rules with classical ML such as RF/XGBoost on engineered features.
- Calibrate thresholds by region such as Delta, Valley, and Reclaimed land.
- Add confidence models such as probability calibration and uncertainty bands.
- Introduce a credit readiness layer as an aggregation of indicators.
- Revisit broad crop category only if validation evidence and trust requirements are met.
- Boundary refinement using a segmentation model such as U-Net or DeepLab trained on weak labels plus a small manual set.
- Encroachment detection using land-use change models with multi-year change maps.
- Crop taxonomy with weak labels and domain adaptation.
- Add water-demand class and season length class.
- Yield potential bands using multi-year productivity proxies and regional calibration.
- Multimodal fusion across optical, SAR, and thermal sources.
- Self-supervised pretraining on regional time series.
- Teacher-student distillation for Egypt-specific models.
- Queue/broker support when multi-user concurrency and reliability become active requirements.
- Postgres/PostGIS and object storage when production persistence, geospatial querying, or durable report/raster storage become active requirements.
- Neighbor comparison features, including trend-vs-neighbor signals and batched neighbor comparison performance work.
- Cropping-intensity features if current season and interval evidence is not enough for lender-facing decisions.
- Mosaic scenes before filtering when an AOI is only partially covered by individual tiles and full spatial continuity becomes a strict downstream requirement.

## Parked Options

### Crop signal depth

- [option] Attempt detailed crop types
  - Tradeoff: higher value if correct, higher risk of error and trust loss.
  - Evidence needed: reliable local ground truth or strong domain adaptation.
  - Decision trigger: access to labels and acceptable validation performance.
  - Kill condition: error rate damages credibility with users.
- [option] Skip crop category in the current build
  - Tradeoff: lower feature breadth, higher trust and lower ambiguity in the first lender-facing outputs.
  - Evidence needed: none for the current build; revisit only when regional labels and validation are available.
  - Decision trigger: decision-support outputs are stable and the team has enough crop evidence to add a coarse class safely.
  - Kill condition: crop output would distract from more reliable land-status and season evidence.

### Yield representation

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

### Time-series gaps and confidence

- [option] Smoothing plus light interpolation with confidence penalty
  - Tradeoff: simple, fast, explainable; long gaps may still mislead trends.
  - Evidence needed: backtests show stable outputs in cloudy periods.
  - Decision trigger: trends remain consistent on known plots.
  - Kill condition: frequent false alerts in cloudy seasons.
- [option] Multi-source fusion or model-based imputation
  - Tradeoff: better continuity, higher complexity and risk of hallucinated signals.
  - Evidence needed: side-by-side error reduction with uncertainty maintained.
  - Decision trigger: reliable improvement without confidence drift.
  - Kill condition: outputs become less explainable for lenders.

### Boundary accuracy

- [option] Manual draw plus light heuristics
  - Tradeoff: fastest path, minimal model training; precision varies by plot.
  - Evidence needed: pilot plots show stable outputs despite boundary noise.
  - Decision trigger: status/trend outputs stay consistent on sampled plots.
  - Kill condition: boundary noise flips decisions or risk flags.
- [option] Segmentation model for boundary refinement
  - Tradeoff: better plot purity, higher data and training cost.
  - Evidence needed: measurable reduction in false flags vs heuristics.
  - Decision trigger: precision gains without label burden stalling the current build.
  - Kill condition: cannot reach needed accuracy without local labels.

### Monitoring alerts

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

## Teacher-Student Distillation Note

- Collect global datasets such as crop maps, land-use, and time-series, then remove non-Egypt patterns.
- Train a large teacher model for generalized crop or behavior signals.
- Generate high-confidence pseudo-labels for Egypt.
- Train a smaller Egypt-specific student model through distillation.
- Use student outputs to improve accuracy and build higher-quality local datasets.

## Credit Readiness Layer Note

- Purpose: aggregate indicators into a lender-facing risk tier before a numeric score.
- Possible inputs: land status, trend, season performance, risk flags, confidence, neighbor comparison, and irrigation stability.
- Possible approach: start as weighted rules; transition to ML only when outcome labels are available.
- Guardrail: this remains decision support, not an automated financing decision.
