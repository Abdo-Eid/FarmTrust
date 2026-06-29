# Crop Classification Research And Model Work Log

Date started: 2026-06-27

## Purpose

This document tracks the research, technical analysis, data work, model work, experiments, validation evidence, limitations, and possible synthesis of the crop-classification work.

It is written as a normal long-form documentation log so it can later support the graduation book. It is not a repo activity log. Branches, merge details, file status, and task mechanics belong in active `docs/TASKS/` files while work is open; durable research evidence and reproducibility details belong here.

## Review Scope

This log covers two research streams:

- PR #10: field-level crop mapping experiments using YieldSAT Sentinel-2 seasonal field data.
- PR #11: research-only XGBoost crop inference validation around a known Corn AOI.

Current boundary:

- Crop classification remains research-only.
- Crop category is not part of the current FarmTrust land assessment output.
- Notebook metrics are not treated as production validation.
- Generated datasets, model binaries, pickles, and local research outputs should stay out of git.

## Current Research State

- This log is sequential: older blocked, failed, and superseded results are intentionally preserved to show the scientific approach over time.
- Latest branch outcome: the first AOI-passing candidate is `notebooks/08-morocco_crop_lightgbm_baseline.ipynb` configured as a Morocco-only binary `Alfalfa`/`Corn` LightGBM model using 18 AOI-compatible features: 9 brightness-normalized default Sentinel-2 band ratios plus 9 vegetation indices.
- Latest AOI result: C1 Corn -> Corn `0.999847`, C3 Corn -> Corn `0.991948`, and C4 Alfalfa -> Alfalfa `0.568402`. C4 passes but remains the weaker moderate-confidence case.
- Main scientific conclusion: the combined YieldSAT + Morocco models failed the AOI label check because of source/domain/class-boundary conflict, not because the AOI Corn seasons were impossible to classify.
- Scope remains unchanged: crop classification is research-only and is not part of the current FarmTrust production land-assessment contract.

## PR #10 - Field-Level Crop Mapping Review

### Initial Summary

PR #10 originally added a field-level crop mapping research report and four notebooks. That old report is now retired because the cleaned YieldSAT feature-store workflow supersedes the raw-raster notebook path.

Original report path, deleted after review:

- `docs/field_level_crop_mapping_experiment_report.md`

Original notebooks, retired or replaced after review:

- `notebooks/crop_mapping_v1_reflectance_baseline.ipynb`
- `notebooks/crop_mapping_full_features_final.ipynb`
- `notebooks/crop_mapping_aggressive_feature_reduction.ipynb`
- `notebooks/crop_mapping_light_reduced_final.ipynb`

Current replacement notebooks:

- `notebooks/05-yieldsat_crop_mapping_feature_store.ipynb`
- `notebooks/06-yieldsat_crop_mapping_baseline.ipynb`

Research target:

- `wheat`
- `corn`
- `other`

Initial reported results:

- Full-feature LSTM test accuracy: `0.9476`
- Full-feature LSTM validation macro F1: `0.9443`
- Full-feature XGBoost test accuracy: `0.9170`
- Full-feature tuned ensemble test accuracy: `0.9782`
- Full-feature tuned ensemble macro F1: `0.9796`
- Reduced 15-feature LSTM test accuracy: `0.9476`

Initial limitations already documented by the report:

- No full external validation.
- SCL masking assumptions were not perfectly consistent.
- Deployment behavior may be fragile.
- Some late cells in the retired light-reduced notebook failed.
- Strong notebook metrics do not guarantee robust AOI serving behavior.

### Initial Review Finding

The four PR #10 notebooks currently fail trusted `nb` inspection with:

```text
Only nbformat v4 notebooks are supported
```

The notebooks were then converted in place with `nbformat`, normalized to `nbformat_minor: 5`, and missing cell IDs were added. After this, trusted `nb read --no-output` inspection succeeded for all four notebooks.

### Planned Review Steps

1. Decide whether to convert the notebooks to nbformat v4 or ask for valid notebook exports.
2. Inspect converted notebooks with trusted notebook tooling.
3. Verify whether reported metrics are present and internally consistent.
4. Identify failed cells or non-reproducible steps.
5. Refine the report to clearly separate strong internal evidence from unresolved deployment risk.
6. Capture graduation-book figures, tables, and narrative points.

### Testing Log

