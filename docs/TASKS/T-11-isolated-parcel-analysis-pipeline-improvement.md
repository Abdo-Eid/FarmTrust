# T-11 — Isolated Parcel Analysis to Pipeline Improvement

## Goal

Use the isolated one-parcel analysis directory as evidence to improve the FarmTrust land-assessment pipeline.

The main goal is not to make the LLM report assistant smarter. The main goal is to compare what the current production pipeline does against what the isolated parcel-analysis work found, identify unbiased gaps, and turn validated findings into better ingestion, preprocessing, activity-window, scoring, confidence, and reporting behavior.

## Scope

### IN

- Inventory the copied isolated parcel-analysis directory: notes, prompts, notebooks, scripts, charts, raw data, generated outputs, and conclusions.
- Map each useful finding to the current pipeline stage: ingestion, preprocessing, activity-window detection, scoring/risk flags, confidence/evidence, API contract, portal/reporting.
- For each mapped finding, record a side-by-side comparison:
  - **Current pipeline has:** what this repo currently computes, stores, exposes, or displays.
  - **Isolated parcel work has:** what the external analysis computed, observed, inferred, or proposed.
  - **Neutral comparison:** agreement, disagreement, missing evidence, different assumptions, or incompatible time windows.
  - **Pipeline implication:** no change, documentation/reporting change, rule change, data-processing change, validation case, or open question.
- Use the parcel as an informal reference case for better assessment-window, season-context, land-status, abandonment, trend, and confidence rules. A formal validation harness is deferred until the pipeline stabilises.
- Identify whether any LLM interpretation notes are useful only for explanation/reporting versus useful for core pipeline logic.

### OUT

- Treating the isolated parcel work as automatically correct.
- Changing scoring rules before the comparison is documented and evidence is understood.
- Expanding the LLM assistant into an open-ended analyst or decision-maker.
- Adding crop-yield, loan-approval, legal-boundary, pest, or crop-type claims unless supported by existing pipeline evidence and approved scope.
- Replacing existing active tasks T-09, T-10, or T-04; this task should connect to them and may spawn or refine implementation work.

## Role Split

- Driver: inspect the copied directory, build the comparison ledger, and propose pipeline changes.
- Reviewer: challenge bias, overfitting to one parcel, unsupported LLM interpretations, and hidden assumptions in both systems.
- Curator: promote only durable pipeline knowledge into `ENGINEERING.md`, decisions into `DECISIONS.md`, and product/report wording into `PROJECT.md` when needed.

## Chosen approach

Use an evidence-first comparison ledger.

Each isolated-directory finding must be compared against the current pipeline without assuming either side is right. The comparison should preserve exact evidence: file path, artifact, chart, metric, date window, method, and conclusion. Differences should be classified before implementation.

The expected implementation path is likely to refine T-09 and T-10 first: configurable assessment windows, season-context interpretation, short-window-safe land status rules, abandonment semantics, trend confidence, and evidence limitations. T-04 may be enhanced later only if the report assistant needs better grounded inputs from the improved pipeline.

## Work checkpoints

### Checkpoint 1 — Inventory only

Record every file under `outputs/exploration/`, including figures. Classify each file as script, methodology note, analysis report, visualization, template, or generated artifact. Do not judge conclusions yet.

### Checkpoint 2 — Evidence extraction

Extract concrete claims and observations from the isolated parcel work. Label each as measured evidence, code-derived method, visual interpretation, LLM/narrative interpretation, or recommendation.

### Checkpoint 3 — Stage mapping

Map each extracted item to the current FarmTrust stage it touches: ingestion, preprocessing, activity-window detection, scoring/risk flags, confidence/evidence, API contract, portal/reporting, or assistant.

### Checkpoint 4 — Neutral comparison ledger

For each mapped item, write the unbiased comparison:

- **Current pipeline has:** exact repo evidence.
- **Isolated parcel work has:** exact `outputs/exploration/` evidence.
- **Neutral comparison:** agreement, disagreement, different assumption, missing evidence, or incompatible window.
- **Pipeline implication:** no change, doc/reporting change, rule change, processing change, validation case, or open question.

### Checkpoint 5 — Small implementation slices

Only after the ledger is written, split changes into small follow-up slices. Prefer refining existing tasks T-09, T-10, and T-04 where appropriate instead of creating broad implementation work.

## Checkpoint Log

### Checkpoint 1 — Inventory v0

Directory inspected: `outputs/exploration/`.

Top-level files:

| File | Type | What it contains |
|---|---|---|
| `outputs/exploration/analyze.py` | Script | Field-mean analysis pipeline: QC, weighted Whittaker smoothing, multi-peak phenology, crop labels from notes, chart generation, HTML token injection. |
| `outputs/exploration/cube_explore.py` | Script | Direct Zarr cube decoding without `zarr`/`xarray`, CSV-vs-cube NDVI validation, spatial peak maps, winter-zone maps, cut-log prototype. |
| `outputs/exploration/cube_figs.py` | Script | Regenerates pixel-level figures from clean cube, including NDVI maps, cut sweep, NDRE comparison, and CSV validation. |
| `outputs/exploration/hmm_phenology.py` | Script | Standalone 4-state Gaussian HMM implementation for LOW/RISING/HIGH/DECLINING phenology states. The file includes a synthetic demo; the report says it was used as a cross-check on the parcel. |
| `outputs/exploration/menofia_analysis_process_report.md` | Analysis report | Full process report, post-mortem, final parcel findings, mistakes corrected, scaling notes, band recommendations, NDRE/MSAVI/HMM updates. |
| `outputs/exploration/cross_team_brief_satellite_subsystem.md` | Integration brief | Separates built one-field work from designed/discussed future work; describes data contract and crossing points. |
| `outputs/exploration/lender_methodology_monitoring.md` | Methodology/spec | Lender-oriented inference ladder, confidence model, absence gate, baseline/neighbor logic, snapshot and monitoring alert rules. |
| `outputs/exploration/lender_land_use_card.html` | Generated lender card | Lender-facing one-parcel snapshot with Observed/Interpreted/Confidence/Watch, activity record, track record, risk register, boundaries, monitoring alerts. |
| `outputs/exploration/report_template.html` | HTML template | Technical phenology report layout with token placeholders for computed cards, insights, rows, and figures. |
| `outputs/exploration/menofia_ndvi_report.html` | Generated technical report | Self-contained technical parcel report with embedded charts and final numbers. |

Figures under `outputs/exploration/figs/`:

| Files | Figure group |
|---|---|
| `f1_timeline.png`, `f2_quality.png`, `f3_veg.png` | Phenology timeline, acquisition quality, NDVI/EVI/NDMI relationship. |
| `f4_yoy.png`, `f5_hetero.png`, `f6_corn.png` | Year-over-year NDVI, field uniformity, corn/FAW comparison. |
| `f7_spatial_peaks.png`, `f8_zones.png`, `f9_validation.png` | Raw-pixel peak maps, within-field winter/summer spatial structure, CSV-vs-cube validation. |
| `f10_cuts.png`, `f11_sweep.png` | Berseem cut-log and moving cut-front. |
| `f12_ndre.png`, `msavi_vs_ndvi.png`, `f14_hmm.png` | NDRE, MSAVI, HMM cross-check outputs. |
| `f4_water.png`, `f5_yoy.png`, `f6_hetero.png` | Older/superseded or alternate figure outputs. Keep as evidence but do not treat as final without matching script/report context. |

### Checkpoint 2 — Extracted Evidence v0

Parcel/source assumptions from `outputs/exploration/`:

| Item | Evidence |
|---|---|
| Parcel | One field in Menofia governorate, Nile Delta, Egypt; `AOI demo 01`; about 0.9 ha. |
| Source | Sentinel-2 L2A, MGRS tiles `36RTU` / `36RUU`, 10 m root grid with 20 m red-edge/SCL group. |
| Date window | Final report/card use `02 May 2024 -> 19 Jun 2026` (`2.1 yr`). `menofia_analysis_process_report.md` line 4 has an older `21 Jun 2024 -> 19 Jun 2026` statement, later corrected in section 16. |
| Observations | 280 acquisitions, 248 clean in final report/card; process notes also mention earlier 262/231 and stale/corrupt mount cases. |
| Source artifacts | Source parcel artifacts are present under `data/aoi_demo_01/`: `indices_timeseries.csv`, `run_metadata.json`, `scenes_index.jsonl`, `cube.zarr/`, and `weather_daily.parquet`. Exact equivalence to every isolated run still needs explicit rerun/comparison because the copied `outputs/exploration/` include stale/intermediate notes. |

Concrete findings from the isolated work:

| Finding | Type | Evidence |
|---|---|---|
| The parcel is double-cropped at about 1.9-2.0 cycles/year. | Measured + interpreted | `menofia_ndvi_report.html` cards and cycle table; `menofia_analysis_process_report.md` section 4. |
| Four cycles were identified: 2024 corn, 2024/25 wheat+berseem, 2025 corn, 2025/26 berseem. | Measured + ground-truth-labelled | `menofia_ndvi_report.html` cycle table lines 73-76; labels rely on grower notes. |
| SOS/POS/EOS are estimated from 20% of per-cycle amplitude, with planting windows inferred as SOS minus 1-3 weeks. | Code-derived method | `outputs/exploration/analyze.py` lines 92-100 and report template method paragraph. |
| Quality filtering used `valid_fraction >= 0.5`, then quality-weighted Whittaker smoothing on a daily grid with lambda 3000. | Code-derived method | `outputs/exploration/analyze.py` lines 31, 41, 45-52; `menofia_analysis_process_report.md` sections 3.1, 3.2, 16. |
| Lambda 6000 over-smoothed a real bare-soil trough; lambda 3000 preserved crop-turnover troughs. | Process lesson | `menofia_analysis_process_report.md` section 16. |
| Raw cube validation reproduced CSV NDVI with r about 0.94 and near-zero bias. | Measured validation | `outputs/exploration/cube_explore.py` lines 29-34; `outputs/exploration/cube_figs.py` lines 57-65; report sections 11 and 8. |
| Within-field winter variability was ultimately interpreted as a moving berseem cutting pattern, not a static wheat/berseem boundary. | Visual interpretation corrected by ground truth | `menofia_analysis_process_report.md` section 11; `report_template.html` lines 107-118. |
| Berseem cut count is about 5 per pixel for 2025/26, a floor because revisit and saturation miss some cuts. | Measured + interpreted | `menofia_analysis_process_report.md` section 11; `menofia_ndvi_report.html` section 9. |
| NDRE tracks NDVI closely (r about 0.99) and did not reveal Fall Armyworm damage, but helps where NDVI saturates in dense canopy. | Measured + limitation | `menofia_analysis_process_report.md` section 15; `menofia_ndvi_report.html` section 10. |
| MSAVI tracks NDVI closely (r about 0.98), preserves same phenology, and provides a cleaner bare-soil/fallow floor. | Measured + recommendation | `menofia_analysis_process_report.md` section 17; `menofia_ndvi_report.html` section 11. No generation script was found in `outputs/exploration/` for `msavi_vs_ndvi.png`. |
| HMM recovered the same four crop cycles as the threshold method, with about 4 d start and 1 d end agreement. | Cross-check | `outputs/exploration/hmm_phenology.py`; `menofia_analysis_process_report.md` section 18; `menofia_ndvi_report.html` section 12. |
| MNDWI never exceeded about -0.30, so no standing-water/rice signal was found. | Measured + interpretation | `menofia_ndvi_report.html` insight list and `menofia_analysis_process_report.md` sections 4 and 12. |
| Fall Armyworm/yield damage was not visible in NDVI or NDRE at this scale. | Limitation | `menofia_analysis_process_report.md` sections 5.4 and 15; `lender_methodology_monitoring.md` hard boundaries. |
| Lender output should show inference ladder and boundaries: measured, pattern, labelled, judgment; Observed -> Interpreted -> Confidence -> Watch. | Reporting/methodology | `lender_methodology_monitoring.md` sections 1 and 5; `lender_land_use_card.html`. |
| Absence/idle claims require an expected crop window plus clean-look gaps tighter than a crop green-up could hide in. | Scoring principle | `lender_methodology_monitoring.md` section 3. |
| Neighbor baseline is needed before field-specific productivity decline alarms. | Monitoring/scoring principle | `lender_methodology_monitoring.md` sections 4 and 6. |

### Checkpoint 3/4 — Neutral Comparison Ledger v0

This is an initial ledger from available `outputs/exploration/` artifacts, current repo code/docs, and the source parcel artifacts now present at `data/aoi_demo_01/`. It is not final calibration: the Menofia parcel is one evidence case, useful for design and sanity checks, but not enough to tune global thresholds or prove smoothing behavior across regions.

| Topic | Current pipeline has | Isolated parcel work has | Neutral comparison | Pipeline implication |
|---|---|---|---|---|
| Data integrity gate | `farmtrust_core/ingest/cube_pipeline.py:347` validates cube time, 20 m time, ledger days, and CSV rows. | `outputs/exploration/analyze.py:15-30` refuses to build if CSV rows do not match cube root/20 m time. | Strong agreement. Isolated work independently found the same stale-artifact failure mode. | Keep/strengthen artifact consistency as a first-class gate; expose failures clearly in job/report logs. |
| Source data availability | `data/aoi_demo_01/` contains `indices_timeseries.csv`, `run_metadata.json`, `scenes_index.jsonl`, `cube.zarr/`, and `weather_daily.parquet`. | Reports/scripts reference source artifacts and also contain stale/intermediate notes from earlier mounts/runs. | We can inspect or rerun from repo-local source artifacts, but exact equivalence to each isolated output still needs explicit comparison. | Use the parcel as an informal reference case only for now; no formal regression harness in this pass. |
| Ingestion/index set | Ingest computes NDVI, EVI, NDMI, NDWI, MNDWI means/p95 in `cube_stats.py`; cube loader supports red-edge bands and B12 in `cube_loader.py`. | Isolated work uses same base indices plus NDRE from B8A/B05 and MSAVI2 from red/NIR. | Production can store red-edge bands but does not compute/export NDRE/MSAVI in `indices_timeseries.csv`. | Candidate processing change: add optional NDRE/MSAVI stats after deciding contract and tests. |
| Quality threshold | Preprocess marks usable anchors at `valid_fraction >= 0.90` (`pipeline.py:34`, `pipeline.py:185-188`). | Isolated analysis keeps `valid_fraction >= 0.5` and weights by valid fraction. | Different objective. Current threshold is conservative for trust; isolated threshold preserves more observations for dense time-series reconstruction. Neither is automatically right. | Run an A/B smoothing comparison on the parcel before changing threshold. Possible split: confidence gate remains strict, analysis smoother uses weights. |
| Smoothing method | Linear fill between usable anchors then Savitzky-Golay on observed timestamps; no synthetic timestamps (`smoothing.py`). | Weighted Whittaker smoother on a daily grid, lambda 3000, gap-fills and denoises together. | Both intentionally fill a continuous curve while keeping gaps as confidence evidence. Isolated work argues Whittaker preserved phenology after tuning; current docs explicitly rejected Whittaker earlier because of user preference and demo behavior. | Do not switch globally yet. Add comparison harness and evaluate preservation of troughs, peaks, and cut-like saw-tooth suppression. |
| Daily grid vs observed timestamps | Current smoother does not create synthetic timestamps; seasonal detection runs on observed timestamp rows. | Isolated smoother creates a daily grid for analysis and uses daily SOS/EOS estimates. | Daily grid gives cleaner phenology dates; observed-only avoids inventing days. Both can be acceptable if confidence and interpolation policy are explicit. | Consider a separate phenology-analysis curve with daily outputs while preserving raw observation truth. |
| Activity boundaries | Current activity windows use hybrid threshold plus relative boundary/promenence; `BOUNDARY_PROMINENCE_FRACTION = 0.20`. | Isolated cycles use peak/trough and 20% of per-cycle amplitude. | Good conceptual alignment on field-relative boundaries. Production naming says activity windows, not agronomic seasons. | Reuse current boundary concept; improve exposed metrics rather than replacing detection first. |
| Edge-cycle handling | Current detector supports `open_left`, `open_right`, `open_both` lifecycle statuses and provisional boundaries. | Isolated work added explicit edge-cycle handling after missing summer 2024. | Alignment. The isolated parcel is a useful regression for start/end censored cycles. | Add regression once source data or synthetic equivalent exists. |
| Cycle feature richness | Current internal `SeasonWindow` has start/peak/end, duration, peak NDVI, amplitude, baseline, confirmation, gap overlap; scoring adds AUC and EVI/NDMI/NDWI summaries internally. API exposes only slim `SeasonRecord`. | Isolated report exposes SOS/POS/EOS, duration, peak NDVI, amplitude, greenness sum, crop label, estimated planting window. | Production computes many of the necessary fields but drops them in API/portal mapping. Crop labels and planting estimates are extra inference. | First improvement can be contract/report exposure, not new math. Crop labels should stay optional/ground-truth/calendar-gated. |
| Crop identity | Current product decision defers crop category; docs say current contract avoids crop category. | Isolated labels use Delta calendar plus grower notes. | No conflict if isolated labels are treated as field-note annotations, not automated crop classification. | Keep crop identity out of automated core status unless user-approved scope changes. Could support optional user-provided crop notes later. |
| Land status vocabulary | Current API: `active`, `intermittent`, `inactive`; scoring uses recent windows and activity coverage. | Isolated lender card: `Actively double-cropped`, `Single-cropped`, `Idle/fallow`, `Unclear`. | Current vocabulary is simpler but loses cropping intensity. Isolated vocabulary is more lender-readable but needs scope/contract work. | Add cropping intensity/cycle-count evidence without renaming current core fields immediately. |
| Abandonment/idle semantics | Current mapper turns any risk code containing `inactivity` into `abandonment` (`assessment_mapper.py:49-61`). T-10 already identifies this as too aggressive. | Isolated methodology says idle/fallow requires an absence gate, and idle is not abandonment. | Strong disagreement with current public flag mapping. Isolated principle matches T-10 concern. | High-priority rule/mapper fix: separate `idle/fallow`, `insufficient_history`, and `abandonment`. |
| Short-window interpretation | T-09 documents current fixed lookback and need for window configuration; T-10 documents short-window false abandonment risk. | Isolated work shows window boundaries matter: extending start to 2 May 2024 changed a partial corn cycle into a full cycle. | Strong agreement that assessment windows affect classification and interpretation. | T-09 and T-10 should be connected to this parcel as validation evidence. |
| Trend/track record | Current trend compares first/last activity windows and can output improving/stable/declining/uncertain. | Isolated lender card says 2 years is a baseline, not certifiable trend; track record shown as `2 of ~5 seasons`. | Current trend may sound more definitive than isolated lender methodology would allow. | Add track-record/evidence-age framing; cap or label trend as provisional for short history. |
| Confidence model | Current confidence components: continuity, activity-window clarity, signal strength; evidence coverage caps confidence. | Isolated confidence adds data sufficiency, signal clarity, repetition, corroboration, per-claim confidence, absence gate. | Compatible. Isolated work is a richer presentation and adds absence-specific confidence. | Expose confidence components and per-claim confidence in report DTO/portal before adding LLM explanations. |
| Risk flags vs risk register | Current risk flags are compact codes/severity and portal maps only waterlogging/salinity/abandonment/encroachment. | Isolated risk register includes yield invisible, short record, crop-character change, small parcel, no peer baseline. | Current flags mix land-condition semantics with activity/inactivity. Isolated register distinguishes limitations from land risks. | Split land risk flags from evidence limitations/watch items. Avoid mapping evidence caveats to land defects. |
| Moisture/water interpretation | Current pipeline computes NDMI/NDWI/MNDWI but API exposes little beyond median NDMI/NDWI internally. | Isolated report uses NDMI for summer moisture watch and MNDWI to rule out rice/flooding. | Current data supports this partially, but product scope avoids crop/rice claims. | Expose moisture/water evidence cautiously as indicators/limitations, not definitive crop claims. |
| Spatial/pixel evidence | Current cube stores pixels, but API/portal report uses field-level series only; maps do not show true raster evidence. | Isolated work decodes raw pixels for peak maps, uniformity, cutting sweep, validation overlay. | Production has source data but no pixel-level report artifact pipeline. One parcel may not justify full raster UI yet. | Defer full maps; consider cheap numeric spatial features first: mean-p95 gap, p95 series, within-field spread. |
| Field uniformity | Current ingestion computes p95 for indices, but preprocess/API mostly use means and do not expose mean-vs-p95 spread. | Isolated uses NDVI mean-vs-p95 gap to discuss patchiness/mixed stand and field uniformity. | Current pipeline already has raw p95 but drops it before reporting. | Good minimal improvement: carry p95/spread into preprocessing/report DTO as field-uniformity evidence. |
| Pest/yield claims | Current docs forbid yield/pest claims; T-04 guardrails include no pest/yield claims. | Isolated explicitly says FAW/yield damage was not visible in NDVI/NDRE. | Strong agreement. Isolated parcel is a useful example for guardrails. | Add as report/assistant guardrail example, not as a detection feature. |
| Neighbor baseline | Current API has `neighbor_comparison: avg` placeholder; FUTURE parks neighbor comparison. | Isolated methodology says productivity decline alarm needs own history and neighbors. | Current placeholder can mislead because no neighbor computation exists. | Replace placeholder with unavailable/null until neighbor baseline exists; keep neighbor baseline as future/monitoring task. |
| Monitoring | T-03 exists as monitoring-layer planning; current jobs are one-off assessments. | Isolated methodology has alert rules but says live monitoring is designed, not built. | Agreement: not built. | Do not build monitoring inside this task; use findings to refine T-03 later. |
| Report/portal evidence ladder | Current portal has summary/evidence/PDF, confidence, flags, indicators, NDVI/EVI chart, season table. | Isolated card has Observed/Interpreted/Confidence/Watch, risk register, boundaries, track-record gauge, monitoring alerts. | Mostly reporting/API gap. Current DTO is too compressed for isolated explanation style. | Add structured report evidence packet before or alongside T-04 assistant. |
| LLM/assistant role | T-04 plans grounded explanation only, no score creation. | Isolated narrative translated measurements through remote-sensing/analyst/agronomist roles. | Useful style, but some interpretations rely on grower ground truth and should not become automated facts. | T-04 should consume a richer grounded packet and label measured vs interpreted vs user-provided notes. |

