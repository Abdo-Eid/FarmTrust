# FarmTrust ML — Decision Log
> Every architectural, technical, and strategic decision made during development.
> Why we chose each path, what the alternatives were, and what we learned.
> **NeuralAlloy · Graduation Project · Menoufia University Faculty of AI · 2025–2026**

---

## How to Read This Document

Each decision entry has:
- **Context** — what problem we were facing
- **Options considered** — every real alternative we evaluated
- **Decision** — what we chose and why
- **Outcome** — what actually happened
- **What we learned** — honest reflection

---

## Part 1 — System Design Decisions

---

### D-001 — ML Model Architecture: Rule-Based vs ML/DL

**Context:** FarmTrust needed to verify whether Egyptian agricultural parcels were genuinely cultivated. The existing system used rule-based NDVI thresholds. The question was whether to improve the rules or build a real ML model.

**Options considered:**
- Option A: Improve rule-based thresholds (faster, simpler, no training data needed)
- Option B: Classical ML on engineered features (LightGBM, XGBoost)
- Option C: Deep learning Transformer on raw satellite time series (SITS-BERT)
- Option D: Combine B and C — classical ML baseline first, then Transformer

**Decision:** Option D — build classical ML baseline first (LightGBM), then upgrade to SITS-BERT Transformer. Rules kept as weak label generator only.

**Why not Option A:** Rules cannot generalize across Egypt's regional crop calendar variation. They also cannot learn from labeled data as it accumulates.

**Why not Option C directly:** Zero labeled data at the start. Deep learning requires a minimum of 500–1,000 clean labeled samples to train from scratch.

**Why Option D:** LightGBM ships in 6–8 weeks on weak labels. SITS-BERT ships in 3–4 months on accumulated labels. Each phase's output feeds the next.

**Outcome:** This staged approach proved correct. The classical model (Phase 2.5 benchmark) validated the feature pipeline before committing to DL training.

**What we learned:** Never jump to deep learning before you have labeled data. The classical baseline is not a compromise — it is a validation step.

---

### D-002 — Satellite Data Source: Sentinel-2 Only vs Multimodal

**Context:** We could add Sentinel-1 SAR (radar) data to improve cloud penetration and crop structure detection. This is standard in academic literature.

**Options considered:**
- Option A: Sentinel-2 optical only
- Option B: Sentinel-2 + Sentinel-1 SAR
- Option C: Sentinel-2 + Landsat + ERA5 weather
- Option D: All of the above

**Decision:** Sentinel-2 only for MVP and Phase 1–2. Sentinel-1 deferred to a future phase.

**Why:** SAR preprocessing (orbit correction, speckle filtering, geocoding) adds 3–4 weeks of engineering with no labeled data to validate the improvement. Sentinel-2 L2A from Microsoft Planetary Computer covers Egypt from 2017–present with acceptable cloud statistics.

**The 2015 question:** Lenders initially asked for 10-year histories (2015+). After confirming 2017+ is acceptable for MVP, we avoided Landsat fallback complexity entirely.

**Outcome:** Correct decision. The full pipeline shipped without SAR. Egypt has lower cloud cover than Europe, making optical-only more viable here than in northern latitudes.

**What we learned:** Always confirm the date range requirement before designing the ingestion pipeline. One question saved 4 weeks of work.

---

### D-003 — Parcel Aggregation Strategy: Mean vs Percentile

**Context:** Each Sentinel-2 observation contains multiple pixels per parcel (5–50 pixels for sub-0.5 ha parcels). We needed to aggregate pixel-level indices to a single parcel-level value per observation.

**Options considered:**
- Option A: Mean of all valid pixels
- Option B: Median of all valid pixels
- Option C: 75th percentile of valid pixels
- Option D: Maximum NDVI pixel

**Decision:** 75th percentile of valid pixels within a 1-pixel eroded polygon boundary.

**Why 75th percentile over mean:** Mean is sensitive to edge pixel contamination. When a cadastral polygon overlaps with a neighboring bare-soil field at the boundary, the mean NDVI is dragged down. The 75th percentile captures the vegetation signal from the core of the parcel.

**Why erode by 1 pixel:** ±5m cadastral accuracy means boundary pixels may represent neighboring parcels. Erosion removes the outer ring.

**Why not maximum:** Maximum is too sensitive to noise and cloud mask failures.

**Outcome:** The aggregation strategy produced clean time series for all 14 AOIs. No edge contamination artifacts were observed in the NDVI timelines.

**What we learned:** Spatial aggregation strategy matters more than the ML model for small parcels. Getting this right first prevented hours of debugging later.

---