| Date | Action | Result | Evidence | Follow-up |
|---|---|---|---|---|
| 2026-06-27 | Initial trusted notebook read attempt | All four PR #10 notebooks failed nbformat support check | `nb read ... --no-output` returned `Only nbformat v4 notebooks are supported` | Convert in place |
| 2026-06-27 | Convert PR #10 notebooks in place | Top-level format became `nbformat 4`, `nbformat_minor 4`, but `nb` still rejected them | `nbformat.read(..., as_version=4)` / `nbformat.write(...)` | Normalize to v4.5 and add cell IDs |
| 2026-06-27 | Normalize PR #10 notebooks to v4.5 | All four notebooks became readable by trusted `nb read --no-output` | `nbformat.validator.normalize(...)`; added missing cell IDs | Continue content inspection |

### Findings And Fixes

| Date | Finding | Impact | Fix or decision |
|---|---|---|---|
| 2026-06-27 | PR #10 notebooks lacked modern v4.5 cell IDs | Blocked trusted notebook review | Converted in place, set `nbformat_minor` to `5`, and normalized missing cell IDs |
| 2026-06-27 | Original PR #10 report and raw-raster notebooks became stale after the feature-store baseline work | Keeping them as active references would point readers to deleted notebooks and weaker preprocessing | Retired the old report; preserved useful historical metrics, field-level framing, and risk notes in this log |

### Retired PR #10 Report Notes

The retired report remains useful as historical evidence, but not as the current recommended implementation path.

Useful points preserved from it:

- The task framing is field-level target-crop screening: `wheat`, `corn`, and `other`.
- Field-level modeling is preferred over pixel-level modeling because the available labels are field labels, and field aggregation reduces pixel noise from clouds, boundaries, shadows, and registration effects.
- The old raw-raster experiments showed that seasonal Sentinel-2 sequences contain strong crop signal under grouped internal validation.
- The strongest historical PR #10 metrics were full-feature tuned ensemble macro F1 `0.9796`, full-feature LSTM accuracy `0.9476`, and light-reduced LSTM accuracy `0.9476`.
- The main historical risks were no full external validation, SCL masking inconsistency, fragile deployment behavior, and notebook cells that were not fully reproducible.

Current decision:

- Do not continue the old raw-raster/LSTM report path.
- Use the two-file YieldSAT feature store and `06-yieldsat_crop_mapping_baseline.ipynb` as the active crop-mapping research path.
- Treat old PR #10 metrics as historical evidence only, not as the model recommendation.

## PR #11 - XGBoost AOI Validation Review

### Initial Summary

PR #11 adds research-only XGBoost crop model validation around a known Corn AOI.

Notebooks:

- `notebooks/Morocco_Only_XGBoost_professional.ipynb`
- `notebooks/Merged_xgboost_training.ipynb`

Old script artifacts:

- The PR #11 AOI inference scripts were distilled into `docs/documentations/04-morocco-crop-classification-scientific-log.md` and then removed from the active workspace.
- The durable result is the scientific record, not active script entry points.

Dependencies added through the `ml` extra:

- `scikit-learn`
- `xgboost`
- `joblib`
- `openpyxl`
- `xlrd`

Main validation result:

- Known AOI label: `Corn`
- Morocco-only XGBoost predicted: `corn`
- Correct: `true`
- Confidence: `0.42813432216644287`
- Confidence status: low

Blocked model path:

- `merged_crop_5labels_xgboost`
- Blocked because the full model artifact is missing and the AOI lacks `B01`, `B09`, and `B12`.

Failed model path:

- `merged_crop_5labels_aoi_shared_bands_xgboost`
- Ran technically, but predicted `Wheat` for known `Corn`.

### Initial Review Findings

- PR #11 notebooks are nbformat v4 and readable by trusted `nb` tooling.
- The old PR #11 plan docs were distilled into `docs/documentations/04-morocco-crop-classification-scientific-log.md`; the stale merged-model training command was not preserved as an active instruction.
- `README.md` and `docs/ENGINEERING.md` still describe the `ml` extra as an empty placeholder, but PR #11 makes it real.
- The old sibling-import issue is no longer an active code issue because the PR #11 research scripts were removed after their durable findings were preserved.
- PR #11 docs are careful about research-only scope, low confidence, blocked full model inference, and failed AOI-compatible validation.

### Planned Review Steps

1. Update dependency docs so the `ml` extra is accurately described if that stale text still exists.
2. Preserve the low-confidence and failed-validation results honestly in graduation-book material.

### Testing Log

| Date | Action | Result | Evidence | Follow-up |
|---|---|---|---|---|
| 2026-06-27 | Initial notebook inspection | Both PR #11 notebooks are readable by `nb` | `nb read ... --no-output` produced notebook content | Continue script checks later |

### Findings And Fixes