### Checkpoint 5 — Candidate Small Slices v0

These are candidate or decided implementation slices, not yet implemented:

1. **Parcel reference slice:** use `data/aoi_demo_01/` as an informal manual reference for comparison. Do not add a formal regression harness now; a future validation harness can use invariant checks only if the pipeline stabilises.
2. **Short-window/status-vocabulary slice:** implement T-10 mapper/scoring fixes: no `possible_inactivity` -> `abandonment` mapping without sufficient history and an absence gate. Separate current activity status from history coverage, e.g. one good observed cycle becomes `active` with `limited_history`, not stable long-term performance. Add absence-gate outputs such as `activity_present`, `absence_supported`, `absence_uncertain`, and `not_assessed`.
3. **Phenology feature exposure slice:** expose richer activity-window/cycle metrics already computed internally: peak date, start/end certainty, amplitude, AUC/greenness sum, lifecycle status, confirmation level, gap overlap, broad calendar label such as summer/winter where available.
4. **Additional indicators slice:** carry NDVI p95/spread, existing EVI, NDMI, and MNDWI through preprocessing/reporting as cautious evidence signals. Use p95/spread for field uniformity/patchiness, NDMI for moisture watch, MNDWI for surface-water/flooding signal, and EVI for vegetation confirmation. Do not claim crop type, pest, yield, income, or certainty from these indicators.
5. **Season-analysis curve slice:** keep strict valid observations, but adopt isolated-style smoothing and a reconstructed analysis curve for season/activity-window detection only. Gap analysis remains based on real usable observation timestamps, and synthetic/model-derived curve values must not be treated as direct evidence outside the season-analysis module.
6. **Index expansion slice:** defer NDRE/MSAVI to later work after confirming band availability and contract shape. NDRE is valuable for dense-canopy headroom/vigour/nitrogen/stress context where NDVI saturates, but the isolated report showed it is not a Fall Armyworm detector or yield detector at 20 m. MSAVI may help bare-soil/early-onset interpretation later.
7. **Report evidence-packet and HTML report slice:** define a DTO/report packet with Observed/Interpreted/Confidence/Watch, boundaries, watch items, limitations, local context, and per-claim confidence. Render it as a polished HTML-style report/card experience like the isolated `outputs/exploration/` HTML artifacts, separate from PDF. Later LLM wording may affect the narrative, but only from grounded packet fields.
8. **Spatial evidence slice:** carry numeric spatial evidence now, especially mean, p95, and mean-vs-p95 spread for field uniformity/patchiness. Add a small number of selected static visuals later when they are both useful and visually compelling. Defer full pixel-map workflows and interactive raster maps.

### Audit Follow-up — Provenance and Rerunnable Outputs

Decision: report visuals shipped to users require **Level 3 provenance minimum**. Core scoring/status logic should target Level 4 provenance.

The isolated work is valuable evidence, but some outputs were created during exploratory/inline analysis and are not yet fully production-rerunnable. This does not make them wrong; it means they must be labelled correctly before being used in production report surfaces or assistant responses.

| Level | Name | Meaning | Allowed use |
|---|---|---|---|
| 0 | Narrative-only | Finding appears in a report/note, but there is no committed artifact or generation path. | Context only. Do not ship as a report fact or visual. |
| 1 | Artifact-only | PNG/HTML/CSV exists, but the generator, inputs, or parameters are unclear. | Manual/reference evidence only. Assistant may mention with caveat. |
| 2 | Scripted research | Script exists, but assumptions, paths, parameters, or rerun steps are manual/unclear. | Internal research and comparison. Not enough for shipped visuals. |
| 3 | Rerunnable artifact | Script, input path, parameters, output path, and run steps are documented and committed. | Minimum for user-facing report visuals and selected static maps. |
| 4 | Pipeline artifact | Produced by the FarmTrust pipeline with metadata/versioning and stable output contract. | Required/preferred for core packet fields, scoring, status, confidence, and repeated production use. |

Current implications:

- `msavi_vs_ndvi.png` is useful isolated evidence, but no committed generator was found in `outputs/exploration/`; keep it below shipped-visual status until rerunnable.
- `f14_hmm.png` / HMM cross-check are useful supporting research, but `outputs/exploration/hmm_phenology.py` includes a standalone synthetic demo and does not by itself prove a production-rerunnable parcel HMM path.
- Selected static report visuals, such as a cycle peak map or winter variability/cut-front figure, must be promoted to Level 3 before they appear in the polished HTML/card report.
- Evidence-packet fields used by scoring/status/confidence should be Level 4 whenever possible.
- If a user or assistant references Level 0-2 items, wording must say `isolated analysis suggested`, `research cross-check`, or `manual/context evidence`, not `production result`.

### Audit Follow-up — LLM Provenance Rules

T-11 owns the evidence-packet metadata. T-04 owns the assistant/chat implementation and guardrail tests. The packet must make provenance visible enough that T-04 can enforce safe assistant behavior.

Every assistant-consumable claim should carry metadata similar to:

| Field | Purpose | Example |
|---|---|---|
| `claim` | Human-readable assertion. | `Four vegetation activity cycles were detected.` |
| `claim_type` | What kind of statement it is. | `deterministic_pipeline_result` |
| `provenance_level` | Provenance ladder level. | `4` |
| `source` | Artifact or packet field. | `season_windows.json` / `report_evidence_packet.json` |
| `method` | How it was derived. | `deterministic_activity_cycle_detector` |
| `allowed_use` | Where the claim may be used. | `report`, `chat`, `status_explanation` |
| `restriction` | What must not be said. | `do_not_infer_crop_identity_or_yield` |
| `confidence` | Claim confidence or evidence quality. | `strong`, `moderate`, `limited` |

Claim-type vocabulary:

| Claim type | Meaning | Assistant behavior |
|---|---|---|
| `measured_observation` | Direct field, index, or artifact value from real observations. | Can state with source/caveat. |
| `deterministic_pipeline_result` | FarmTrust pipeline output from stable logic. | Can state as the system result. |
| `model_derived_analysis` | Derived from smoothing/reconstructed curve or model output. | Can explain, but must say estimated/model-derived where relevant. |
| `isolated_research_cross_check` | Result from isolated analysis not yet production-rerunnable. | Mention only as supporting research, not production validation. |
| `user_provided_local_context` | Grower/user/local knowledge. | Label as user-provided/local context. |
| `hypothesis` | Plausible explanation not proven. | Must use tentative wording and alternatives. |
| `unknown` | Not enough evidence. | Say unknown; do not fill gaps. |

Assistant-specific rule for provenance:

- Level 3-4 claims can support report narration and chat answers.
- Level 2 claims can support cautious research/context explanations.
- Level 0-1 claims can only be mentioned with explicit caveat and must not become system facts.
- LLM output is never evidence by itself; it is a rendering/analysis over the packet.
- Store generated LLM text with evidence-packet version/hash, provider/model, prompt version, timestamp, and guardrail result when assistant implementation starts in T-04.

Safe answer example for HMM:

```text
The isolated analysis reported an HMM cross-check that matched the four-cycle interpretation, but the exact production-rerunnable HMM generation path is not yet documented. Treat it as supporting research evidence, not production validation.
```

### Selected Season/Activity-Cycle Detector Approach

Decision: use the current deterministic FarmTrust detector as the production backbone, align it with the isolated peak/trough and per-cycle amplitude approach, and keep HMM as validation/future work.

Chosen approach:

| Component | Decision |
|---|---|
| Backbone | Deterministic FarmTrust activity-window/cycle detector. |
| Input signal | Strict valid observations plus isolated-style smoothing and reconstructed/model-derived analysis curve for season analysis only. |
| Boundaries | Align with isolated method: use peak/trough structure and per-cycle amplitude boundaries such as 20% of cycle amplitude for SOS/EOS estimation. |
| Lifecycle | Preserve current `complete`, `open_left`, `open_right`, and `open_both` lifecycle states. |
| Confidence | Use real-observation gap analysis and boundary support metadata; synthetic/model-derived dates must not be direct evidence. |
| Labels | Expose vegetation activity cycles and broad summer/winter calendar descriptors only; do not infer crop identity. |
| HMM | Keep as optional research validation/cross-check until its parcel workflow is Level 3+ rerunnable and production-proven. |