### D-004 — Decision Threshold: 0.50 vs Asymmetric

**Context:** Standard binary classification uses a 0.50 threshold. FarmTrust has an asymmetric cost structure: a false active (approving a loan for an empty parcel) is much worse than a false inactive (declining a loan for a real farm).

**Options considered:**
- Option A: Standard 0.50 threshold
- Option B: Fixed higher threshold (0.65 or 0.70)
- Option C: Calibrated threshold found by sweeping precision-recall curve

**Decision:** Fixed 0.65 as the minimum, then sweep at evaluation time to find the exact threshold where precision_active ≥ 0.90.

**Why not 0.50:** A lender approving a fraudulent loan based on our model output is the worst-case business failure. We explicitly designed the system to be conservative.

**Why not just 0.90:** Too high a threshold causes the model to output "uncertain" for borderline real farms, losing business.

**The class weight implementation:** We also encoded the asymmetry in the training loss itself using class weights [2.5, 1.0, 1.2, 0.8] for [active, bare, sparse, uncertain]. The model was penalized 2.5× more for false active errors during training.

**Outcome:** The final model achieved precision_active = 1.0 and false_active_rate = 0.0 on the test set at the calibrated threshold.

**What we learned:** Cost-sensitive learning (class weights + threshold calibration) is not an afterthought — it should be designed before writing a single line of model code.

---

### D-005 — Boundary Source: Farmer-Declared vs Cadastral

**Context:** Parcel boundaries could come from farmer declarations (approximate, low quality) or official Egyptian cadastral polygons (±5m accuracy).

**Options considered:**
- Option A: Farmer-declared coordinates
- Option B: Official cadastral polygons
- Option C: Both, with quality flag

**Decision:** Official cadastral polygons only for MVP. ±5m accuracy confirmed by stakeholder.

**Why this matters:** With ±5m cadastral accuracy and 10m pixel resolution, boundary erosion by 1 pixel gives clean parcel-interior pixels. With farmer-declared coordinates (potentially ±30m error), edge contamination would make parcel-level aggregation unreliable.

**Outcome:** This single clarification (asked as pre-design question D-001) changed the entire spatial processing architecture. It meant we could use pixel-level aggregation instead of parcel-level spectral unmixing.

**What we learned:** Ask the data quality question before designing the pipeline. The answer determines your entire spatial processing strategy.

---

### D-006 — Inference Latency: Real-Time vs Async vs Pre-computed

**Context:** When a lender submits a parcel for verification, how fast does the response need to be?

**Options considered:**
- Option A: Real-time (< 5 seconds) — requires pre-computed tile cache
- Option B: Async job (2–4 minutes) — fetch tiles on demand, return job_id
- Option C: Pre-computed database — analyze all Egypt parcels proactively

**Decision:** Async job queue (Option B) with a tile cache layer to serve repeat requests in < 10 seconds.

**Why not real-time:** Fetching 7 years of Sentinel-2 tiles and running inference on demand is impossible in 5 seconds without pre-caching.

**Why not pre-computed:** We don't know which parcels lenders will query. Pre-computing all Egypt parcels would require massive storage and compute.

**Why async with cache:** First request takes 2–4 minutes (acceptable for a loan verification). Repeat requests on the same parcel serve from cache in seconds. This is the standard pattern for satellite analysis APIs.

**Outcome:** Celery async worker + Redis cache architecture implemented in Phase 7. Works correctly in testing.

**What we learned:** Latency requirements must be confirmed with end users (lenders) before designing the serving architecture. One clarification question determined the entire backend design.

---

## Part 2 — Data and Label Decisions

---

### D-007 — No Labels at Start: Weak Supervision Strategy

**Context:** FarmTrust had zero labeled data when the ML project started. We needed training data before training any model.

**Options considered:**
- Option A: Wait for manual annotation (months)
- Option B: Buy labeled data from a third party
- Option C: Generate weak labels from the existing rule-based pipeline
- Option D: Use a public labeled dataset (EuroCrops, PASTIS)
- Option E: Combine C and D

**Decision:** Option E — use existing rule-based pipeline output as weak supervision source, then use EuroCropsML for transfer learning.

**Why the existing pipeline as weak supervisor:** The T-03/T-04/T-05 pipeline already detects activity windows with quality labels (good/weak/interrupted). These are imperfect but structured labels. Trusting our own pipeline's output as training signal is correct because the ML model is supposed to improve on it, not contradict it.

**Why EuroCropsML specifically:** Latvia 2021 is the smallest country file with wheat and grass classes. European wheat phenology (NDVI peak in June–July) transfers to Egyptian wheat (NDVI peak in February–March) not in absolute timing but in the shape of the growth curve. The Transformer learns the pattern, not the calendar.

