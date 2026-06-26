# T-07 - Morocco XGBoost AOI Demo Inference

## Goal

Create clean research-only inference paths for AOI demo data using ready notebook-trained crop XGBoost model artifacts. Training is external and is not reproduced in this project.

## Scope

IN:
- Add `scripts/research/infer_morocco_xgboost_demo.py`.
- Load notebook artifacts from `--model-dir`: `xgb_tuned_v2_indices_weighted.pkl`, `label_encoder_v2.pkl`, `feature_cols_v2.pkl`, `clip_lower_common.pkl`, and `clip_upper_common.pkl`.
- Accept `--demo-path`, `--model-dir`, and `--output-csv`.
- Support demo input as a CSV with Sentinel-2 bands, a `cube.zarr` path, or an AOI directory containing `cube.zarr`.
- Aggregate CSV rows and Zarr values with mean only.
- Apply the notebook preprocessing contract, predict XGBoost probabilities, and write clean demo output columns.
- Add an inference-only archive test for `aoi_demo_01(1).rar` under `data/research/merged_crop_classification/`.
- Evaluate the ready merged five-label artifact set when the AOI archive contains the required static mean features.

OUT:
- Canonical FarmTrust land assessment JSON or product/API/portal output.
- Training code, model fitting, model comparison, alternate model families, or productized crop classification.
- Imputing absent bands into the five-label merged model input row.

## Role Split

- Driver: clean old research experiment files and implement the dedicated XGBoost demo CLI.
- Reviewer: verify artifact loading, band validation, preprocessing order, output columns, and local demo run.
- Curator: keep the work research-only and avoid changes to canonical assessment outputs.

## Chosen approach

Use a dedicated script under `scripts/research` so the demo path is explicit and isolated from product assessment code. Keep the implementation narrow: one model family, mean-only aggregation, and one prediction CSV contract.

## Task List

- [x] Remove old experiment entry points from the active workspace.
- [x] Remove stale experiment task notes.
- [x] Add the clean Morocco XGBoost demo inference script.
- [x] Clean old research generated outputs.
- [x] Verify `py_compile`, `--help`, and one local AOI inference run.
- [x] Revert timestamp-selection options and keep one deterministic mean-over-demo path.
- [x] Remove legacy project training package and merged-data CSV.
- [x] Add a research-only archive inference smoke test for `aoi_demo_01(1).rar`.
- [x] Save merged crop archive test outputs as local ignored JSON and CSV.
- [x] Document the current archive inference result and next validation path.
- [x] Add the AOI-compatible shared-band five-label model to the archive inference test.
- [x] Run archive inference and save updated JSON/CSV results.

## Feedback Log

- 2026-06-25: User requested a clean restart from the notebook-trained XGBoost model only, with one dedicated demo inference path.
- 2026-06-25: Added `scripts/research/infer_morocco_xgboost_demo.py`, removed stale untracked experiment entry points and generated research outputs, and verified the clean AOI demo inference run.
- 2026-06-25: User requested reverting timestamp-selection options to keep the clean demo inference script simple and deterministic.
- 2026-06-25: Reverted the script to one mean-over-demo path, removed timestamp-selected generated CSVs, and verified `py_compile`, `--help`, and clean default AOI inference.
- 2026-06-25: User requested inference-only cleanup and removal of legacy project training work. Removed legacy training entry point: `scripts/research/crop_classification/train_xgboost_crop_model.py`.
- 2026-06-25: Removed the legacy training helper package and `data/combined_model_ready_scaled.csv`; verified compile, help, and clean AOI inference after cleanup.
- 2026-06-26: User added `aoi_demo_01(1).rar` as inference-only test data with known actual crop `Corn`, and requested research-only outputs under `data/research/merged_crop_classification/`.
- 2026-06-26: Added `scripts/research/infer_merged_crop_archive_test.py`, extracted the archive locally, and wrote `inference_test_results.json` plus `inference_test_results.csv`. Morocco-only predicted `corn` correctly; the merged five-label model was blocked because the archive lacks `B01_mean`, `B09_mean`, and `B12_mean`.
- 2026-06-26: User added an AOI-compatible five-label XGBoost artifact set trained on the shared AOI bands: `B02_mean`, `B03_mean`, `B04_mean`, `B05_mean`, `B06_mean`, `B07_mean`, `B08_mean`, `B8A_mean`, and `B11_mean`.
- 2026-06-26: Updated `scripts/research/infer_merged_crop_archive_test.py` to run the AOI-shared-band five-label model without imputing `B01`, `B09`, or `B12`. The AOI-shared model predicted `Wheat` for the known Corn AOI, so `is_correct=False`.