This means the implementation should not replace the production detector with HMM, and should not blindly copy the isolated script. It should evolve the existing deterministic detector so it can run on the reconstructed analysis curve and produce better cycle boundaries while keeping FarmTrust's explainability, lifecycle statuses, and confidence model.

Implementation detail to preserve:

- The detector may use model-derived daily/regular curve points for cycle shape and estimated boundaries.
- The detector must retain nearest-real-observation support for important boundaries where feasible.
- Gap/confidence calculations remain based on real usable observation timestamps.
- If a boundary is estimated from synthetic/model-derived curve points, the report should say estimated/model-derived, not observed.
- HMM can be used later to check whether the deterministic detector is missing cycles, but it is not a production source of truth now.

## Decision Walkthrough

Use this list for point-by-point discussion with the user. Do not implement until decisions are taken for the relevant points, then make changes in one planned pass.

| # | Point | Brief | Decision status |
|---|---|---|---|
| 1 | Validation baseline | Decide whether `data/aoi_demo_01` becomes the official regression parcel for pipeline changes. It is the same source cube/CSV used by the isolated analysis and can test cycle count, no false abandonment, evidence coverage, and report output. | **Decided: skip for now** — constant research/iteration means golden-file regression would fight us. A validation harness (invariant checks, no false abandonment, runs without crash) could come later when pipeline stabilises. Refer to `data/aoi_demo_01` informally for now. |
| 2 | Assessment window | Decide how much control the user gets over start/end dates and whether season/calendar guidance is part of the first fix. The isolated work shows window boundaries can change whether a cycle is partial or complete. | **Decided: general first** — use a dropdown-first assessment-window experience, with a possible calendar view. For now, use general observed seasons/activity windows from the latest observations. If a season is incomplete at the assessment end date, keep it explicitly incomplete instead of forcing a full-season interpretation. Explicit custom dates can remain an advanced option later. |
| 3 | Preprocessing and smoothing | Decide whether to keep current strict usable-anchor + Savitzky-Golay method, compare it with weighted Whittaker first, or adopt a split approach where confidence remains strict but the analysis curve uses quality weights. | **Decided: strict observations + isolated-style analysis curve** — keep stricter valid observations. For season/activity-window analysis, use isolated-style smoothing and a reconstructed/model-derived curve. Gap analysis stays separate and uses only real usable observation timestamps. Synthetic curve values are allowed only inside smoothing/curve/season analysis and must be labelled as model-derived, not observed evidence. |
| 4 | Activity windows vs crop cycles | Decide whether the pipeline should continue exposing generic vegetation activity windows only, or expose richer cycle metrics while still avoiding automated crop labels. Current code computes more than the API shows. | **Decided: activity cycles + broad season labels** — expose richer vegetation activity-cycle evidence, including complete/open lifecycle, count, peak/start/end, and broad summer/winter cycle labels where dates align a general regional calendar. Do not infer crop identity; summer/winter labels are calendar descriptors, not claims of wheat, maize, berseem, beans, etc. |
| 5 | Land status and abandonment | Decide the vocabulary and rule boundary between active, intermittent, idle/fallow, insufficient history, and abandonment. The isolated methodology says idle is not abandonment, and current mapper is too aggressive. | **Decided: cautious status vocabulary** — separate land activity from evidence/history coverage. One good observed season is `active` with `limited_history`; if still open, `active` with an incomplete current cycle. Do not call one observed season single-cropped, stable, trending, or long-term reliable. Idle/fallow is not abandonment. Use `possible_abandonment` only after enough history and an absence gate; avoid definitive abandonment for now unless explicitly supported later. |
| 6 | Absence gate and confidence | Decide how strict evidence must be before saying there was no crop/activity in an expected window. This affects false idle/abandonment flags and confidence wording. | **Decided: gate absence claims** — before `idle_or_fallow` or `possible_abandonment`, require enough window length, enough strict real observations, no major gaps across key onset/peak periods, low vegetation signal, multi-index support, and history context for abandonment-style wording. If the gate fails, output `absence_uncertain`, `not_assessed`, or `insufficient_evidence`, not inactivity/abandonment. |
| 7 | Additional indicators | Decide which extra indicators are worth carrying: p95/spread, NDMI moisture, MNDWI water, NDRE, MSAVI. Each should have a defined use and explicit forbidden claims. | **Decided: expose current indicators, defer index expansion** — carry p95/spread, existing EVI, NDMI, and MNDWI as cautious evidence. Defer NDRE and MSAVI to later index-expansion work. NDRE is worth keeping for dense-canopy headroom/vigour/nitrogen/stress context, but not for Fall Armyworm, pest, yield, crop-type, or income claims. MSAVI may help bare-soil and early-onset interpretation later. |
| 8 | Pixel-level evidence | Decide whether to add pixel-level maps/cube-derived figures now, or start with cheaper numeric spatial features such as mean-vs-p95 spread and leave maps for later. | **Decided: numeric spatial evidence + selected static visuals** — use numeric spatial evidence now, especially mean/p95/spread, to support field uniformity and patchiness wording. Add part of static-map work later for visual value: pick one or a few visuals that are useful and impressive, such as a cycle peak map or winter variability/cut-front figure. Defer full pixel-map pipeline and interactive raster maps. Preserve non-obvious local lessons in `docs/documentations/05-local-interpretation-context.md`. |
| 9 | Report evidence packet | Decide whether to add a structured report packet with Observed -> Interpreted -> Confidence -> Watch, risk register, boundaries, and track-record language. This helps portal/PDF and later LLM assistant. | **Decided: packet + polished HTML report** — build a structured evidence packet for correctness and a good-looking rendered HTML-style report/card experience like the isolated `outputs/exploration/` HTML, separate from PDF. The packet should include Observed, Interpreted, Confidence, Watch, Limitations, local context, risk/watch register, boundaries, and track record. Later LLM can improve narrative/content wording, but only from grounded packet fields and must not create new evidence. |
| 10 | LLM assistant role | Decide whether T-04 should wait until the report packet is grounded, or whether a deterministic brief should be built in parallel from existing fields. LLM must not create new evidence. | **Decided: T-04 owns assistant/chat implementation** — the report can narrate on request and a bounded analyst/chat interface is intended to ship, but implementation details and guardrail tasks belong in `T-04`. T-11 must produce the grounded packet/data the assistant consumes. The LLM may connect observations with local context and answer questions, but claim boundaries must remain typed: measured evidence, deterministic pipeline output, user-provided/local context, hypothesis, or unknown. |
| 11 | Monitoring and neighbours | Decide whether monitoring/neighbor baseline remains future scope or whether the current report should explicitly show these as unavailable limitations. | **Decided: unavailable for now** — monitoring and neighbour baseline remain out of current scope. Do not build live monitoring, alerts, neighbour comparison, or placeholder neighbour-average sections in this pass. Current reports may have watch items from the snapshot itself, but not monitoring/neighbour features. |
| 12 | Implementation packaging | Decide how to bundle the work: one larger pipeline/report pass after all decisions, or a sequence of small tasks such as T-10 fix first, then metrics exposure, then report packet. | **Decided: one coordinated pass, internally split by layer** — do not start implementation in this chat. In the next implementation chat, implement as one coherent project pass but in layer order: pipeline/data, season-analysis curve and activity cycles, status and absence gate, indicators/spatial evidence, evidence packet, polished report/card surface. Assistant/chat implementation is tracked in `T-04`, with T-11 providing the grounded packet. |

### Future Work — Crop/Rotation-Aware Calendar

Not current scope for this implementation pass.

Future direction: move beyond a generic region season calendar into a crop/rotation-aware calendar. A broad Nile Delta winter/summer calendar is useful for default assessment windows, but it is not enough when the user wants to judge whether a parcel behaved correctly for the crop sequence that was actually planted.

Key principle: crop/rotation context should be treated as user-provided or locally configured expectation, not as an automated crop-identity claim.

Example: in the same village, some farmers may plant `fasolia`/beans before wheat instead of berseem/clover. That rotation can delay wheat by about one month compared with the normal wheat start window. The pipeline should not flag that parcel as inactive or late just because it used the wrong expected calendar.

Future model:

| Layer | Meaning | Example |
|---|---|---|
| Region calendar | Broad local seasons. | Nile Delta winter, summer, and possible nili/transition season. |
| Crop calendar | Expected planting/harvest window for a declared crop. | Wheat normal sowing window, berseem/clover window, maize summer window. |
| Rotation calendar | Expected sequence and delays caused by the previous crop. | Beans before wheat shifts expected wheat green-up later than normal wheat. |

Future UI direction:

```text
Assessment window: [Crop / rotation calendar]
Region: [Egypt > Nile Delta > Menofia]
Season: [Winter 2025/26]
Expected plan: [Wheat after beans / fasolia]
```

Future report wording examples:

| Context | Wording |
|---|---|
| User declares wheat after beans | Observed activity is consistent with the declared wheat-after-beans window. |
| User declares normal wheat | Observed activity starts later than the normal wheat window. |
| Crop/rotation unknown | Winter-season activity detected; crop identity is not inferred. |

Current scope stays simpler: use general observed seasons/activity windows from the latest observations. If a season is incomplete at the assessment end date, keep it explicitly incomplete rather than forcing a complete-season interpretation.

## Task List