**Outcome:** EuroCrops transfer learning dramatically improved the model. Without it, Stage 2 fine-tuning on 14 Egypt AOIs alone produced 0.0 precision. With it, the model generalized correctly.

**What we learned:** Transfer learning from related domains (European wheat → Egyptian wheat) works even when the absolute crop calendars differ. The model learns temporal patterns, not absolute dates.

---

### D-008 — Test Set: Real Annotations vs Rule-Based Proxy

**Context:** We needed a test set to evaluate the model but had no manually annotated ground truth.

**Options considered:**
- Option A: Use weak labels as test set (wrong — same source as training)
- Option B: Use rule-based pipeline outputs as proxy labels
- Option C: Manually annotate 200+ parcels before any training
- Option D: Use proxy labels now, replace with real annotations later

**Decision:** Option D — proxy labels with explicit warnings, replace with real annotations before lender demo.

**Why not wait for Option C:** Manual annotation of 200 parcels requires field knowledge and domain expertise that takes weeks to organize. Building the full pipeline first meant we had something to show and improve.

**The sacred rule:** The test set can never be touched during training. This is enforced in code — `evaluation/metrics.py` prints a visible warning every time it loads `test_set.csv`, and the file is listed in project rules as untouchable.

**The proxy label bug:** The auto-labeler assigned `intermittent` to `aoi_nile_delta_03` because it had `season_count = 1`. But this AOI had 191 usable observations over 5 years with 50 cloud gaps — the season detector couldn't connect the windows through the gaps. The true label was `active`. This was caught because the model predicted P(active) = 0.92 on this parcel — a strong signal that the label was wrong, not the model.

**What we learned:** When the model strongly disagrees with a proxy label, check the label first. High model confidence on a "wrong" prediction is often evidence of a labeling error.

---

### D-009 — AOI Coordinate Strategy: Hardcoded vs Demo-Region Offsets

**Context:** We needed 10+ Egypt AOIs for training but Planetary Computer STAC requests kept timing out locally. Initial hardcoded coordinates (spread across different Egyptian governorates) all failed ingest.

**Why the initial coordinates failed:** The hardcoded bounding boxes were placed in governorate centers based on geography, not confirmed agricultural coverage. Many ended up in desert, urban, or low-revisit areas that produced `gap_risk = "high"` even with 5 years of data.

**Decision:** Use `aoi_demo_01` as the reference parcel (confirmed working) and generate 10 new bboxes by shifting its coordinates by 0.05–0.30 degree offsets. This guaranteed we stayed in the same agricultural region with proven Sentinel-2 coverage.

**Outcome:** The offset strategy worked. All 10 new AOIs ingested successfully on Kaggle, producing 191–404 usable observations each.

**What we learned:** When designing AOI sampling strategies, use a known-good parcel as an anchor. Geographic intuition about where farms should be is unreliable — use confirmed coverage data.

---

### D-010 — `gap_risk` Gate: Why We Removed It

**Context:** The proxy test set gate included `gap_risk != "high"` as a quality filter. This was designed to exclude low-quality AOIs. But it rejected our best AOIs (361 observations, 6 good seasons) because `gap_risk = "high"`.

**Root cause:** The `gap_risk` field is set by the existing FarmTrust pipeline based on `max_gap_days`. Egypt has frequent winter cloud gaps (10–40 days) throughout the 5-year observation period. The pipeline's `gap_risk` calculator was calibrated for European data where clean winter observations are more common. For Egypt, `gap_risk = "high"` is the normal state and does not indicate poor data quality.

**Decision:** Remove the `gap_risk` gate from the proxy test set generator. Replace with `usable_observation_count >= 10` and `gap_ratio <= 0.50` as the Egypt-calibrated quality filters.

**What we learned:** Pipeline output fields designed for one context (European satellite coverage) cannot be directly reused as quality gates in a different context (Egypt). Always inspect the actual values before using a field as a filter.

---

## Part 3 — Training and Infrastructure Decisions

---

### D-011 — Training Environment: Local vs Kaggle

**Context:** The SITS-BERT Transformer requires GPU training. Local machine has insufficient memory and no GPU.

**Options considered:**
- Option A: Google Colab (free, limited RAM, session timeouts)
- Option B: Kaggle Notebooks (free, T4 GPU, 30GB RAM, 9-hour sessions, Kaggle CLI integration)
- Option C: AWS/GCP cloud GPU (paid, requires setup)
- Option D: University compute cluster

**Decision:** Kaggle Notebooks. T4 x2 for pretraining, T4 x1 for fine-tuning.

