# PR #11 Scientific Log - XGBoost AOI Crop Inference

Date started: 2026-06-28

## Version Note

This document is the old/current-work scientific snapshot for PR #11. It preserves what was known at this stage before later improvements, retraining, or redesign.

It is intended to support the graduation book by keeping the research question, experiments, progress, struggles, and interpretation in one coherent place. Later work may supersede these results.

This is research-only. Crop classification is not part of the current FarmTrust production land assessment output.

## Research Objective

The objective was to test whether a notebook-trained XGBoost crop classifier could be used for an AOI-style inference input.

The specific AOI used in this stage was known to be `Corn`. The work tested which available model path could produce a defensible current demo result while keeping failed and blocked paths visible.

## Scientific Question

Can a tabular XGBoost crop classifier trained from Sentinel-2 field features correctly classify a real AOI cube when the inference input is reduced to the bands and features available in the AOI archive?

Secondary questions:

- Does the model's expected feature schema match the AOI's available bands?
- Can a merged multi-source crop model generalize to this AOI?
- Are execution success and scientific validation success the same thing?

The answer at this stage is partial. One Morocco-only model predicted the known Corn AOI correctly, but with low confidence. The broader merged five-label model path was either blocked or failed validation.

## Working Hypotheses

Hypothesis 1: A Morocco-only XGBoost model trained from Morocco field features may work better on the current AOI than a merged model because its feature set is closer to the available AOI bands.

Status: supported only as a one-AOI smoke result. The Morocco-only model predicted `corn`, but confidence was low.

Hypothesis 2: A merged AgrifieldNet + Morocco five-label model may provide broader crop coverage.

Status: not validated in the current AOI test. The full model was blocked by missing artifact and missing AOI bands. The AOI-compatible reduced variant predicted `Wheat` for known `Corn`.

Hypothesis 3: Missing spectral bands should not be imputed just to force a model to run.

Status: accepted as a research guardrail. Missing `B01`, `B09`, and `B12` blocked the full merged model instead of being invented.

## Data And AOI Context

The tested AOI archive was:

- `D:\My_Downloads\aoi_demo_01 (1).rar`

The extracted AOI input contained:

- `cube.zarr`
- known actual label: `Corn`
- archive member count: `8763`

Available Zarr variables included:

- `B02`
- `B03`
- `B04`
- `B05`
- `B06`
- `B07`
- `B08`
- `B8A`
- `B11`
- `SCL`
- `mgrs_tiles`
- `min_cloud_cover`
- `source_item_ids`

Important missing bands:

- `B01`
- `B09`
- `B12`

No missing bands were imputed or synthesized.

## Model Paths Investigated

### Morocco-Only XGBoost

Notebook source:

- `notebooks/Morocco_Only_XGBoost_professional.ipynb`

Local artifact folder:

- `models/Moroco_only_Model/`

Target classes:

- `corn`
- `other_crop`
- `soil`
- `wheat`

The notebook trained a tabular XGBoost classifier from Morocco field-level Sentinel-2 features. It did not use the `Photos/` folder as image input. It used consolidated tabular CSV features.

Training data recorded by the notebook:

- labels table shape: `(7124, 9)`
- features table shape: `(7124, 17)`
- filtered rows after label cleaning: `6762`

Class counts after filtering:

- `wheat`: `2614`
- `other_crop`: `1954`
- `corn`: `1252`
- `soil`: `942`

Notebook holdout evidence:

- best CV macro F1: `0.7305293112128431`
- tuned holdout accuracy: `0.7531411677753141`
- tuned holdout macro F1: `0.73`

Final feature count: `17`.

Raw and engineered features included:

- `B2`, `B3`, `B4`, `B5`, `B6`, `B7`, `B8`, `B8A`, `B11`, `NDVI`
- `NDWI`, `NDBI`, `SAVI`, `BSI`, `B11_B8_ratio`, `B4_B8_ratio`, `B8_B4_diff`

Inference preprocessing reproduced the notebook contract:

- mean-aggregate AOI Zarr bands
- compute `NDVI`
- apply saved clipping bounds
- compute engineered indices
- reorder by `feature_cols_v2.pkl`
- predict probabilities with XGBoost

### Full Merged Five-Label XGBoost

Notebook source:

- `notebooks/Merged_xgboost_training.ipynb`

Research purpose:

- combine AgrifieldNet and Morocco field-level samples
- test a broader five-label crop classifier

Five retained labels:

- `Corn`
- `Potatoes`
- `Rice`
- `Sugarcane`
- `Wheat`

The merged dataset contained `11284` rows and `16` columns before five-label filtering. After removing unsupported labels, `7200` rows remained.

Source counts in the merged CSV:

- `morocco`: `6762`
- `agrifieldnet`: `4522`

The full model expected these static mean features:

- `B01_mean`
- `B02_mean`
- `B03_mean`
- `B04_mean`
- `B05_mean`
- `B06_mean`
- `B07_mean`
- `B08_mean`
- `B8A_mean`
- `B09_mean`
- `B11_mean`
- `B12_mean`
- `NDVI_mean`

Notebook holdout evidence for the full five-label model:

- accuracy: `0.845139`
- macro F1: `0.753623`
- weighted F1: `0.849403`
- 5-fold mean macro F1: `0.7696`

Current status in AOI testing:

- blocked because the expected local full model artifact was missing
- also incompatible with the current AOI unless a full-band AOI provides `B01`, `B09`, and `B12`

### AOI-Compatible Reduced Five-Label XGBoost

This variant was created to match the current AOI's available shared bands.

Feature schema:

- `B02_mean`
- `B03_mean`
- `B04_mean`
- `B05_mean`
- `B06_mean`
- `B07_mean`
- `B08_mean`
- `B8A_mean`
- `B11_mean`

It intentionally excluded:

- `B01_mean`
- `B09_mean`
- `B12_mean`

Notebook holdout evidence:

- accuracy: `0.8354166666666667`
- macro F1: `0.7305025296798493`
- weighted F1: `0.8409700758719112`

This model ran technically on the AOI, but failed validation by predicting `Wheat` for known `Corn`.

## Experiment Timeline

| Stage | Action | Result | Scientific Meaning |
|---|---|---|---|
| Clean restart | Focused on notebook-trained XGBoost artifacts instead of old experiment entry points | Dedicated research inference path created | Reduced implementation noise and isolated the experiment |
| Deterministic AOI aggregation | Used mean aggregation over available AOI cube values | One simple reproducible AOI row | Avoided unvalidated timestamp-selection behavior |
| Morocco-only inference | Ran notebook-compatible preprocessing and prediction | Predicted `corn` for known `Corn` | Useful one-AOI smoke evidence, but not broad validation |
| Full merged model check | Tried to evaluate the broader five-label model path | Blocked by missing artifact and missing AOI bands | Execution could not produce a valid prediction |
| AOI-compatible five-label test | Used shared available bands only | Predicted `Wheat` for known `Corn` | Model ran, but failed validation |
| Diagnostics | Checked class order, feature order, clipping, and holdout confusion | No label-order or feature-order bug found | Failure is likely model/data/schema related |

## Implementation History Preserved From Old Task

This section distills the old T-07 task notes. The task file was removed because it belonged to the old implementation cycle, while the durable knowledge belongs here.

The work started with a clean restart from notebook-trained XGBoost artifacts only. Training was treated as external and was not reproduced inside the FarmTrust product pipeline.

The implemented research path was intentionally narrow:

- one dedicated research script path, later removed after its durable findings were preserved here
- one model family: XGBoost
- one deterministic AOI aggregation method: mean over available AOI values
- one notebook-compatible preprocessing contract
- one research/demo output table with class probabilities and confidence

The early implementation included timestamp-selection options, but those were removed because they made the demo path look more precise than the evidence supported. The final old-work version used mean aggregation only.

Research outputs were kept local/ignored. The archive test wrote JSON and CSV outputs under `data/research/merged_crop_classification/`, but those outputs were evidence artifacts, not production data.

Important implementation decisions preserved from T-07:

- The work remained research-only and did not modify canonical FarmTrust assessment output.
- No retraining was done during archive inference validation.
- Missing full-model bands were not imputed.
- The full merged five-label model was allowed to be blocked rather than forced to run.
- The AOI-compatible five-label model used only shared AOI features.
- The demo did not claim timestamp-selected predictions were validated.

The old task also recorded the exact notebook preprocessing order used by the Morocco-only inference path:

- compute `NDVI`
- clip common features with saved bounds
- compute engineered indices
- reorder by `feature_cols_v2.pkl`
- predict with the XGBoost artifact

Supported AOI band aliases included:

- `B02` -> `B2`
- `B03` -> `B3`
- `B04` -> `B4`
- `B05` -> `B5`
- `B06` -> `B6`
- `B07` -> `B7`
- `B08` -> `B8`

This implementation history matters for the graduation book because it shows the method became simpler over time: from exploratory scripts and timestamp ideas toward a narrow, reproducible, inference-only experiment.

## Results Summary

| Model | Status | Predicted | Actual | Correct | Interpretation |
|---|---|---|---|---:|---|
| `morocco_only_xgboost` | `ok` | `corn` | `Corn` | `true` | Passed this one AOI smoke validation with low confidence |
| `merged_crop_5labels_xgboost` | `blocked` |  | `Corn` |  | Missing full artifact; AOI also lacks required full-band inputs |
| `merged_crop_5labels_aoi_shared_bands_xgboost` | `ok` | `Wheat` | `Corn` | `false` | Ran technically but failed known-label validation |

Morocco-only probabilities:

- `proba_corn`: `0.42813432216644287`
- `proba_other_crop`: `0.07592978328466415`
- `proba_soil`: `0.20565509796142578`
- `proba_wheat`: `0.290280818939209`
- confidence status: `low`

AOI-compatible five-label probabilities:

- `proba_corn`: `0.014917795546352863`
- `proba_potatoes`: `0.0002640655147843063`
- `proba_rice`: `0.00008443059050478041`
- `proba_sugarcane`: `0.00020094447245355695`
- `proba_wheat`: `0.9845327734947205`