- [x] Copy or locate the isolated parcel-analysis directory and record its path: `outputs/exploration/`.
- [x] Inventory files by type: notes, prompts, notebooks, scripts, data artifacts, charts, and generated reports.
- [x] Identify the parcel identity, polygon/AOI, date window, data source, and analysis assumptions used in the isolated work.
- [x] Extract concrete findings from the isolated work, separating measured evidence from LLM/narrative interpretation.
- [x] Map findings to the current pipeline stage: ingestion, preprocessing, activity windows, scoring, risk flags, confidence, API, portal, PDF/reporting, or assistant.
- [x] Document initial unbiased comparison: current pipeline has / isolated work has / neutral comparison / pipeline implication.
- [x] Compare date-window behavior with T-09: fixed lookback, explicit dates, season calendar, and whether a 6-month result can be interpreted safely. → **migrated to T-09**.
- [x] Compare land-status and abandonment behavior with T-10: recent healthy season, short-window coverage, inactivity flags, trend uncertainty, and mapper behavior. → **migrated to T-10**.
- [x] Compare report/LLM notes with T-04: explanation value versus unsupported assessment claims. → **migrated to T-02** (validation); confirmed live.
- [x] Walk through Decision Point 1: validation baseline.
- [x] Walk through Decision Point 2: assessment window.
- [x] Walk through Decision Point 3: preprocessing and smoothing.
- [x] Walk through Decision Point 4: activity windows vs crop cycles.
- [x] Walk through Decision Point 5: land status and abandonment.
- [x] Walk through Decision Point 6: absence gate and confidence.
- [x] Walk through Decision Point 7: additional indicators.
- [x] Walk through Decision Point 8: pixel-level evidence.
- [x] Walk through Decision Point 9: report evidence packet.
- [x] Walk through Decision Point 10: LLM assistant role.
- [x] Walk through Decision Point 11: monitoring and neighbours.
- [x] Walk through Decision Point 12: implementation packaging.
- [x] Decide which differences are true pipeline defects, which are reporting gaps, which are one-parcel anomalies, and which need more validation parcels. → **migrated to T-13**.
- [x] Produce a prioritized pipeline-improvement proposal with minimal implementation slices. → **migrated to T-13**.
- [x] If implementation starts, update or create the relevant follow-up task before changing code.
- [x] Confirm source parcel artifacts are present: `data/aoi_demo_01/indices_timeseries.csv`, `run_metadata.json`, `scenes_index.jsonl`, `cube.zarr/`, and `weather_daily.parquet`.

## Feedback Log

- 2026-06-28: User has a separate isolated directory created with coding-agent help for interpretation and data analysis on one parcel. User wants it connected to current notes/tasks, but the main goal is a better pipeline rather than only enhancing the LLM task.
- 2026-06-28: User requested unbiased mapping for each finding: state what the current pipeline has, what the isolated parcel work has, and compare without bias.
- 2026-06-28: Isolated parcel-analysis directory is now present at `outputs/exploration/`. User emphasized this is a big task and requested small subtasks to avoid missing details.
- 2026-06-28: Initial inventory and comparison ledger written. Later verified in the active workspace that source parcel artifacts are present under `data/aoi_demo_01/`.
- 2026-06-29: User clarified Point 2: future crop/rotation-aware calendars are valuable because crop sequence changes expected timing (example: `fasolia`/beans before wheat delays wheat by about one month), but current implementation should stay general and good enough.
- 2026-06-29: User decided Point 3: keep stricter valid observations, but use isolated-style smoothing and reconstructed/model-derived curve for season analysis. Gap analysis remains separate and real-observation based; synthetic curve values are not evidence outside the season-analysis module.
- 2026-06-29: User decided Point 4: expose richer activity-cycle evidence and allow broad labels like summer cycle/winter cycle, while still avoiding automated crop identity claims.
- 2026-06-29: User decided Point 5: one good observed season should be called active with limited history. Do not infer single-cropping, trend, long-term reliability, or abandonment from one season.
- 2026-06-29: User decided Point 6: require an absence gate before idle/fallow or possible-abandonment wording. If evidence is weak, report uncertain/not assessed instead of inactivity/abandonment.
- 2026-06-29: User decided Point 7: expose p95/spread, existing EVI, NDMI, and MNDWI cautiously now; defer NDRE/MSAVI. NDRE is valuable for dense-canopy headroom/vigour/nitrogen/stress context but not for Fall Armyworm, pest, yield, or crop certainty claims.
- 2026-06-29: User decided Point 8: use numeric spatial evidence now and part of static visuals for useful/impressive report value; defer full pixel-map workflows. User requested a separate local context document for non-obvious interpretation lessons that required their correction or reporting.
- 2026-06-29: User decided Point 9: build both a structured evidence packet and a polished HTML-style rendered report/card like the isolated outputs, separate from PDF. LLM may later affect narrative/content wording, but only from grounded packet fields.
- 2026-06-29: User decided Point 10: LLM should narrate reports on request, have the needed data, act as a bounded analyst, and support a chat interface where users can ask freely.
- 2026-06-29: User decided Point 11: monitoring and neighbour baseline are unavailable for now; do not add placeholders or report sections for them in this pass.
- 2026-06-29: User decided Point 12: use one coordinated implementation pass internally split by layer, but do not start now. Implementation will begin in a new chat.
- 2026-06-29: Audit follow-up accepted: clean stale source-artifact contradiction, defer weather use, strengthen one-parcel caution, migrate assistant/chat implementation tasks to T-04, and keep abandonment mapping/status fix as a top priority. Reproducibility/provenance questions for figures will be discussed separately.
- 2026-06-29: User decided audit point 2: report visuals shipped to users need Level 3 provenance minimum; evidence-packet/core outputs should target Level 4. LLM assistant work must consume provenance metadata and distinguish production facts from isolated/manual/research evidence.
- 2026-06-29: User selected season detector approach: keep deterministic FarmTrust detector as backbone, align it with isolated peak/trough and per-cycle amplitude boundaries, and keep HMM as validation/future work.
- 2026-06-29: Implementation started with the status/scoring safety slice first: stop false `inactivity` -> `abandonment` exposure, separate activity status from history/evidence coverage, and add targeted tests before moving to larger smoothing/detector/report work. Source artifacts under `data/aoi_demo_01/` were confirmed with PowerShell because glob/grep-style searches may miss that directory shape.
- 2026-06-29: Status/scoring safety slice implemented: core assessment now emits `history_coverage` and `absence_assessment`; one good cycle can stay `active` with `limited_history`; no-activity claims require the absence gate; public API mapping no longer turns `possible_inactivity` into `abandonment`. Focused tests passed. Full pytest still has unrelated crop-classification expectation failures in `tests/test_aoi_demo_crop_classification.py`.
- 2026-06-29: Neighbour/comparables/report-wording safety cleanup completed: API no longer emits placeholder `neighbor_comparison="avg"`; portal summary/evidence/PDF surfaces no longer show neighbour/comparable placeholders; demo/report wording no longer gives financing recommendations or unsupported yield/legal/crop-comparison claims. Neighbour baseline and monitoring remain future/unavailable, not hidden production facts.
- 2026-06-29: Indicators/spatial pass-through slice completed: existing ingestion p95/MNDWI stats now flow through preprocess, scoring metrics, API indicators, and cautious portal/PDF labels. `aoi_demo_01` temp pipeline run produced finite p95/spread/MNDWI metrics. No new risk rules, crop/yield/pest/rice claims, NDRE/MSAVI, or pixel maps were added.
- 2026-06-29: Slice 3 started: season-analysis curve and detector upgrade. Keep strict observations as evidence, use model-derived analysis values only for activity-cycle shape/boundary estimation, add boundary/source support metadata, preserve real-observation gap confidence, and avoid HMM/crop labels/global threshold tuning.
- 2026-06-29: Slice 3 completed: smoothing metadata now marks analysis-curve values as model-derived/non-direct evidence; deterministic season detection uses peak/trough per-cycle amplitude candidates combined with threshold fallback; season payloads expose boundary source and nearest real usable observation support. `aoi_demo_01` temp run detected 4 confirmed complete windows with `land_status=active`, `absence=activity_present`, and `history=sufficient_history`.

## Decisions