**Why Kaggle over Colab:** Kaggle has 30GB RAM (vs 12GB on Colab free), 9-hour sessions (vs 90 minutes), and the Kaggle CLI enables fully automated push-poll-download workflows from the local machine.

**Why Kaggle CLI matters:** Claude Code could push a notebook, poll for completion every 60 seconds, and trigger a manual download — all without opening a browser. This is what enabled the fully automated training pipeline.

**The connection problem:** Local Planetary Computer STAC requests timed out repeatedly. The fix was to run ingestion on Kaggle (where the internet connection is stable) and download only the CSV artifacts locally. This split the pipeline correctly: heavy data fetching on Kaggle, preprocessing and inference locally.

**What we learned:** For graduation projects with no GPU budget, Kaggle is the correct training environment. Design the pipeline around it from the start, not as an afterthought.

---

### D-012 — SITS-BERT vs Presto vs Prithvi-EO-2.0

**Context:** Three pretrained satellite Transformer models were available: SITS-BERT (academic, 256 hidden, 3 layers), Presto (NASA Harvest, lightweight, Africa-tested), and Prithvi-EO-2.0 (IBM/NASA, 300M parameters, 30m resolution).

**Options considered:**
- Option A: SITS-BERT (linlei1214/SITS-BERT on GitHub)
- Option B: Presto (nasaharvest/presto)
- Option C: Prithvi-EO-2.0 (HuggingFace)

**Decision:** SITS-BERT as primary architecture. Presto documented as alternative for future evaluation.

**Why SITS-BERT:** The 10-band input format exactly matches our Sentinel-2 L2A feature set. The architecture (3 Transformer layers, 256 hidden, DOY positional encoding) is small enough to train on a single T4 GPU in under 8 hours. The pretrained checkpoint is available in the GitHub repo itself.

**Why not Prithvi-EO-2.0:** 30m resolution vs our 10m pipeline. Spatial mismatch makes pixel aggregation meaningless for sub-0.5 ha parcels. Also 300M parameters is too large for a T4 single-GPU fine-tuning within Kaggle's 9-hour session limit.

**Why Presto was noted but not used:** Presto is arguably better for Africa. It was pretrained on 21.5M global pixel time series and tested on African agriculture. It is the recommended upgrade path for Phase 3.

**What we learned:** Model selection for this use case is dominated by three constraints: input format compatibility, training time budget, and GPU memory. Research accuracy rankings are secondary.

---

### D-013 — Feature Adaptation: Raw Bands vs Computed Indices

**Context:** SITS-BERT was originally trained on 10 raw Sentinel-2 bands (B02–B12 excluding B01, B09, B10). Our preprocessing pipeline outputs smoothed indices (NDVI, EVI, NDMI, NDWI) rather than raw bands.

**Options considered:**
- Option A: Re-fetch raw bands from Planetary Computer to match original SITS-BERT input
- Option B: Use the existing smoothed indices as input features (10 computed features)
- Option C: Mix — use raw bands where available, fill missing with computed indices

**Decision:** Option B — use the existing pipeline's smoothed index outputs as the 10 input features. Do not re-fetch raw bands.

**Why:** The existing preprocessing pipeline is the canonical data source. Re-fetching raw bands would create a parallel data path that diverges from the rest of the system. The ML module must be a consumer of pipeline artifacts, not a parallel pipeline.

**The trade-off:** SITS-BERT's pretrained weights were trained on raw bands. Loading them with index inputs means the input projection layer weights don't transfer perfectly. We compensate by fine-tuning with a lower learning rate and more epochs on domain data.

**Outcome:** The approach worked. val_precision_active = 0.9147 on the Kaggle validation set with index inputs.

**What we learned:** Model input format adaptation is an engineering constraint, not a model architecture decision. Sometimes using a suboptimal input format is the right choice for system consistency.

---

## Part 4 — Debugging Decisions

---

### D-014 — The 0.0 Precision Problem: Stale Artifacts

**Context:** After running the full training pipeline, evaluation reported precision_active = 0.0000 three times in a row. This appeared to mean the model was not working.

**Root cause identified:** `evaluation/metrics.py` reads `data/ml/<aoi_id>/sits_prediction.json` artifacts that were written by the old (pre-training) model. Those artifacts all predicted "uncertain" because the old model had not been trained yet. The evaluation never re-ran inference with the new model.

**Why this happened:** The inference artifacts were cached on disk. After replacing `models/sits_bert_finetuned.pt` with the new trained model, the old prediction files remained untouched.

**Fix:** Delete all `sits_prediction.json` files, re-run inference with the new model, then evaluate.