| Date | Finding | Impact | Fix or decision |
|---|---|---|---|
| 2026-06-27 | `ml` docs are stale | Dependency docs conflict with `pyproject.toml` | Pending |
| 2026-06-27 | Stale training command references removed package | Users cannot run documented commands | Pending |
| 2026-06-27 | Sibling import may not work under package execution | Research script execution path was fragile | Resolved by removing old research scripts after distillation |
| 2026-06-29 | Earlier `ml` doc-staleness note was rechecked during branch closeout | No remaining markdown text describing the `ml` extra as empty was found | Resolved for this branch; `pyproject.toml` carries the active ML dependency list |

## YieldSAT Feature-Store Baseline Exploration

### Dataset And Feature Store

The current synthesis moved from raw-raster notebook experiments toward a two-file YieldSAT feature store for crop-mapping research.

Feature-store files:

- `crop_mapping_fields.parquet`
- `crop_mapping_observations.parquet`

Latest reported table shapes:

- Fields: `(2173, 936)`
- Observations: `(100670, 258)`

Crop coverage:

- soybean: `1305`
- wheat: `454`
- corn: `303`
- rapeseed: `111`

Country coverage:

- Argentina: `751`
- Uruguay: `572`
- Brazil: `551`
- Germany: `299`

Leakage boundary:

- Exclude `crop` as a feature; it is the label source.
- Exclude `target*` and `yield*` columns.
- Exclude field identity/path/provider/farm metadata from the default model features.
- Treat crop classification as research-only; do not change the FarmTrust land-assessment contract.

### Current Baseline Notebook

Notebook:

- `notebooks/06-yieldsat_crop_mapping_baseline.ipynb`

Target framing:

- `wheat`
- `corn`
- `other`

Sampling logic:

- Keep all wheat fields: `454`.
- Keep all corn fields: `303`.
- Sample `other` to match wheat count: `454`, from soybean and rapeseed with country balancing.

Latest selected-field distribution reported from the notebook:

- Selected fields: `(1211, 938)`
- wheat: `454`
- other: `454`
- corn: `303`

Validation logic:

- One row per field for tabular training.
- Observation rows are aggregated per field using mean, std, min, max, p10, and p90.
- Train/test split uses `StratifiedGroupKFold`.
- Group key is `country_year`, so the same country-year group cannot appear in both train and test.

Manual feature selection approach:

- The notebook now has an exploration section that displays feature groups and examples.
- The user manually chooses groups in `TRAINING_FEATURE_GROUPS` before training.
- No automatic correlation-based dropping is used; high label correlation is treated as possible signal unless the feature is leakage, unavailable from bbox/free APIs, or an unrealistic shortcut.

Current production-accessible feature groups selected for the first run:

- Sentinel-2 bands.
- Vegetation indices.
- SCL/cloud fractions.
- Pixel/valid counts.
- DEM/slope/aspect.
- SoilGrids soil features.
- Weather/GDD/rain/temp.

Excluded by default from this run:

- Yield/target/crop leakage columns.
- Field IDs, names, paths, provider/farm metadata.
- Country/year metadata dummies.
- Season/date-position features such as `days_after_seeding`, `days_before_harvest`, `season_progress`, and `in_declared_season` unless explicitly selected later.
- Static shortcut candidates such as centroid coordinates and CRS.

### First Production-Accessible Feature Run

Models:

- XGBoost with median imputation, `n_estimators=300`, `max_depth=4`, `learning_rate=0.05`.
- CatBoost with median imputation, `iterations=300`, `depth=5`, `learning_rate=0.05`.

Held-out test size:

- `260` fields.

XGBoost result:

- Accuracy: `0.9884615384615385`
- Macro F1: `0.9884342211460856`

XGBoost confusion matrix:

```text
[[88  0  0]
 [ 1 86  2]
 [ 0  0 83]]
```

CatBoost result:

- Accuracy: `0.9769230769230769`
- Macro F1: `0.9771205181159838`

CatBoost confusion matrix:

```text
[[85  3  0]
 [ 0 87  2]
 [ 0  1 82]]
```

### Feature-Importance Findings

XGBoost top drivers included:

- `obs_mean__scl_keep_fraction`
- `obs_max__weather_cum_gdd_base10`
- `obs_mean__s2_valid_pixel_fraction`
- `obs_mean__s2_B06_max`
- `obs_std__weather_cum_gdd_base10`
- several SoilGrids CEC features
- Sentinel-2 vegetation/band features such as SAVI, NBR, GNDVI, NDVI, MSI

CatBoost top drivers included:

- cumulative GDD/weather features
- 7-day, 14-day, and 30-day temperature/GDD features
- Sentinel-2 B06, NDVI, SAVI, NDRE, B08, and B12 features
- SoilGrids CEC features