- [decision] Treat the isolated parcel-analysis work as evidence for pipeline improvement, not as authoritative ground truth.
- [decision] Use side-by-side comparison before implementation: current pipeline has / isolated work has / neutral comparison / pipeline implication.
- [decision] Keep assistant outputs dependent on grounded pipeline/report evidence. T-04 owns assistant narration and bounded analyst/chat implementation; T-11 owns the packet/data those assistant surfaces consume.
- [decision] Validation baseline: no regression harness for `data/aoi_demo_01` now; constant research iteration would fight locked golden outputs. Use the parcel informally for manual reference. A validation harness (invariant checks only) may be added later when the pipeline stabilises. (2026-06-28, Point 1)
- [decision] Assessment window: implement a general dropdown-first assessment-window experience, with a possible calendar view. For now, use general observed seasons/activity windows from the latest observations. If a season is incomplete at the assessment end date, preserve that incomplete status rather than forcing full-season interpretation. Crop/rotation-aware calendars are future work, not current scope. (2026-06-29, Point 2)
- [decision] Preprocessing and smoothing: keep stricter valid observations. For season/activity-window detection, adopt isolated-style smoothing and a reconstructed/model-derived analysis curve. Gap analysis remains separate and based only on real usable observation timestamps. Synthetic/model-derived curve values may support season shape and boundary estimation, but must not be used as direct evidence for scoring, raw observations, water/moisture claims, or confidence without support labels. (2026-06-29, Point 3)
- [decision] Activity windows vs crop cycles: expose richer user-facing vegetation activity-cycle evidence, including cycle count, complete/open lifecycle, start/peak/end dates, and broad summer/winter cycle labels where a general regional calendar supports them. Keep the technical object grounded as a vegetation activity window/cycle and do not infer crop identity. Summer/winter labels are calendar descriptors, not crop labels. (2026-06-29, Point 4)
- [decision] Land status and abandonment: use cautious status vocabulary. Separate `land_status` from history/evidence coverage. One good observed season is `active` plus `limited_history`; if the cycle is still open, report `active` with an incomplete current cycle. Do not call one observed season single-cropped, stable, trending, long-term reliable, idle, or abandoned. `idle_or_fallow` is not abandonment. Use `possible_abandonment` only after sufficient history and an absence gate; avoid definitive abandonment for now unless future evidence/rules explicitly support it. (2026-06-29, Point 5)
- [decision] Absence gate and confidence: do not state `idle_or_fallow`, `inactivity`, or `possible_abandonment` unless an absence gate passes. The gate requires enough assessment-window length, enough strict real observations, no major gaps across key onset/peak periods, low vegetation signal, multi-index support, and sufficient history for abandonment-style wording. Output levels should distinguish `activity_present`, `absence_supported`, `absence_uncertain`, and `not_assessed`; failed gates become uncertain/insufficient evidence, not inactivity/abandonment. (2026-06-29, Point 6)
- [decision] Additional indicators: carry p95/spread, existing EVI, NDMI, and MNDWI forward as cautious evidence. p95/spread supports field-uniformity/patchiness evidence, NDMI supports moisture watch, MNDWI supports surface-water/flooding signal, and EVI supports vegetation confirmation. Defer NDRE and MSAVI to later index-expansion work. NDRE is valuable for dense-canopy headroom/vigour/nitrogen/stress context where NDVI saturates, but the isolated report showed it is not a Fall Armyworm, pest, yield, crop-type, income, or crop-health certainty detector at 20 m. MSAVI may help bare-soil and early-onset interpretation later. (2026-06-29, Point 7)
- [decision] Pixel-level evidence: start with numeric spatial evidence, especially mean, p95, and mean-vs-p95 spread for field uniformity/patchiness. Include part of static-map work later only where it is both useful and visually compelling, such as a cycle peak map or winter variability/cut-front figure. Defer full pixel-map workflows and interactive raster maps. Non-obvious local interpretation lessons are documented in `docs/documentations/05-local-interpretation-context.md` for future agent context. (2026-06-29, Point 8)
- [decision] Report evidence packet: build a structured packet plus a polished HTML-style rendered report/card experience. The packet is the correctness layer: Observed, Interpreted, Confidence, Watch, Limitations, local context, risk/watch register, boundaries, track record, and per-claim confidence. The rendered view is the presentation layer: visually strong like the isolated `outputs/exploration/` HTML reports and separate from PDF. Later LLM content/narrative may affect the report wording, but only by consuming grounded packet fields; it must not invent evidence or override deterministic outputs. (2026-06-29, Point 9)
- [decision] LLM assistant role: T-04 owns assistant/chat implementation. T-11 must provide the grounded evidence packet and supporting data. The intended assistant can narrate on request and ship as a bounded analyst/chat interface, but it must consume typed evidence and label claim type/uncertainty: measured evidence, deterministic pipeline result, user-provided/local context, hypothesis, or unknown. It must not silently override deterministic pipeline outputs, invent evidence, claim unsupported crop identity/yield/pest/income/legal facts, or hide uncertainty. (2026-06-29, Point 10; refined by audit follow-up)
- [decision] Monitoring and neighbours: unavailable for now. Do not build live monitoring, alerting, neighbour baseline, neighbour comparison, placeholder neighbour-average, or report sections for unavailable neighbour/monitoring features in this pass. Snapshot watch items are allowed when they come from the current assessment itself. (2026-06-29, Point 11)
- [decision] Implementation packaging: one coordinated implementation pass, internally split by layer, but do not start in this chat. Next chat should build in order: pipeline/data, season-analysis curve and activity cycles, status and absence gate, indicators/spatial evidence, evidence packet, polished report/card surface. Assistant/chat implementation lives in T-04; T-11 should only provide the grounded packet and integration surface. The first status/scoring priority is the inactivity/idle/fallow/abandonment boundary and mapper fix. (2026-06-29, Point 12; refined by audit follow-up)
- [decision] Weather: `data/aoi_demo_01/weather_daily.parquet` exists but weather integration is deferred. Weather may later support phenology/anomaly/moisture context, but it is out of the current T-11 implementation pass. (2026-06-29 audit follow-up)
- [decision] Provenance: user-facing report visuals require Level 3 provenance minimum: committed/documented script, input path, parameters, output path, and run steps. Core status/scoring/confidence/report-packet fields should target Level 4 pipeline provenance. Level 0-2 isolated/manual/research evidence can inform design or assistant context only with caveats; it must not be presented as a production result. (2026-06-29 audit point 2)
- [decision] LLM evidence provenance: T-11 evidence packets must carry claim metadata so T-04 can enforce safe assistant/chat behavior. Claims should include claim type, provenance level, source, method, allowed use, restrictions, and confidence. LLM output is not evidence; it is narration/analysis over packet evidence and should be stored with packet version/hash, model/provider, prompt version, timestamp, and guardrail result when implemented. (2026-06-29 audit point 2)
- [decision] Season detector: use the current deterministic FarmTrust activity-window/cycle detector as production backbone, aligned with the isolated peak/trough and per-cycle amplitude-boundary method. The detector should run on the reconstructed season-analysis curve, estimate SOS/EOS from per-cycle amplitude boundaries, preserve open/incomplete lifecycle states, and use real-observation gap analysis for confidence. HMM remains research validation/future work until its parcel workflow is rerunnable and production-proven. (2026-06-29 detector decision)

## Open Questions

- [answered] What is the path/name of the copied isolated parcel-analysis directory? `outputs/exploration/`.
- [partly answered] Does the isolated parcel use the exact same AOI polygon and date window as the current FarmTrust run? Current `outputs/exploration/` evidence says final window is `02 May 2024 -> 19 Jun 2026`; source artifacts are present at `data/aoi_demo_01/` for inspection/rerun, but exact run equivalence still needs explicit comparison.
- [partly answered] Which artifacts from the isolated work are trusted measurements versus exploratory LLM interpretation? Scripts/reports expose measured/code-derived outputs; crop identities and management explanations depend partly on grower notes and should be labelled as user-provided or interpreted.
- [answered] Should this parcel become an official regression fixture after review, or remain an informal validation case? **Decided: skip for now.** No regression harness during constant iteration; maybe a validation harness later. Use `data/aoi_demo_01` informally for manual reference.
- [answered] Can the source AOI folder be copied too, especially `indices_timeseries.csv`, `run_metadata.json`, and a reduced or full `cube.zarr`? Source artifacts are present at `data/aoi_demo_01/`, including `indices_timeseries.csv`, `run_metadata.json`, `scenes_index.jsonl`, `cube.zarr/`, and `weather_daily.parquet`.

## Knowledge to Keep

- The comparison must not bias toward either the current pipeline or the isolated work. A disagreement can mean a pipeline bug, a reporting gap, a different time window, a different method, insufficient evidence, or an unsupported isolated conclusion.
- The most relevant existing tasks are T-09 for assessment-window/season-calendar behavior, T-10 for short-window land-status and abandonment fixes, and T-04 for grounded assistant narration plus bounded analyst/chat implementation.
- One parcel is useful for debugging and regression, but not enough by itself to calibrate general scoring thresholds.
- One parcel must not calibrate global thresholds, smoothing parameters, or status cutoffs. The Menofia parcel can expose failure modes and shape design, but production thresholds need more parcels or explicit validation evidence.
- Synthetic/model-derived curve values can support season-shape analysis, but only real usable observations are direct evidence. Gap analysis must remain real-observation based.
- Broad summer/winter cycle labels are allowed as calendar descriptors when supported by dates, but they must not become automated crop labels.
- Land activity status must be separated from history coverage. A single good observed cycle supports current activity, but not long-term stability, trend, single-cropping, or absence/abandonment claims.
- Absence is a claim that requires evidence. No detected activity is not enough by itself; the pipeline must prove the observation window and data coverage were adequate before saying idle/fallow or possible abandonment.
- Additional indicators must have explicit permitted and forbidden uses. NDRE is a dense-canopy headroom/stress-context indicator, not a pest/yield detector; p95/spread is patchiness evidence, not proof of crop split.
- Pixel-level interpretation needs local context. Use `docs/documentations/05-local-interpretation-context.md` to avoid over-reading patterns such as berseem cutting fronts, mixed winter management, delayed wheat after beans/fasolia, central walkways, or pest/yield invisibility.
- The report needs two layers: a grounded evidence packet for correctness and a polished HTML/card rendering for comprehension and trust. PDF is a separate export path, not the primary interactive report experience.
- The LLM layer is allowed to analyze, but analysis must be bounded and typed. It can reason over the packet/data and local context, but must expose whether a statement is observed, deterministic, user-provided, inferred, hypothetical, or unknown.
- Monitoring and neighbour comparison are out of current scope. Do not add placeholder neighbour averages or imply live monitoring exists.
- Weather data is present but deferred. Do not mix `weather_daily.parquet` into this pass unless the user explicitly reopens scope.
- Shipped report visuals need Level 3 provenance minimum. Do not ship isolated/manual figures without committed rerunnable generation steps.
- Assistant-consumable claims need provenance metadata. T-04 should not treat isolated research artifacts as production facts unless provenance level and allowed use permit it.
- Production season detection is deterministic: current FarmTrust backbone, improved with reconstructed analysis curve plus peak/trough and per-cycle amplitude boundary logic. HMM is validation/future, not source of truth.
- Implementation should start in a new chat, not this one. The next agent should treat the 12 decisions as closed unless the user changes them or new evidence appears. T-04 owns assistant/chat tasks; T-11 owns pipeline/report packet readiness.

## Implementation Handoff

Original planning handoff: start from the decisions above and implement as one coordinated pass split by layer:

1. **Pipeline/data layer:** keep strict valid observations; add isolated-style smoothing and reconstructed/model-derived analysis curve only for season/activity analysis; keep gap analysis real-observation based; attach provenance metadata to assistant/report-consumable claims.
2. **Season/activity-cycle layer:** keep deterministic FarmTrust detector as the backbone; run it on the reconstructed analysis curve; align boundaries with peak/trough and per-cycle amplitude logic; preserve open/incomplete lifecycle; expose richer vegetation activity-cycle metrics and broad summer/winter cycle labels without crop identity claims.
3. **Status/scoring layer:** first fix the `inactivity`/idle/fallow/abandonment boundary and mapper behavior; then separate `land_status` from history/evidence coverage and add cautious status vocabulary plus absence-gate levels.
4. **Indicators/spatial layer:** carry p95/spread, EVI, NDMI, and MNDWI cautiously; use numeric spatial evidence now; defer NDRE/MSAVI and full pixel maps.
5. **Evidence packet layer:** produce Observed, Interpreted, Confidence, Watch, Limitations, local context, risk/watch register, boundaries, track record, and per-claim confidence.
6. **Report/UI layer:** render a polished HTML/card-style report experience separate from PDF, with selected useful static visuals only when they add value and meet Level 3 provenance minimum.
7. **Assistant/chat layer:** implementation is tracked in `T-04`. T-11 should expose the grounded evidence packet and integration surface only.