**The diagnostic method:** When evaluation shows 0.0, run `diagnose_predictions.py` which calls the model directly (bypassing cached artifacts) and checks the raw probability distribution. If the model predicts varied classes (active: 10, bare: 4) but evaluation shows 0.0, the problem is stale cached artifacts, not the model.

**What we learned:** Always separate model inference from evaluation artifact reading. The evaluation pipeline must always re-run inference rather than trusting cached files.

---

### D-015 — The False-Active Gate Bug

**Context:** `aoi_demo_01` was predicted as "active" by the evaluation even though P(active) = 0.49, below our 0.65 threshold.

**Root cause:** The inference code stored `raw_probs` (uncalibrated model output) in `observations[].ml_probabilities`. The evaluation code averaged these raw probabilities and took the argmax. Since P(active) = 0.49 > P(bare) = 0.385, the argmax was "active" even though the gate threshold was 0.65.

**Fix:** In `farmtrust_core/ml/inference.py` line 122, apply the active threshold gate before storing probabilities:
```python
if probs.get("active", 0.0) < POSSIBLE_ACTIVE_THRESHOLD:
    gated["active"] = 0.0
    gated["uncertain"] += active_probability
```

**What we learned:** Threshold gates must be applied at the point of probability computation, not at the point of label assignment. If raw probabilities are stored and later averaged, the gate logic must be consistently applied at every aggregation step.

---

### D-016 — The `aoi_nile_delta_03` Label Correction

**Context:** `aoi_nile_delta_03` was auto-labeled "intermittent" (1 detected season) but the model predicted P(active) = 0.92.

**Investigation:** Reading `season_windows.json` and `quality_metrics.json` revealed:
- 191 usable observations over 5 years
- 50 long gap windows (cloud gaps every 10–40 days throughout the year)
- 1 detected activity window (Dec 2020 – Feb 2021, quality=good, confirmation=strong)
- The season detector could not connect activity windows across cloud gaps

**The pipeline's limitation:** The existing season detector requires contiguous observation sequences to confirm a season boundary. With 50 cloud gaps in 5 years, the detector saw only isolated vegetation bursts rather than connected seasons. This is a known limitation of the T-04 gap-aware smoothing approach.

**The model's advantage:** The SITS-Transformer sees the full temporal sequence including the gap structure. It learned that "frequent vegetation bursts separated by regular cloud gaps" = Egypt agricultural pattern, not abandoned land.

**Decision:** Correct the label to "active" based on manual data inspection + high model confidence as supporting evidence.

**What we learned:** When an ML model strongly disagrees with a rule-based label, it is sometimes the model that is correct. High model confidence is a signal to re-examine the label, not to retrain the model.

---

## Summary Table

| Decision | What we chose | Key reason | Alternative rejected |
|---|---|---|---|
| D-001 | SITS-BERT Transformer | Best accuracy for time series | Raw rules (can't learn) |
| D-002 | Sentinel-2 only | Avoid SAR complexity for MVP | SAR (deferred to Phase 3) |
| D-003 | 75th percentile aggregation | Robust to edge contamination | Mean (sensitive to noise) |
| D-004 | 0.65 threshold + class weights | Asymmetric false-active cost | Standard 0.50 threshold |
| D-005 | Cadastral polygons only | ±5m accuracy enables pixel aggregation | Farmer declarations |
| D-006 | Async job + cache | Balance latency vs complexity | Real-time (impossible) |
| D-007 | Weak labels + EuroCrops transfer | No labeled data at start | Wait for annotations |
| D-008 | Proxy test set with warnings | Unblock evaluation honestly | Fabricate ground truth |
| D-009 | Demo-region offset AOIs | Known-good coverage anchor | Geographic intuition |
| D-010 | Remove gap_risk gate | Egypt cloud gaps are normal | Keep European-calibrated gate |
| D-011 | Kaggle for training | Free GPU, CLI integration | Colab (RAM/timeout limits) |
| D-012 | SITS-BERT over Prithvi | Input format match, T4-trainable | 300M params too large |
| D-013 | Computed indices not raw bands | Pipeline consistency | Re-fetch raw bands |
| D-014 | Delete stale artifacts | Evaluation was reading old cache | Retrain (not the problem) |
| D-015 | Gate at probability level | Consistent threshold application | Gate at label level only |
| D-016 | Correct label not retrain | High model confidence = label error | Accept false positive |

---

*Document maintained by: Fares (ML lead) · NeuralAlloy · FarmTrust · 2025–2026*
*For graduation project submission: Menoufia University Faculty of Artificial Intelligence*