## Progress Achieved

- A clean research-only inference path was created for a notebook-trained XGBoost model.
- The AOI archive could be opened and reduced into a model input row.
- The Morocco-only artifact chain was traceable from notebook to local artifacts to inference output.
- The known Corn AOI was predicted correctly by the Morocco-only model.
- The result was not overstated because confidence was low.
- Missing-band imputation was avoided.
- Blocked inference and failed validation were separated clearly.
- Diagnostics confirmed that the AOI-compatible five-label failure was not caused by label mapping or feature order.

## Struggles And Blockers

The central struggle was feature-schema mismatch between training and inference.

The full merged five-label model expected a richer static feature schema than the current AOI could provide. The AOI lacked `B01`, `B09`, and `B12`, and the local full model artifact was missing. This made the full merged path blocked, not scientifically failed.

The reduced AOI-compatible five-label model solved the execution schema problem by using only shared bands, but it lost potentially useful information such as `NDVI_mean` and other computable indices. It then predicted `Wheat` with high confidence for a known Corn AOI.

Diagnostics showed:

- label encoder order was correct
- probability order was correct
- feature order matched the artifact contract
- six of nine AOI features clipped high
- computed AOI NDVI was available but not used by the reduced five-label model
- notebook holdout behavior already showed Corn-to-Wheat confusion: `35 / 311`, about `11.25%`

This means the failure is probably not a simple code bug. It is more likely a model generalization and feature-design problem.

## Scientific Interpretation

The Morocco-only model is the current selected demo model only because it is the only path that both ran and predicted the known AOI label correctly.

The result is weak evidence because it is based on one AOI and low confidence. It is still useful because it verifies that the notebook-trained tabular model can be connected to an AOI cube inference path without changing FarmTrust production output.

The merged five-label direction remains scientifically interesting, but it is not validated at this stage. Its current challenge is not just model quality; it is the mismatch between training features, artifact availability, and real AOI data availability.

The AOI-compatible reduced model teaches an important negative lesson: making a model executable by reducing features is not enough. The reduced schema must still preserve discriminative crop information and must be validated on known AOIs.

## Validity Threats

- Only one known AOI was tested.
- The Morocco-only model confidence was low.
- The AOI may not represent the training distribution.
- The full merged model was not fully tested because the artifact was missing.
- The current AOI lacks bands required by the full merged model.
- The AOI-compatible reduced model omitted `NDVI_mean`, even though it was computable from available `B08` and `B04`.
- Internal notebook metrics do not prove AOI deployment robustness.
- There is no broad external validation set of AOIs with known crop labels yet.

## Lessons Learned

- Scientific validation must distinguish technical execution from correct prediction.
- A blocked model is different from a failed model.
- Missing Sentinel-2 bands should block incompatible model paths instead of being invented.
- A single correct AOI prediction is only smoke evidence.
- Low confidence must remain visible in reporting.
- Feature-schema design is a first-order scientific issue, not just an implementation detail.
- A production-style AOI model should be trained on the same features that can be reliably computed from future AOI inputs.
- Reduced shared-band models need additional validation and may need computed indices such as `NDVI_mean`.

## Graduation Book Material To Preserve

Potential narrative:

- The project tested a practical bridge from notebook-trained crop classification models to AOI-level inference.
- The first Morocco-only model produced a correct Corn prediction, but low confidence showed that correctness alone is insufficient.
- The broader merged model idea exposed a real research challenge: the training schema must match the data that production-like AOIs can actually provide.
- A reduced AOI-compatible model ran successfully but failed scientifically, demonstrating why execution success is not validation success.

Potential table:

| Experiment | Outcome | Lesson |
|---|---|---|
| Morocco-only XGBoost | Correct Corn prediction, low confidence | Useful proof of inference path, not production validation |
| Full merged five-label model | Blocked | Required artifacts and bands must exist before testing |
| AOI-compatible five-label model | Wrong Wheat prediction | Schema compatibility alone does not guarantee crop separability |

Potential figure ideas:

- AOI inference pipeline diagram: `cube.zarr -> band aggregation -> indices -> XGBoost -> probabilities`.
- Model comparison table showing `ok`, `blocked`, and `failed validation` as separate outcomes.
- Feature-schema mismatch diagram comparing full merged model features with available AOI bands.

## Next Experiments

For the current Morocco-only path:

- Keep the low confidence visible.
- Test more known-label AOIs.
- Record confusion patterns across AOIs, not only a single prediction.

For the full merged five-label path:

- Restore or regenerate the full model artifact if this path remains important.
- Test only with AOIs that include the full required band set.
- Do not force prediction by imputing absent bands.

For the AOI-compatible five-label path:

- Treat the current model as failed validation.
- Add computed `NDVI_mean` and other indices available from shared bands.
- Validate against more known Corn and Wheat AOIs to investigate Corn/Wheat confusion.
- Recheck whether feature clipping indicates out-of-distribution AOI values.

For the graduation-book storyline:

- Present this stage as an honest research iteration.
- Highlight the methodological discipline: trace artifacts, validate with known labels, preserve failures, and do not promote weak evidence into production claims.