### Implementation Start — Slice 1: Status/Scoring Safety

Active first slice:

- Fix the public mapper so `possible_inactivity`, idle/fallow, or insufficient-history evidence cannot become `abandonment` without the T-11 absence gate and sufficient history.
- Separate current activity status from history/evidence coverage enough for one good observed cycle to be reported as current activity with `limited_history`, not long-term stability or abandonment evidence.
- Add absence-gate output vocabulary at the scoring/API boundary where feasible: `activity_present`, `absence_supported`, `absence_uncertain`, `not_assessed`, or `insufficient_evidence`.
- Keep this slice narrow: no Whittaker/analysis-curve switch, no detector rewrite, no report-card redesign, no assistant/chat implementation.
- Verification target: unit tests for no false abandonment, cautious one-cycle status, and uncertain/not-assessed absence behavior; then rerun the pipeline scripts on `data/aoi_demo_01/` as an informal reference check.

Slice 1 result:

- Implemented in `farmtrust_core/scoring/rules.py`, `api/assessment_mapper.py`, and `api/schemas.py`.
- Added tests in `tests/test_evidence_confidence_gate.py` and updated the no-activity fixture in `tests/test_activity_window_detection.py` to make low multi-index vegetation signal explicit.
- Verification: `uv run pytest tests/test_evidence_confidence_gate.py tests/test_activity_window_detection.py` passed (`18 passed`).
- Verification: temp pipeline run for `data/aoi_demo_01/` completed without overwriting repo data; generated assessment reported `land_status=active`, `absence_assessment=activity_present`, `history_coverage=sufficient_history`, and no abandonment exposure.
- Verification: repo-output pipeline rerun for `data/land-c92521f9627b4cc1a9e0ef65909a1820/` rewrote `data/preprocess/land-c92521f9627b4cc1a9e0ef65909a1820/`, `data/seasonal/land-c92521f9627b4cc1a9e0ef65909a1820/`, and `data/assessment/land-c92521f9627b4cc1a9e0ef65909a1820/`. Generated assessment reported `assessment_status=complete`, `land_status=active`, `absence_assessment=activity_present`, `history_coverage=limited_history`, `trend_2y=uncertain`, `risk_flags=[]`, `confidence=low`, and no abandonment exposure.
- Known out-of-scope verification issue: full `uv run pytest` passed 55 tests and failed 3 crop-classification expectation tests in `tests/test_aoi_demo_crop_classification.py`; those failures are unrelated to this status/abandonment safety slice.

### Implementation Safety Cleanup — Neighbours, Comparables, and Wording

Completed before moving to the next pipeline layer:

- Removed the API placeholder neighbour comparison value from `api/assessment_mapper.py` and the exposed indicator contract in `api/schemas.py` / portal types.
- Removed portal neighbour/comparable placeholder displays from summary indicators, evidence tabs, and PDF report output.
- Replaced financing-decision wording with evidence-review / decision-support wording.
- Replaced unsafe demo/report risk descriptions that implied yield, legal verification, or unavailable neighbour comparisons with cautious signal wording.
- Verification: `uv run pytest tests/test_evidence_confidence_gate.py tests/test_activity_window_detection.py` passed (`18 passed`).
- Verification: `bun run typecheck` and `bun run build` passed.
- Verification: searched portal sources for removed neighbour/comparable placeholders and unsafe financing/yield/legal strings; no matches remained.

Boundary preserved:

- Neighbour baseline, comparable parcels, live monitoring, and financing/legal decisions remain out of scope for T-11 implementation.
- Future report surfaces may show these only after real pipeline support exists and the evidence packet marks provenance/allowed use clearly.

### Implementation Slice — Indicators and Numeric Spatial Evidence

Completed before the larger smoothing/detector rewrite:

- Carried existing ingestion stats through preprocessing: `ndvi_p95`, `evi_p95`, `ndmi_p95`, `ndwi_p95`, `mndwi_mean`, and `mndwi_p95`.
- Added raw numeric spread fields in preprocessing output, especially `ndvi_spread_raw` and `mndwi_spread_raw`, while preserving strict usable-observation semantics.
- Added scoring summary metrics: `interval_max_ndvi_p95`, `interval_median_ndvi_spread`, and `interval_median_mndwi`, plus per-cycle `peak_ndvi_p95`, `median_ndvi_spread`, and `median_mndwi`.
- Exposed cautious API/portal indicators: `ndvi_p95_peak`, `ndvi_spread_median`, `evi_peak`, `ndmi_median`, and `mndwi_median`.
- Rendered UI labels as signals: Field Spread, EVI Confirmation, Moisture Signal, and Surface-Water Signal.
- Fixed summary statistics to ignore non-finite raw p95/spread values from invalid rows so model-filled/smoothed rows do not produce `NaN` interval evidence.

Verification:

- `uv run pytest tests/test_gap_aware_smoothing.py tests/test_evidence_confidence_gate.py tests/test_activity_window_detection.py tests/test_cube_pipeline_offline.py tests/test_cube_ingest.py` passed (`55 passed`).
- `bun run typecheck` passed.
- `bun run build` passed.
- Temp pipeline run for `data/aoi_demo_01/` completed without overwriting repo data and generated finite metrics: `interval_max_ndvi=0.927099`, `interval_max_ndvi_p95=0.960125`, `interval_median_ndvi_spread=0.052221`, `interval_max_evi=0.834393`, `interval_median_ndmi=0.245872`, `interval_median_mndwi=-0.424085`.
- Search found no targeted unsafe portal strings for yield/pest/crop type/rice, detected waterlogging/salinity, or neighbour placeholders.

Boundary preserved:

- These indicators are evidence signals only. They do not create new risk rules or automated crop, pest, yield, income, rice, waterlogging, salinity, or legal claims.
- NDRE/MSAVI, selected static visuals, full pixel maps, and detector/smoothing changes remain separate future slices.

### Implementation Slice — Season-Analysis Curve and Detector Boundary Provenance

Completed slice:

- Preserve strict usable observations as the evidence layer.
- Treat filled/smoothed values as model-derived analysis values for cycle shape and estimated boundaries only.
- Align deterministic activity-window boundaries with per-cycle amplitude logic while preserving the current FarmTrust detector backbone and lifecycle states.
- Add boundary provenance/support metadata so report/API consumers can distinguish observed support from model-derived estimates.
- Keep real-observation gap analysis as the confidence source; do not treat synthetic/model-derived values as direct evidence.

Result:

- Added smoothing metadata: `analysis_curve_source=model_derived_filled_smoothed_values_at_observed_timestamps` and `analysis_curve_direct_evidence=false`.
- Decision: do not add a separate `season_analysis_curve.csv` artifact in this slice. Keep `ndvi_smoothed.csv` as the single preprocess artifact for now, and make the model-derived analysis-curve role explicit through metadata and boundary-support fields instead of multiplying files.
- Detector reference: use the more mature parcel-cycle logic in `outputs/exploration/analyze.py` as the phenology reference for Slice 3, especially its per-peak cycle builder, 20% amplitude SOS/EOS boundaries, and explicit edge-cycle handling. Port those ideas into the production detector without copying parcel-specific labels, hard-coded paths, or report-only logic.
- Simplified the deterministic detector to use peak/trough per-cycle amplitude candidates as the single production path; removed the older threshold-candidate fallback so one boundary method remains the long-lived source of truth.
- Added activity model metadata: `input_signal=model_derived_analysis_curve_at_observed_timestamps`, `boundary_method=peak_trough_per_cycle_amplitude_fraction`, and `gap_confidence_source=real_usable_observation_timestamps`.
- Added season payload fields for `start_boundary_source`, `peak_source`, `end_boundary_source`, nearest real observation dates, and nearest real observation day offsets.
- Kept lifecycle handling (`complete`, `open_left`, `open_right`, `open_both`) and real-observation gap-overlap confidence logic.

Verification:

- `uv run pytest tests/test_gap_aware_smoothing.py tests/test_evidence_confidence_gate.py tests/test_activity_window_detection.py tests/test_cube_pipeline_offline.py tests/test_cube_ingest.py` passed (`55 passed`).
- `bun run build` passed.
- Temp pipeline run for `data/aoi_demo_01/` completed without overwriting repo data. Generated season payload reported `season_count=4`, `complete_window_count=4`, `open_window_count=0`, `borderline_window_count=0`, and all window boundary sources as `model_derived_analysis_curve` with nearest real observation support dates.
- Generated assessment reported `land_status=active`, `absence_assessment=activity_present`, `history_coverage=sufficient_history`, and no abandonment exposure.

Boundary:

- No HMM production source of truth.
- No crop identity or crop labels.
- No global threshold tuning from `data/aoi_demo_01`.
- No evidence-packet or polished report redesign inside this slice.

## Done Summary

### Smoothing + detector + HMM cross-check rewrite (2026-06-30)

Completed the smoothing/season-analysis-curve and activity-cycle detector rewrite (Slice 3, properly), plus the HMM cross-check and a visualization deliverable.