## Decisions

- This remains research-only and must not modify canonical FarmTrust assessment output.
- Training is external and not reproduced in this project.
- No retraining was done for the archive inference test.
- Mean is the only aggregation method for CSV rows and Zarr values.
- The clean demo output columns are `pred_class`, `proba_corn`, `proba_other_crop`, `proba_soil`, `proba_wheat`, `confidence`, and `confidence_status`.
- The merged five-label model must receive `B01_mean`, `B02_mean`, `B03_mean`, `B04_mean`, `B05_mean`, `B06_mean`, `B07_mean`, `B08_mean`, `B8A_mean`, `B09_mean`, `B11_mean`, `B12_mean`, and `NDVI_mean`; missing bands should block that model result instead of being invented.
- The AOI-compatible five-label model uses only shared AOI features and must not impute `B01`, `B09`, or `B12`.

## Open Questions

- The current local AOI archive includes `B02`, `B03`, `B04`, `B05`, `B06`, `B07`, `B08`, `B8A`, and `B11`, but not `B01`, `B09`, or `B12`. A full-band archive is required before the merged five-label model can produce a real prediction.
- The current local full five-label artifact `models/Merged_Morocco_AgriNet_Model/xgb_merged_crop_5labels.pkl` is not present. The archive script records this model as blocked instead of failing the whole run.

## Knowledge to Keep

- Required raw bands are `B2`, `B3`, `B4`, `B5`, `B6`, `B7`, `B8`, `B8A`, and `B11`.
- Supported Zarr/CSV aliases are `B02` -> `B2`, `B03` -> `B3`, `B04` -> `B4`, `B05` -> `B5`, `B06` -> `B6`, `B07` -> `B7`, and `B08` -> `B8`.
- Notebook preprocessing order: compute NDVI, clip common features with saved bounds, compute engineered indices, reorder by `feature_cols_v2.pkl`, then predict.
- The demo averages over the available AOI cube values and does not claim timestamp-selected predictions are validated.

## Current Archive Inference Result

- AOI archive tested: `D:\My_Downloads\aoi_demo_01 (1).rar`.
- Extracted location: `data/research/merged_crop_classification/test_inputs/aoi_demo_01/`.
- Detected input: `cube.zarr`.
- Available bands: `B02`, `B03`, `B04`, `B05`, `B06`, `B07`, `B08`, `B8A`, and `B11`.
- Known actual label: `Corn`.
- Morocco-only result: `morocco_only_xgboost` predicted `corn`; `is_correct=True`; `status=ok`.
- Merged five-label result: `merged_crop_5labels_xgboost` was blocked with `status=blocked_missing_required_features`.
- Missing merged five-label features: `B01_mean`, `B09_mean`, and `B12_mean`.
- Interpretation: the merged five-label result is a valid blocked inference caused by input schema mismatch, not a failed crop prediction.
- No missing bands were imputed or invented.
- No production scoring or canonical FarmTrust assessment output was changed.

## Current AOI-Shared Five-Label Result

- Model: `merged_crop_5labels_aoi_shared_bands_xgboost`.
- Artifact: `models/Merged_Morocco_AgriNet_Model/xgb_merged_crop_5labels_aoi_shared_bands.pkl`.
- Feature schema: `B02_mean`, `B03_mean`, `B04_mean`, `B05_mean`, `B06_mean`, `B07_mean`, `B08_mean`, `B8A_mean`, and `B11_mean`.
- No `B01`, `B09`, or `B12` imputation was used.
- Result on known Corn AOI: predicted `Wheat`; `is_correct=False`.
- Probabilities: `proba_wheat=0.984533`, `proba_corn=0.014918`, `proba_potatoes=0.000264`, `proba_sugarcane=0.000201`, `proba_rice=0.000084`.

## Done Summary

- Clean research-only XGBoost demo baseline is implemented and verified. Local AOI demo output may be low confidence; current verified Morocco-only output is `pred_class=corn`, `confidence=0.428134`, `confidence_status=low`. The archive test output records a correct Morocco-only `corn` prediction, a blocked original full five-label result in the current local artifact state, and an incorrect AOI-shared five-label prediction of `Wheat` for the known Corn AOI. Canonical FarmTrust assessment output was not changed.