Importance by source from the first run:

| Source | CatBoost | XGBoost |
|---|---:|---:|
| dem | `0.3454736657573548` | `0.04164201021194458` |
| s2 | `39.88739860780908` | `0.37162891030311584` |
| scl | `2.009819664992631` | `0.09967704862356186` |
| soil | `7.831037938786332` | `0.23782654106616974` |
| weather | `49.92627012265467` | `0.2492254674434662` |

### Interpretation So Far

The first production-accessible run is strong but not yet definitive. The metrics are high, but feature importance shows heavy use of weather/GDD/temp, soil, SCL/valid-pixel behavior, and Sentinel-2 signals together.

Current interpretation:

- The model is likely learning real crop signal from Sentinel-2 and vegetation-index patterns.
- The model may also be using climate, soil, country-year, or data-quality shortcuts because the crops are not evenly distributed across countries and regions.
- Weather and soil are not leakage if they can be obtained from free/public APIs, but they can still inflate internal validation when crop labels are geographically clustered.

Next ablation checks planned before stronger claims:

1. Rerun without `Weather/GDD/rain/temp`.
2. Rerun with only Sentinel-2 bands, vegetation indices, SCL/cloud fractions, and pixel/valid counts.
3. Compare metric drops and feature importances to decide whether the model is mostly visual, climate/region-driven, or mixed.

### No-Weather Ablation

The first ablation removed `Weather/GDD/rain/temp` while keeping Sentinel-2 bands, vegetation indices, SCL/cloud fractions, pixel/valid counts, DEM/slope/aspect, and SoilGrids soil features.

Held-out test size:

- `260` fields.

XGBoost result:

- Accuracy: `0.9076923076923077`
- Macro F1: `0.9067736353625925`

XGBoost confusion matrix:

```text
[[73  1 14]
 [ 0 87  2]
 [ 2  5 76]]
```

CatBoost result:

- Accuracy: `0.8961538461538462`
- Macro F1: `0.8947039897039897`

CatBoost confusion matrix:

```text
[[70  4 14]
 [ 0 87  2]
 [ 2  5 76]]
```

Metric drop relative to the first full production-accessible run:

| Model | Full macro F1 | No-weather macro F1 | Drop |
|---|---:|---:|---:|
| XGBoost | `0.9884342211460856` | `0.9067736353625925` | `0.0816605857834931` |
| CatBoost | `0.9771205181159838` | `0.8947039897039897` | `0.0824165284119941` |

No-weather feature-source importance:

| Source | CatBoost | XGBoost |
|---|---:|---:|
| dem | `0.718188` | `0.030715` |
| s2 | `86.796687` | `0.636054` |
| scl | `1.491915` | `0.024437` |
| soil | `10.993209` | `0.308794` |

Interpretation:

- Removing weather reduced macro F1 by about `0.08` for both XGBoost and CatBoost.
- The task remains strong without weather: about `0.90` macro F1.
- After weather removal, CatBoost relies mostly on Sentinel-2 features, with SoilGrids as secondary support.
- The main errors are corn predicted as wheat: XGBoost has `14` corn-to-wheat errors, and CatBoost also has `14` corn-to-wheat errors.
- This suggests weather/GDD materially helped separate crop calendars or climate regimes, especially corn versus wheat, but Sentinel-2/soil still carry substantial crop signal.

### Sentinel-2 And SCL Only Ablation

The second ablation kept only Sentinel-2 bands, vegetation indices, SCL/cloud fractions, and pixel/valid counts. It removed weather, DEM, and SoilGrids features.

Held-out test size:

- `260` fields.

XGBoost result:

- Accuracy: `0.9153846153846154`
- Macro F1: `0.9146175345060715`

XGBoost confusion matrix:

```text
[[74  2 12]
 [ 0 87  2]
 [ 1  5 77]]
```

CatBoost result:

- Accuracy: `0.8807692307692307`
- Macro F1: `0.8792108041827037`

CatBoost confusion matrix:

```text
[[68  3 17]
 [ 0 87  2]
 [ 1  8 74]]
```

Metric comparison across the three current runs:

| Run | Feature groups | XGBoost macro F1 | CatBoost macro F1 |
|---|---|---:|---:|
| Full production-accessible | Sentinel-2, vegetation indices, SCL/cloud, pixel counts, DEM, SoilGrids, weather | `0.9884342211460856` | `0.9771205181159838` |
| No weather | Sentinel-2, vegetation indices, SCL/cloud, pixel counts, DEM, SoilGrids | `0.9067736353625925` | `0.8947039897039897` |
| Sentinel-2/SCL only | Sentinel-2, vegetation indices, SCL/cloud, pixel counts | `0.9146175345060715` | `0.8792108041827037` |