- **Smoother:** replaced the index-domain polyfit (mislabeled Savitzky-Golay) and the dead `smooth_usable_values` with a quality-weighted **Whittaker-Eilers** smoother on a regular **daily grid** in `farmtrust_core/preprocess/analysis_curve.py`. `is_usable` stays the strict 0.90 evidence/gap gate; the curve uses a looser weighted inclusion (`>=0.30`). A new daily artifact `season_analysis_curve.csv` is persisted alongside `ndvi_smoothed.csv` (the obs-grid `*_smoothed` columns are now the daily curve sampled at observations). `smoothing_metadata()` rewritten to describe the running smoother. `scipy` added as a base dependency.
- **Lambda:** derived from a **phenology smoothing timescale (~45 days)** via `lambda = (T/2*pi)**4` (≈2631 on a daily grid), not a Menofia-tuned constant. Plain GCV was implemented and **rejected as default** — it systematically undersmooths daily-gridded NDVI (minimizes at lambda≈1-10, ~150 effective DOF). The timescale is an agronomic constant, identical across fields, so it avoids single-AOI overfit while giving the correct ~weeks-scale smoothing. `select_lambda_gcv` kept as an available alternative.
- **Detector:** `farmtrust_core/seasonal/seasons.py` rebuilt on the daily curve. Peak min-distance now in **real days** (fixes the two-cycles-merged bug); per-limb **asymmetric** SOS/EOS amplitude thresholds (`ALPHA_START=0.20`, `ALPHA_END=0.35`) with slope confirmation; sub-peak merging so a berseem multi-cut stays one cycle; **lifecycle by crossing-reachability** (fixes open_left/open_right mislabeling). Overloaded `BOUNDARY_PROMINENCE_FRACTION` split into named constants; dead constants/`crossing_date` removed; `season_id` sequenced across the combined confirmed+borderline list. Additive fields: `season_calendar_label`, `greenup_rate`, `senescence_rate`, `integrated_ndvi`, `cycle_split_merged`, `daily_curve_lambda`. Load-bearing payload contract preserved; scoring/API consume it unchanged (`rules.py` only gained additive `season_calendar_label` + `is_open` contract comments).
- **HMM cross-check:** ported the deterministic 4-state Gaussian HMM to `outputs/tools/hmm_phenology.py` (RNG-free, flat-series + std/variance guards) with `outputs/tools/hmm_comparison.py` and `outputs/tools/season_detector_comparison.py`. It consumes the same daily curve, writes `outputs/diagnostics/<aoi>/hmm_cross_check.{json,md}`, and **never** changes production output. On Menofia it independently recovers 4 cycles matching the detector (mean peak delta 0.0 d).
- **Visualization:** `outputs/tools/visualize_pipeline_outputs.py` renders a self-contained offline HTML (raw obs, linear interpolation, Whittaker curve, per-point hover, detected cycles, HMM comparison) to `outputs/diagnostics/<aoi>/pipeline_visualization.html`.
- **Tests:** realistic deterministic fixtures in `tests/fixtures/phenology_synthetic.py`; new `tests/test_analysis_curve_smoothing.py`, rewritten `tests/test_activity_window_detection.py` (the 3 previously-failing scenarios now pass + a berseem-sawtooth single-cycle test), `tests/test_hmm_cross_check.py`, and `tests/test_pipeline_invariants_real_aoi.py` (invariant checks on both reference AOIs). 53 relevant tests pass; the only remaining failures are pre-existing collection errors in 3 modules needing the optional `data`/`ml` dependency groups (xarray/odc/joblib).
- **Validation:** end-to-end temp runs — Menofia: 4 cycles, `active`/`activity_present`/`sufficient_history`; short AOI `land-c925…`: 1 cycle, `active`/`limited_history`, no false abandonment.

### Docs sync + lambda fix (2026-06-30, follow-up to the rewrite)

- Brought every related doc in line with the rebuilt smoother/detector: `docs/PIPELINE.md`, `docs/ENGINEERING.md`, `README.md` (scipy base dep), `docs/DECISIONS.md` back-reference, and a full methodology rewrite in `docs/pipeline-walkthrough.md`. Added the graduation log `docs/documentations/06-smoother-detector-hmm-refactor-log.md` and wired it into T-12's Ch 6/7/9 source lists.
- Fixed `daily_curve_lambda` being written as `NaN` on the CSV-loaded path: `load_daily_analysis_curve` now recovers `select_lambda()[0]` (the production worker path already produced the correct ≈2631).

### Report evidence packet — Layer 5 (2026-06-30)

Implemented Implementation-Handoff layer 5 / Decision Point 9: a grounded, deterministic evidence packet that aggregates the written assessment, season, and quality artifacts into an `Observed -> Interpreted -> Confidence -> Watch` structure. Scope was **core artifact only** (no API endpoint/DTO and no HTML render — those stay in layer 6) with **lightweight per-claim provenance** (`layer` + `confidence` + `rests_on`; the full provenance schema is deferred to T-04, which owns assistant guardrails).

- **Module:** `farmtrust_core/report/evidence_packet.py` — `build_report_evidence_packet()` (pure over four input artifacts; no DB/network/wall-clock) + `write_report_evidence_packet()`. New `farmtrust_core/report/` package (future home of the layer-6 renderer).
- **Artifact:** `data/assessment/<aoi_id>/report_evidence_packet.json` (Level-4 pipeline artifact). Path helper `report_evidence_packet_path` added to `farmtrust_core/io/paths.py`.
- **Packet content:** cautious `headline` (state vocabulary + provisional cropping intensity), `claims[]` projected into `layers`, `activity_record`, `track_record` (seasons toward a certifiable trend), a `risk_register` split into `land_risk` vs `evidence_limitation`, `limitations`, fixed `boundaries` ("what this does NOT tell you"), cautious `indicators`, and an empty `local_context` slot.
- **Claim discipline:** no crop identity (calendar labels are summer/winter descriptors only); yield/income/price/pest/legal terms appear only inside `boundaries`; one good cycle stays `Active — limited history`; no monitoring/neighbour sections.
- **Wiring:** built per-land in the worker's `report_generation` phase (`api/worker.py` `_build_evidence_packet`), after the assessment is saved; a packet failure logs `[WARN]` and does not fail the job.
- **Tests:** `tests/test_report_evidence_packet.py` — deterministic unit tests (structure, cautious-vocabulary cases, forbidden crop-token guard, determinism, write round-trip) plus invariant tests on both reference AOIs. Verified with a scratch end-to-end run through the real path helpers on `aoi_demo_01`.

### Report/UI — Layer 6 (2026-06-30)

Implemented Implementation-Handoff layer 6 / Decision Point 9 presentation layer: the API surface for the packet plus a polished, lender-facing report card in the portal, separate from the PDF.

- **API:** `EvidencePacketResponse` DTO (`api/schemas.py`, nested Packet* models; the packet's `schema` key exposed via `Field(alias="schema")`), `map_evidence_packet_response` (`api/assessment_mapper.py`), and `GET /lands/{land_id}/evidence-packet` (`api/routers/lands.py`) — 404 for a missing land or an ungenerated packet.
- **Portal data layer:** `EvidencePacket` TS types + `api.lands.evidencePacket` + `useEvidencePacket` react-query hook + a Next proxy route `app/api/lands/[id]/evidence-packet/route.ts` (forwards the real FastAPI status/body).
- **Report card:** `portal/src/components/report/` — `EvidencePacketReport` (verdict, four-layer Observed/Interpreted/Confidence/Watch read, activity timeline, track-record gauge, split risk register, limitations, indicators, the dark "what this does not tell you" boundaries block) + `ActivityTimeline` (data-driven SVG, calendar-coloured, open cycles hatched, per-cycle date tooltips) + `TrackRecordGauge` (neutral maturity ring + provisional badge) + `packet-style.ts`. Rendered on a new route `app/(portal)/lands/[id]/packet/page.tsx`, linked from the summary page.
- **Claim discipline carried into the UI:** no crop/yield/loan wording outside the boundaries block; calendar labels are summer/winter/transition only; `status_so_far` always shown with its provisional flag/note; manual-review shown honestly.
- **Verification:** portal `tsc --noEmit` clean, `next build` green (both routes compiled), `tests/test_evidence_packet_api.py` (mapper + DTO + alias round-trip) added; 41 backend tests pass. Hardened against a 3-lens adversarial review (claim discipline, robustness, backend contract) — fixes: softened layer blurbs, neutral gauge colour, timeline label de-overlap + peak clamp + degenerate-span handling + date tooltips, indicators empty-state, collision-proof keys, honest proxy error forwarding, distinct land-load error state.

### Bounded report assistant — Layer 7 (2026-06-30, implemented in T-04)

Implemented Implementation-Handoff layer 7 / Decision Point 10: the grounded, bounded report assistant that consumes this packet. Tracked and documented in `docs/TASKS/T-04-ai-report-assistant.md`; summarised here because it closes the T-11 packet-provenance contract and the assistant-storage requirement.

- **Packet provenance (this repo, T-11-owned):** the per-claim metadata schema T-11 specified (claim type, provenance level, source, method, allowed use, restriction) is now attached by `farmtrust_core/report/evidence_packet.py::_apply_provenance` (packet `v1.1`, additive). This is the contract Layer-7 guardrails depend on, so it lives in the packet builder; the assistant only consumes it.
- **Assistant (T-04-owned):** deterministic-first narration + bounded analyst chat over the packet (`farmtrust_core/report/brief.py`, `api/assistant/*`, `POST /lands/{id}/assistant/{narrate,chat}`), Azure `gpt-4o` via `langchain-openai` gated off when unconfigured, with the deterministic brief as the always-on fallback. Every interaction is stored in an `AssistantMessage` audit row with packet hash, model, prompt version, and guardrail result — satisfying the T-11 storage requirement (line ~238). Portal: a "Report / Ask the assistant" tab on `/lands/[id]/packet`.
- **Claim discipline preserved:** answers are bounded to packet evidence and per-claim typing; grounding is enforced by the system prompt (the output forbidden-phrase scan was removed post-launch — see T-04), with the deterministic brief as the always-on fallback. The assistant reasons with crops the user *declares* but never asserts a crop from satellite alone, and keeps yield/income/loan out. Provenance levels distinguish measured vs model-derived vs interpretation vs boundary-exclusion, so Level 0–2 isolated/manual context can never be presented as a production fact.

All seven Implementation-Handoff layers are now landed (Layers 1–4 pipeline/scoring, Layer 5 packet, Layer 6 report card, Layer 7 assistant).

### Task closed (2026-07-01)

T-11 is **closed**. All seven Implementation-Handoff layers shipped, and the Layer-7 assistant was verified live by the user. The five remaining analysis/proposal checkboxes were migrated rather than dropped:

- date-window comparison → **T-09**; land-status/abandonment comparison → **T-10**;
- report/LLM explanation-value comparison → **T-02** validation (confirmed live);
- "triage differences + prioritized improvement proposal" → new follow-up **T-13**.

No open items remain in T-11.