Sentinel-2/SCL-only feature-source importance:

| Source | CatBoost | XGBoost |
|---|---:|---:|
| s2 | `96.272373` | `0.962561` |
| scl | `3.727627` | `0.037439` |

Interpretation:

- Pure Sentinel-2/SCL features are already strong: XGBoost reaches about `0.915` macro F1.
- XGBoost slightly improves when SoilGrids/DEM are removed compared with the no-weather run, while CatBoost drops modestly.
- SoilGrids and DEM are not required for a strong first production-oriented baseline.
- Weather/GDD remains the largest performance booster, but it likely encodes crop-calendar or climate-region information in addition to agronomic signal.
- The repeated main error pattern is still corn predicted as wheat: `12` corn-to-wheat errors for XGBoost and `17` for CatBoost.
- The evidence now supports a simple production-first baseline using Sentinel-2 bands, vegetation indices, SCL/cloud fractions, and pixel/valid counts, with weather as an optional enhancement to test separately.

### PyTorch Sequence Baseline

The sequence baseline was added to test whether temporal crop-season shape provides useful evidence beyond tabular aggregation. It is not intended to replace the tree baselines yet; its main purpose is to support temporal feature-importance analysis.

Input design:

- Temporal branch: observation-level time-series features compressed to `20` timesteps per field-season.
- Static branch: fixed field-context features such as DEM/slope/aspect and SoilGrids soil statistics.
- Static features are not repeated across timesteps; they enter through a separate MLP branch.

Selected feature groups for this run:

- Sentinel-2 bands.
- Vegetation indices.
- SCL/cloud fractions.
- Pixel/valid counts.
- DEM/slope/aspect.
- SoilGrids soil features.
- Weather/GDD/rain/temp.

Feature dimensions reported by the model:

- Temporal features: `251`.
- Static features: `909`.
- Trainable parameters: `144131`.

Architecture:

- PyTorch `InceptionTemporalStaticCNN`.
- Temporal projection: `Conv1d(251 -> 32, kernel_size=1)`.
- Two Inception-style temporal blocks with parallel `Conv1d` kernels `3`, `5`, and `9`, plus a max-pool branch.
- Residual connections and batch normalization in temporal blocks.
- Static branch: MLP from `909` static features to a `32`-feature embedding.
- Classifier combines temporal average/max pooled embedding with static embedding.
- Training restores the checkpoint with best validation macro F1 rather than lowest validation loss.

Best validation result:

- Best validation macro F1: `0.9053013785495262`.

Held-out test result:

- Accuracy: `0.8996138996138996`.
- Macro F1: `0.8952815446956611`.

Confusion matrix:

```text
[[62 11  8]
 [ 2 77  1]
 [ 0  4 94]]
```

Classification summary:

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| corn | `0.97` | `0.77` | `0.86` | `81` |
| other | `0.84` | `0.96` | `0.90` | `80` |
| wheat | `0.91` | `0.96` | `0.94` | `98` |

Main error pattern:

- Corn remains the hardest class.
- Corn was confused as `other` `11` times and as `wheat` `8` times.
- Wheat and other were learned more reliably.

Sequence group permutation importance:

| Source | Kind | Macro F1 drop | Accuracy drop |
|---|---|---:|---:|
| Sentinel-2 bands | time_series | `0.290581` | `0.289575` |
| Weather/GDD/rain/temp | time_series | `0.282402` | `0.281853` |
| Vegetation indices | time_series | `0.135962` | `0.119691` |
| SoilGrids soil features | static | `0.007983` | `0.007722` |
| DEM/slope/aspect | static | `0.006997` | `0.007722` |
| Pixel/valid counts | time_series | `0.004194` | `0.003861` |
| SCL/cloud fractions | time_series | `-0.002407` | `-0.003861` |

Top feature-level permutation signals included:

- `weather_cum_heavy_rain_days`
- `weather_30d_gdd_base10`
- `weather_cum_gdd_base10`
- `s2_BSI_p75`
- `weather_14d_gdd_base10`
- `weather_14d_Total_prec_mm`
- `weather_14d_rainy_days`
- `weather_daily_Temp_max_C`
- `s2_B08_p10`
- `weather_daily_gdd_base10`

Interpretation:

- The sequence model is now strong enough to support group-level temporal importance evidence.
- Temporal Sentinel-2 bands and weather/GDD are the dominant sequence signals.
- Vegetation indices provide a clear secondary temporal signal.
- Static soil and DEM contribute little in this architecture and split.
- SCL/cloud and pixel-count groups appear low-importance or noisy after the stronger temporal/static branch split.
- The sequence model remains weaker than the full tabular tree models for prediction, but it provides a more direct view of temporal crop-season signal.

Comparison with tabular baselines:

| Model/run | Macro F1 | Note |
|---|---:|---|
| Full XGBoost tabular | `0.9884342211460856` | Best predictive result so far |
| Full CatBoost tabular | `0.9771205181159838` | Strong tabular baseline |
| PyTorch temporal/static sequence | `0.8952815446956611` | Useful temporal feature-importance baseline |
| Sentinel-2/SCL-only XGBoost tabular | `0.9146175345060715` | Strongest simple production-first imagery baseline |

Current conclusion:

- Use XGBoost/CatBoost as the strongest predictive baselines.
- Use the PyTorch sequence model as the main temporal-feature-importance baseline.
- Treat Sentinel-2 bands and weather/GDD as the most important temporal groups until stricter external or country-held-out validation says otherwise.

## Comparison Notes

| Topic | PR #10 | PR #11 | Initial note |
|---|---|---|---|
| Main target | `wheat / corn / other` | Morocco-only four-class and merged five-label XGBoost | Targets do not match directly |
| Model family | LSTM, XGBoost, ensemble | XGBoost | PR #10 explores temporal sequence models; PR #11 focuses inference validation |
| Input style | Seasonal field sequence, 20 timesteps | Static mean AOI/field features | Feature contracts differ |
| Validation | Strong internal grouped metrics | One known Corn AOI plus notebook metrics | PR #11 has direct AOI validation evidence, but low confidence |
| Current blocker | Evidence/content review after conversion | Stale docs/import polish | PR #10 format blocker is resolved; content still needs review |
| Production readiness | Not production-ready | Not production-ready | Both remain research-only |

## Possible Combined Direction

The combined direction should take the best parts from both PRs only after review.

Candidate strengths from PR #10:

- Field-level seasonal framing.
- Group-aware validation mindset.
- LSTM sequence modeling and feature-reduction experiments.
- Clear discussion of deployment risks.

Candidate strengths from PR #11:

- Explicit research-only inference scripts.
- Known-AOI validation discipline.
- Honest blocked/failed model reporting.
- Artifact and feature-contract checks.

Possible synthesis:

- A research-only crop-classification pipeline that uses field-level seasonal evidence from PR #10, but adopts PR #11's strict inference-contract validation and known-AOI testing discipline.

Kill conditions:

- Notebook evidence cannot be inspected or reproduced.
- Feature schemas cannot be aligned.
- External or known-AOI validation remains weak.
- The work starts conflicting with the current FarmTrust assessment boundary.

## Graduation Book Evidence

Use this section to collect clean material for later writing.

| Date | Evidence item | Why it matters | Source | Figure/table needed |
|---|---|---|---|---|
| 2026-06-27 | PR #10 report reviewed and retired | Shows useful crop mapping experiment history, but is superseded by the feature-store workflow | `docs/documentations/02-crop-research-review-log.md` | Historical metrics table |
| 2026-06-27 | PR #10 notebook format blocker found and fixed | Makes the experiment notebooks inspectable as technical evidence | `nb read` failure, followed by nbformat v4.5 normalization | Notebook validation table |
| 2026-06-27 | PR #11 AOI validation reviewed initially | Shows known-label validation discipline | `docs/documentations/04-morocco-crop-classification-scientific-log.md` | AOI result table |
| 2026-06-27 | YieldSAT two-file baseline produced strong grouped test metrics | Provides current best crop-mapping research evidence, but needs ablation before strong claims | `notebooks/06-yieldsat_crop_mapping_baseline.ipynb` | Model comparison table and feature-source importance table |
| 2026-06-27 | YieldSAT no-weather ablation completed | Shows weather/GDD adds about 0.08 macro F1, while Sentinel-2/soil still reach about 0.90 macro F1 | `notebooks/06-yieldsat_crop_mapping_baseline.ipynb` | Ablation comparison table |
| 2026-06-27 | YieldSAT Sentinel-2/SCL-only ablation completed | Shows a production-simple imagery baseline can reach about 0.91 XGBoost macro F1 without weather, soil, or DEM | `notebooks/06-yieldsat_crop_mapping_baseline.ipynb` | Three-run ablation table |
| 2026-06-27 | PyTorch temporal/static sequence baseline completed | Provides temporal feature-importance evidence showing Sentinel-2 bands and weather/GDD dominate sequence signal | `notebooks/06-yieldsat_crop_mapping_baseline.ipynb` | Sequence architecture diagram and group permutation table |

## Open Questions

- Which PR #10 result is the most defensible after testing: full-feature ensemble, reduced LSTM, or report-only evidence?
- Should PR #11 remain as inference validation only, or should a cleaned training path be recreated later?
- How well does the Sentinel-2/SCL-only baseline generalize under stricter country-held-out or new-AOI validation?
- Does the sequence model's Sentinel-2/weather importance remain stable under country-held-out validation?
- What exact screenshots, tables, and diagrams are needed for the graduation book chapter?

## Next Actions

1. Add or run a stricter validation split, preferably country-held-out or AOI-held-out, for the Sentinel-2/SCL-only baseline.
2. Repeat sequence-model feature importance under a stricter split if time allows.
3. Treat Sentinel-2/SCL-only as the simplest production-first baseline unless stricter validation fails.
4. Treat weather/GDD as an optional enhancement because it improves internal metrics but may encode crop-calendar or regional shortcuts.
5. Continue PR #10 notebook evidence inspection and compare against the original report metrics.
6. Run PR #11 script checks and fix stale docs after the baseline ablations are understood.

## Final Summary

Latest branch outcome:

- Notebook 08 is the current AOI-passing research candidate, not a production contract change.
- Active labels: `Alfalfa` and `Corn`.
- Training table: `2109` rows (`Corn` 1252, `Alfalfa` 857).
- Features: `18` AOI-compatible columns: 9 brightness-normalized default S2 band ratios plus 9 vegetation indices.
- Model: LightGBM with automatic objective selection; this run used `binary`.
- Random split result: accuracy `0.9502`, macro F1 `0.9486`.
- Direct AOI check: C1 Corn -> Corn `0.999847`, C3 Corn -> Corn `0.991948`, C4 Alfalfa -> Alfalfa `0.568402`.
- Interpretation: Morocco-only binary class boundaries solved the current AOI label check. C4 Alfalfa remains moderate-confidence and should be flagged as weaker evidence.

Sequential evidence preserved above:

- Earlier Morocco-only XGBoost work showed one correct known-Corn AOI prediction with low confidence.
- Combined AOI-compatible five-label and temporal models repeatedly failed direct AOI checks despite useful internal metrics.
- The failed combined-model runs are scientifically useful because they isolate source/domain/class-boundary conflict and show that internal validation alone is not AOI validation.

Earlier feature conclusion for the YieldSAT crop-mapping baseline:

- Use a production-first feature set based on data that can be derived from a bbox using free/public sources.
- Use all primary optical features, but keep the order below as the current importance priority for reporting, debugging, and later reduction.
- Skip SoilGrids, DEM, and slope for the first production-oriented baseline. They added little in the current experiments and increase feature/API complexity.
- Keep a selected weather group as the main secondary enhancement because weather is easy to obtain from free APIs and repeatedly ranked high, while still treating it carefully because it may encode crop-calendar or regional shortcuts.

Evidence basis:

- Sentinel-2/SCL-only XGBoost reached `0.9146175345060715` macro F1, so optical imagery alone is a strong production-first baseline.
- Full XGBoost reached `0.9884342211460856` macro F1 and full CatBoost reached `0.9771205181159838` macro F1, showing that the enhanced feature set is very strong internally.
- Removing weather dropped XGBoost macro F1 by about `0.0817` and CatBoost macro F1 by about `0.0824`, so weather is the strongest secondary group.
- PyTorch sequence group permutation ranked Sentinel-2 bands first with `0.290581` macro F1 drop, weather second with `0.282402`, and vegetation indices third with `0.135962`.
- SoilGrids and DEM/slope were low in the sequence run: `0.007983` and `0.006997` macro F1 drop respectively.

Ordered primary feature groups:

1. Sentinel-2 bands.
2. Vegetation indices computed from Sentinel-2.
3. Basic SCL/cloud and valid-pixel quality features.

Ordered Sentinel-2 band priority:

1. `B06`
2. `B08`
3. `B07`
4. `B8A`
5. `B11`
6. `B12`
7. `B09`
8. `B05`
9. `B04`
10. `B03`
11. `B02`
12. `B01`

Sentinel-2 interpretation:

- Red-edge and NIR bands such as `B05`, `B06`, `B07`, `B08`, and `B8A` are prioritized because they capture canopy vigor, chlorophyll response, biomass, and phenology.
- SWIR bands `B11` and `B12` are prioritized because they capture vegetation water content, dryness, senescence, and residue/background effects.
- Visible bands `B02`, `B03`, and `B04` remain included because they support basic spectral separation and index computation, even when they are less dominant individually.
- `B01` and `B09` can be kept when available, but they are not the first operational dependency to optimize around.

Ordered vegetation-index priority:

1. `NDRE`
2. `NDMI`
3. `BSI`
4. `NBR`
5. `NDVI`
6. `SAVI`
7. `MSI`
8. `EVI`
9. `GNDVI`
10. `NDWI_GREEN`

Vegetation-index interpretation:

- `NDRE` is prioritized because red-edge response is sensitive to crop canopy and chlorophyll changes during growth.
- `NDMI` and `MSI` are prioritized because moisture and water-stress behavior helped separate crop-season patterns.
- `BSI` and `NBR` are prioritized because bare-soil, residue, dryness, and senescence patterns appeared in sequence and tree importance outputs.
- `NDVI`, `SAVI`, `EVI`, `GNDVI`, and `NDWI_GREEN` remain included because they provide robust vegetation vigor, soil-adjusted vegetation, greenness, and water-related signals.

Ordered quality-feature priority:

1. `s2_valid_pixel_fraction`
2. `s2_valid_pixel_count`
3. `scl_keep_fraction`
4. `scl_nodata_fraction`
5. `scl_cloud_fraction`

Quality-feature interpretation:

- These features are not the main crop signal, but they describe whether each observation is trustworthy.
- `s2_valid_pixel_fraction` and `s2_valid_pixel_count` were more visible in tree importance than detailed SCL classes.
- `scl_keep_fraction`, `scl_nodata_fraction`, and `scl_cloud_fraction` are retained as operational quality controls and for possible missingness/cloud-pattern effects.

Selected secondary weather features:

1. `weather_cum_gdd_base10`
2. `weather_30d_gdd_base10`
3. `weather_14d_gdd_base10`
4. `weather_7d_gdd_base10`
5. `weather_daily_gdd_base10`
6. `weather_30d_Temp_mean_C`
7. `weather_14d_Temp_mean_C`
8. `weather_7d_Temp_mean_C`
9. `weather_daily_Temp_mean_C`
10. `weather_daily_Temp_max_C`
11. `weather_daily_Temp_min_C`
12. `weather_cum_Total_prec_mm`
13. `weather_30d_Total_prec_mm`
14. `weather_14d_Total_prec_mm`
15. `weather_7d_Total_prec_mm`
16. `weather_daily_Total_prec_mm`
17. `weather_cum_rainy_days`
18. `weather_30d_rainy_days`
19. `weather_14d_rainy_days`
20. `weather_7d_rainy_days`
21. `weather_daily_rainy_day`
22. `weather_cum_heavy_rain_days`
23. `weather_daily_heavy_rain_day`
24. `weather_cum_cold_stress_days`
25. `weather_daily_cold_stress_day`
26. `weather_cum_heat_stress_days`
27. `weather_daily_heat_stress_day`

Weather interpretation:

- GDD features are selected because XGBoost, CatBoost, and the sequence model repeatedly ranked cumulative, 30-day, and 14-day GDD among the strongest weather signals. GDD represents thermal time, which controls crop development stage and separates crop calendars.
- Temperature features are selected because rolling and daily temperature signals describe crop suitability, phenological speed, heat exposure, and cold exposure. `Temp_max_C` and `Temp_min_C` help capture extremes that a mean-only feature can hide.
- Precipitation and rainy-day features are selected because rainfall timing, recent moisture availability, and rain frequency affect crop growth trajectories and can separate crop systems.
- Heavy-rain and stress-day features are selected because sequence importance highlighted `weather_cum_heavy_rain_days` and `weather_cum_cold_stress_days`; heat-stress features are kept for the same agronomic reason as cold-stress features, even if they were not the top-ranked item in this specific run.
- Daily, 7-day, 14-day, 30-day, and cumulative windows are retained because they represent different temporal scales: immediate condition, short-term weather, recent growth window, monthly context, and season-to-date crop development.
- A bbox weather-access test succeeded using the free Open-Meteo historical archive API for a sample Egypt field centroid.
- The test returned daily temperature and precipitation, and the selected GDD, rain, stress-day, rolling-window, and cumulative weather features were computable from it.

Recommended model framing:

- Minimal production baseline: Sentinel-2 bands + vegetation indices + basic SCL/valid-pixel quality.
- Enhanced production baseline: minimal baseline + selected weather/GDD/rain/temp features listed above.
- Do not include SoilGrids, DEM, slope, aspect, or terrain curvature in the first production-oriented feature set unless later stricter validation shows a clear need.
