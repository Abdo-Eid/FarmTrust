# P-07 - Crop Classification Inference Validation Report

## Objective

Document the research-only crop classification inference validation work for the current AOI/demo input.

The AOI is known to be `Corn`. The goal was to test which locally available trained crop model can currently be trusted for this AOI/demo path, while keeping all crop-classification work outside canonical FarmTrust assessment output.

This report separates technical execution success from model validation success. A model can run successfully and still fail validation if it predicts the wrong crop.

## Scope

IN:
- Inspect local model artifacts, research scripts, generated inference outputs, generated diagnostics, and existing task/plan notes.
- Link the Morocco dataset to the exact notebook, exported artifacts, inference scripts, and validation outputs used on this branch.
- Document the current AOI inference result for discovered crop models.
- Identify the selected model for current AOI/demo validation.
- Document blocked and failed-validation models honestly.

OUT:
- Production scoring changes.
- Canonical FarmTrust assessment output changes.
- Missing-band imputation.
- Retraining or model fitting during this inference validation.

## Test Input

Source of truth: `data/research/merged_crop_classification/outputs/inference_test_results.json`.

- Input archive: `D:\My_Downloads\aoi_demo_01 (1).rar`
- Extracted location: `data/research/merged_crop_classification/test_inputs/aoi_demo_01`
- Detected input: `cube.zarr`
- Known actual label: `Corn`
- Archive member count: `8763`
- Research-only: `true`
- Training used during inference: `false`

Available Zarr variables:

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

Band/source grouping:

- Root group: `B02`, `B03`, `B04`, `B08`
- `20m` group: `B05`, `B06`, `B07`, `B8A`, `B11`, `SCL`

The AOI does not provide `B01`, `B09`, or `B12`. No missing bands were imputed or invented.

## Morocco Dataset And Notebook Workflow

### Dataset Source

Provided Google Drive source:

- `https://drive.google.com/drive/folders/18BDNzhdPw-oMsmQLzmngSg7r3nziz8R-?usp=sharing`

The training dataset itself is not checked into the current project workspace. A targeted local search under the project and `D:\My_Downloads` did not find `morocco_labels_with_features.csv` or `morocco_field_features.csv` at documentation time.

The executed Morocco notebook records the source Drive location it used:

- `BASE_PATH = /content/drive/MyDrive/Crop and irrigation type dataset for Moroccan`
- `OUTPUT_DIR = /content/drive/MyDrive/morocco_clean_outputs`

The notebook's executed directory preview shows this dataset structure:

- `Features/`
- `Photos/`
- `morocco_field_features.csv`
- `morocco_labels_with_features.csv`

Current local project state keeps the reusable outputs from that workflow:

- Notebook: `notebooks/Morocco_Only_XGBoost_professional.ipynb`
- Exported artifacts: `models/Moroco_only_Model/`
- Research inference outputs: `data/research/merged_crop_classification/outputs/` and `data/research/morocco_crop_demo/`

### Notebook Used

Morocco-only training notebook:

- `notebooks/Morocco_Only_XGBoost_professional.ipynb`

The notebook title is `XGBoost Crop Classification for Morocco`. It trains and evaluates a four-class XGBoost classifier for:

- `wheat`
- `corn`
- `soil`
- `other_crop`

### Data Loading Logic

The notebook loads tabular CSVs from Google Drive:

- Labels: `morocco_labels_with_features.csv`
- Field features: `morocco_field_features.csv`

The executed notebook output records:

- `labels_df shape: (7124, 9)`
- `features_df shape: (7124, 17)`

The field-feature table includes the tabular model inputs and metadata:

- `parcel_id`
- Sentinel-2 columns: `B1`, `B2`, `B3`, `B4`, `B5`, `B6`, `B7`, `B8`, `B8A`, `B9`, `B11`, `B12`
- `NDVI`
- `label`
- `irrigation`
- `zone`

`Photos/` is not used by the Morocco-only model. Based on notebook source inspection, the notebook only previews the folder name; it does not load image files, use image libraries, or train on photo/image data. The selected Morocco-only model is tabular-feature only.

`Features/` is also not traversed directly by this notebook. The notebook uses the consolidated tabular feature CSV `morocco_field_features.csv`; if files under `Features/` were used upstream to create that CSV, that aggregation step is outside this notebook and is not reproduced in this project.

### Preprocessing Steps

The notebook's preprocessing source of truth is `notebooks/Morocco_Only_XGBoost_professional.ipynb`.

Label cleaning and consolidation:

- `Wheat` -> `wheat`
- `Corn` -> `corn`
- `Bare soil` -> `soil`
- `Alfalfa`, `Beets`, `Potatoes`, `Tomatoes`, `Sugarcane`, `Rice`, and `Beans` -> `other_crop`
- Labels outside this map are filtered out.

After label filtering:

- Rows before: `7124`
- Rows after: `6762`
- Class counts:
  - `wheat`: `2614`
  - `other_crop`: `1954`
  - `corn`: `1252`
  - `soil`: `942`

Missing-value handling:

- The modeling bands and `NDVI` are non-null after filtering in the executed notebook.
- `irrigation` has missing values, but it is metadata and is not used as a model feature.

Clipping:

- The notebook clips only the common model inputs at the 1st and 99th percentiles.
- Clipped columns: `B2`, `B3`, `B4`, `B5`, `B6`, `B7`, `B8`, `B8A`, `B11`, `NDVI`
- These clipping bounds are saved as `clip_lower_common.pkl` and `clip_upper_common.pkl`.

Scaling/normalization:

- No scaler artifact is used for the Morocco-only XGBoost model.
- The preprocessing artifact is quantile clipping, not standardization or min-max scaling.

Train/test and tuning:

- `LabelEncoder` encodes the four cleaned classes.
- Stratified train/test split uses `test_size=0.2` and `random_state=42`.
- Class-balanced sample weights are computed with `compute_sample_weight(class_weight='balanced')`.
- The tuned model uses `RandomizedSearchCV` with `25` candidates, `StratifiedKFold(n_splits=3, shuffle=True, random_state=42)`, and `scoring='f1_macro'`.
- Best CV macro F1 recorded in the notebook: `0.7305293112128431`.
- Final tuned holdout accuracy: `0.7531411677753141`.
- Final tuned holdout macro average F1: `0.73`.

### Feature Engineering

The final Morocco-only model uses `17` features.

Raw Sentinel-2 and NDVI inputs:

- `B2`
- `B3`
- `B4`
- `B5`
- `B6`
- `B7`
- `B8`
- `B8A`
- `B11`
- `NDVI`

Engineered indices and ratios:

- `NDWI = (B3 - B8) / (B3 + B8 + 1e-6)`
- `NDBI = (B11 - B8) / (B11 + B8 + 1e-6)`
- `SAVI = 1.5 * (B8 - B4) / (B8 + B4 + 0.5 + 1e-6)`
- `BSI = ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2) + 1e-6)`
- `B11_B8_ratio = B11 / (B8 + 1e-6)`
- `B4_B8_ratio = B4 / (B8 + 1e-6)`
- `B8_B4_diff = B8 - B4`

Final feature order from `feature_cols_v2.pkl`:

- `B2`
- `B3`
- `B4`
- `B5`
- `B6`
- `B7`
- `B8`
- `B8A`
- `B11`
- `NDVI`
- `NDWI`
- `NDBI`
- `SAVI`
- `BSI`
- `B11_B8_ratio`
- `B4_B8_ratio`
- `B8_B4_diff`

Source columns deliberately not used in the final Morocco-only model include `parcel_id`, `label`, `irrigation`, `zone`, `B1`, `B9`, and `B12`.

### Artifacts Produced By The Notebook

The notebook save cell writes these artifacts to `/content/drive/MyDrive/morocco_clean_outputs`:

- `xgb_tuned_v2_indices_weighted.pkl`
- `label_encoder_v2.pkl`
- `feature_cols_v2.pkl`
- `clip_lower_common.pkl`
- `clip_upper_common.pkl`

The corresponding local project copies are in:

- `models/Moroco_only_Model/xgb_tuned_v2_indices_weighted.pkl`
- `models/Moroco_only_Model/label_encoder_v2.pkl`
- `models/Moroco_only_Model/feature_cols_v2.pkl`
- `models/Moroco_only_Model/clip_lower_common.pkl`
- `models/Moroco_only_Model/clip_upper_common.pkl`

Artifact load checks confirm:

- Label encoder classes: `corn`, `other_crop`, `soil`, `wheat`
- Feature count: `17`
- Clip bounds cover `B2`, `B3`, `B4`, `B5`, `B6`, `B7`, `B8`, `B8A`, `B11`, and `NDVI`

Loading currently emits a scikit-learn pickle version compatibility warning for the label encoder. This is not fatal in the current local test, but it should be tracked if the runtime environment changes.

### Inference Pipeline Link

Primary Morocco-only script:

- `scripts/research/infer_morocco_xgboost_demo.py`

Archive comparison script that also runs the Morocco-only model:

- `scripts/research/infer_merged_crop_archive_test.py`

For AOI `cube.zarr` input, the inference path:

- Reads Zarr root and `20m` groups.
- Maps AOI band aliases into the Morocco model schema:
  - `B02` -> `B2`
  - `B03` -> `B3`
  - `B04` -> `B4`
  - `B05` -> `B5`
  - `B06` -> `B6`
  - `B07` -> `B7`
  - `B08` -> `B8`
  - `B8A` -> `B8A`
  - `B11` -> `B11`
- Aggregates available AOI values with `np.nanmean`.
- Computes `NDVI`.
- Applies `clip_lower_common.pkl` and `clip_upper_common.pkl`.
- Computes the same engineered indices as the notebook.
- Reorders columns using `feature_cols_v2.pkl`.
- Calls `predict_proba`.
- Decodes the class with `label_encoder_v2.pkl`.

This is research-only and is not part of FarmTrust canonical land assessment output.

### AOI Validation Result

Source files:

- `data/research/merged_crop_classification/outputs/inference_test_results.json`
- `data/research/merged_crop_classification/outputs/inference_test_results.csv`

Known AOI actual label:

- `Corn`

Morocco-only result:

- `model_name`: `morocco_only_xgboost`
- `status`: `ok`
- `predicted_label`: `corn`
- `known_actual_label`: `Corn`
- `is_correct`: `True`
- `proba_corn`: `0.42813432216644287`
- `proba_other_crop`: `0.07592978328466415`
- `proba_soil`: `0.20565509796142578`
- `proba_wheat`: `0.290280818939209`

The one-row demo output at `data/research/morocco_crop_demo/prediction.csv` records:

- `pred_class`: `corn`
- `confidence`: `0.42813432216644287`
- `confidence_status`: `low`

### Why This Model Is Selected For The Current Demo

The Morocco-only model is selected for the current research/demo path because:

- Its notebook-to-artifact-to-inference chain is traceable in the project.
- Its required AOI bands are available in the current `cube.zarr`.
- Its preprocessing is reproduced by the inference scripts.
- It predicted the known Corn AOI as `corn`.
- The merged five-label alternatives are either blocked in the current local state or failed this AOI validation.

Selection is limited to research/demo validation. The low confidence must remain visible, and no crop classification result should be promoted into production scoring yet.

### Relationship To Merged Five-Label Research

Separate notebook:

- `notebooks/Merged_xgboost_training.ipynb`

That notebook is the merged AgriFieldNet + Morocco research path. It is separate from the Morocco-only selected demo model.

The merged notebook:

- Loads `combined_model_ready_scaled.csv`.
- Keeps five labels: `Corn`, `Potatoes`, `Rice`, `Sugarcane`, and `Wheat`.
- Uses static mean features `B01_mean`, `B02_mean`, `B03_mean`, `B04_mean`, `B05_mean`, `B06_mean`, `B07_mean`, `B08_mean`, `B8A_mean`, `B09_mean`, `B11_mean`, `B12_mean`, and `NDVI_mean`.
- Excludes metadata from model input.
- Also creates a separate AOI-compatible reduced feature variant using `B02_mean`, `B03_mean`, `B04_mean`, `B05_mean`, `B06_mean`, `B07_mean`, `B08_mean`, `B8A_mean`, and `B11_mean`.

Current merged-model status:

- The original full merged model artifact `xgb_merged_crop_5labels.pkl` is not present locally, and the current AOI also lacks `B01`, `B09`, and `B12`.
- The AOI-compatible reduced five-label model ran but predicted `Wheat` for the known Corn AOI, so it failed validation.
- No missing bands were imputed, no retraining was run during inference validation, and no production output was changed.

## Merged AgrifieldNet + Morocco Dataset Workflow

### Dataset Purpose

The merged dataset is a research dataset intended to combine field-level Sentinel-2 features from:

- AgrifieldNet field-level samples
- Morocco field-level samples

It is separate from the currently selected Morocco-only demo model. The merged path is documented because it is the research workflow behind the full five-label notebook and the later AOI-compatible reduced-feature experiment, but it is not the selected current AOI/demo model.

### Processed Merged CSV

Discovered local CSV:

- `C:\Users\Al-Ahram\Documents\GitHub\combined_model_ready_scaled.csv`

The attachment refers to `combined_model_ready_scaled(1).csv`; the local file currently found is named `combined_model_ready_scaled.csv`.

Actual discovered CSV shape:

- Rows: `11284`
- Columns: `16`
- Duplicate rows: `0`

Columns:

- `field_id`
- `source`
- `target_class`
- `B01`
- `B02`
- `B03`
- `B04`
- `B05`
- `B06`
- `B07`
- `B08`
- `B8A`
- `B09`
- `B11`
- `B12`
- `NDVI`

Source counts:

- `morocco`: `6762`
- `agrifieldnet`: `4522`

Classes present in the raw merged CSV:

- `Wheat`: `4762`
- `Fallow`: `2649`
- `Corn`: `1556`
- `Berseem`: `873`
- `Potatoes`: `459`
- `Beets`: `424`
- `Sugarcane`: `267`
- `Rice`: `156`
- `Tomatoes`: `128`
- `Beans`: `10`

This distinction matters: the raw merged CSV contains more than the five final crop labels used by the notebook model.

### Raw Source Dataset Standardization

The merge-construction notebook or script that created `combined_model_ready_scaled.csv` was not found in the current project. The current project contains the finished merged CSV plus the notebook that consumes it for training. The standardization and scaling process below is documented from the provided dataset provenance and validated against the discovered CSV schema, source counts, class counts, and value ranges.

AgrifieldNet standardization:

- `unique_field_id` was renamed to `field_id`.
- `dataset` was renamed to `source`.
- `target_class` was kept as the crop label.
- Metadata columns removed before the final model-ready table:
  - `chip_id`
  - `crop_label`
  - `pixel_count`

Morocco standardization:

- `parcel_id` was renamed to `field_id`.
- `label` was renamed to `target_class`.
- A new `source` column was added with value `morocco`.
- Raw band names were converted into Sentinel-2 zero-padded names:
  - `B1` -> `B01`
  - `B2` -> `B02`
  - `B3` -> `B03`
  - `B4` -> `B04`
  - `B5` -> `B05`
  - `B6` -> `B06`
  - `B7` -> `B07`
  - `B8` -> `B08`
  - `B8A` -> `B8A`
  - `B9` -> `B09`
  - `B11` -> `B11`
  - `B12` -> `B12`
- Metadata columns removed before the final model-ready table:
  - `irrigation`
  - `zone`

Class harmonization:

- Class labels were harmonized across both sources.
- Morocco `Bare soil` was mapped to `Fallow` to align with the shared merged dataset taxonomy.

Feature scaling:

- AgrifieldNet spectral bands were divided by `255`.
- Morocco spectral bands were divided by `10000`.
- `NDVI` was kept unchanged because it was already normalized.

Final merge:

- The standardized AgrifieldNet and Morocco tables were concatenated row-wise.
- The final discovered table has `11284` samples and `16` columns.

### Source And Class Composition

Discovered source-by-class counts:

| target_class | agrifieldnet | morocco |
|---|---:|---:|
| `Beans` | `0` | `10` |
| `Beets` | `0` | `424` |
| `Berseem` | `16` | `857` |
| `Corn` | `304` | `1252` |
| `Fallow` | `1707` | `942` |
| `Potatoes` | `43` | `416` |
| `Rice` | `131` | `25` |
| `Sugarcane` | `173` | `94` |
| `Tomatoes` | `0` | `128` |
| `Wheat` | `2148` | `2614` |

Five-label retained subset counts:

| target_class | agrifieldnet | morocco | total |
|---|---:|---:|---:|
| `Corn` | `304` | `1252` | `1556` |
| `Potatoes` | `43` | `416` | `459` |
| `Rice` | `131` | `25` | `156` |
| `Sugarcane` | `173` | `94` | `267` |
| `Wheat` | `2148` | `2614` | `4762` |

### Notebook Used

Merged training notebook:

- `notebooks/Merged_xgboost_training.ipynb`

The notebook title is `Merged AgriFieldNet + Morocco XGBoost Crop Classification Training Walkthrough`.

Notebook data path:

- `DATA_PATH = Path("combined_model_ready_scaled.csv")`

The notebook loads the prepared CSV directly with `pd.read_csv(DATA_PATH)`. It does not create the merged CSV in the current project; it consumes it.

### Training Label Filtering

The merged CSV contains ten classes, but the notebook trains the full merged crop model only on these five labels:

- `Corn`
- `Potatoes`
- `Rice`
- `Sugarcane`
- `Wheat`

Rows excluded by the notebook before training:

- `Fallow`: `2649`
- `Berseem`: `873`
- `Beets`: `424`
- `Tomatoes`: `128`
- `Beans`: `10`

Training rows after target filtering:

- Rows before cleaning: `11284`
- Excluded rows: `4084`
- Rows after cleaning: `7200`
- Retained share: `63.81%`

The notebook does not collapse excluded labels into `other_crop`. It removes them from this five-label model target.

### Feature Schema

The raw merged CSV stores scaled Sentinel-2 features as:

- `B01`
- `B02`
- `B03`
- `B04`
- `B05`
- `B06`
- `B07`
- `B08`
- `B8A`
- `B09`
- `B11`
- `B12`
- `NDVI`

The notebook then normalizes feature names into the document-aligned static mean schema:

- `B01` -> `B01_mean`
- `B02` -> `B02_mean`
- `B03` -> `B03_mean`
- `B04` -> `B04_mean`
- `B05` -> `B05_mean`
- `B06` -> `B06_mean`
- `B07` -> `B07_mean`
- `B08` -> `B08_mean`
- `B8A` -> `B8A_mean`
- `B09` -> `B09_mean`
- `B11` -> `B11_mean`
- `B12` -> `B12_mean`
- `NDVI` -> `NDVI_mean`

The full five-label model trains on all `13` mean-feature columns:

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

Metadata columns such as `field_id` are kept only for reporting and are not used as model inputs.

### Full Five-Label Model Training

Notebook preprocessing:

- Converts the `13` feature columns to numeric.
- Drops rows missing any modeling feature.
- Computes 1st and 99th percentile clipping bounds.
- Clips the feature columns using those bounds.
- Uses `LabelEncoder` for labels.
- Uses stratified `train_test_split` with `test_size=0.2` and `random_state=42`.
- Uses class-balanced sample weights.
- Trains `XGBClassifier(objective="multi:softprob", eval_metric="mlogloss")`.
- Runs 5-fold stratified cross-validation with macro F1 scoring.

Notebook holdout metrics for the full 13-feature five-label model:

- Accuracy: `0.845139`
- Macro F1: `0.753623`
- Weighted F1: `0.849403`

Notebook cross-validation:

- Folds: `5`
- Mean macro F1: `0.7696`
- Std macro F1: `0.0136`
- Min macro F1: `0.7566`
- Max macro F1: `0.7908`

Full model class order:

- `Corn`
- `Potatoes`
- `Rice`
- `Sugarcane`
- `Wheat`

Full model artifact paths saved by the notebook runtime:

- `models/xgb_merged_crop_5labels.pkl`
- `models/label_encoder_merged_crop_5labels.pkl`
- `models/feature_cols_merged_crop_5labels.pkl`
- `models/clip_lower_merged_crop_5labels.pkl`
- `models/clip_upper_merged_crop_5labels.pkl`

These are notebook output targets, not the current local state of the active `models/` tree.

Current local state:

- The full five-label artifact set is not present in the current local model folders.
- The archive inference script expects the full model at `models\Merged_Morocco_AgriNet_Model\xgb_merged_crop_5labels.pkl`.
- The archive inference output records `merged_crop_5labels_xgboost` as blocked because that artifact is missing.
- The current AOI archive also lacks `B01`, `B09`, and `B12`, so a compatible full-band AOI would still be required before this full model can produce a valid prediction.

### AOI-Compatible Reduced Five-Label Variant

The same notebook also includes a deliberately separate AOI-compatible variant because the current AOI archive exposes only:

- `B02`
- `B03`
- `B04`
- `B05`
- `B06`
- `B07`
- `B08`
- `B8A`
- `B11`

AOI-compatible feature columns:

- `B02_mean`
- `B03_mean`
- `B04_mean`
- `B05_mean`
- `B06_mean`
- `B07_mean`
- `B08_mean`
- `B8A_mean`
- `B11_mean`

The variant intentionally excludes these full-model features because the current AOI archive does not provide them:

- `B01_mean`
- `B09_mean`
- `B12_mean`

No missing-band imputation or synthetic bands are used.

AOI-compatible artifacts discovered locally:

- `models/Merged_Morocco_AgriNet_Model/xgb_merged_crop_5labels_aoi_shared_bands.pkl`
- `models/Merged_Morocco_AgriNet_Model/label_encoder_merged_crop_5labels_aoi_shared_bands.pkl`
- `models/Merged_Morocco_AgriNet_Model/feature_cols_merged_crop_5labels_aoi_shared_bands.pkl`
- `models/Merged_Morocco_AgriNet_Model/clip_lower_merged_crop_5labels_aoi_shared_bands.pkl`
- `models/Merged_Morocco_AgriNet_Model/clip_upper_merged_crop_5labels_aoi_shared_bands.pkl`

Local artifact contents:

- Classes: `Corn`, `Potatoes`, `Rice`, `Sugarcane`, `Wheat`
- Feature count: `9`
- Clip-bound columns match the 9 AOI-compatible feature columns.

AOI-compatible notebook holdout metrics:

- Accuracy: `0.8354166666666667`
- Macro F1: `0.7305025296798493`
- Weighted F1: `0.8409700758719112`

### Inference Result

Source files:

- `data/research/merged_crop_classification/outputs/inference_test_results.json`
- `data/research/merged_crop_classification/outputs/inference_test_results.csv`
- `data/research/merged_crop_classification/outputs/aoi_shared_5label_diagnostics.json`
- `data/research/merged_crop_classification/outputs/aoi_shared_5label_feature_diagnostics.csv`

Full merged five-label model:

- `model_name`: `merged_crop_5labels_xgboost`
- `status`: `blocked`
- Blocked reason: `Missing model artifact: models\Merged_Morocco_AgriNet_Model\xgb_merged_crop_5labels.pkl`
- It is also not compatible with the current AOI archive unless the AOI provides `B01`, `B09`, and `B12`.

AOI-compatible merged five-label model:

- `model_name`: `merged_crop_5labels_aoi_shared_bands_xgboost`
- `status`: `ok`
- Known actual label: `Corn`
- Predicted label: `Wheat`
- `is_correct`: `False`
- `proba_corn`: `0.014917795546352863`
- `proba_potatoes`: `0.0002640655147843063`
- `proba_rice`: `0.00008443059050478041`
- `proba_sugarcane`: `0.00020094447245355695`
- `proba_wheat`: `0.9845327734947205`

Diagnostics confirm:

- The `Wheat` prediction is not a label-mapping bug.
- Feature order matches the artifact contract.
- Six of nine AOI features clipped high.
- The AOI-compatible model excludes `NDVI_mean`, even though the AOI has `B08` and `B04` from which NDVI can be computed.
- Corn-to-Wheat confusion appears in notebook holdout behavior: `35 / 311` Corn holdout samples were predicted as Wheat.

### Why This Path Is Research-Only For Now

The merged AgrifieldNet + Morocco workflow is documented as a research attempt, not the selected current demo path.

It is not selected because:

- The full 13-feature merged model artifacts are missing locally in the current setup.
- The current AOI archive lacks `B01`, `B09`, and `B12`, which the full model requires.
- The AOI-compatible reduced model ran technically but failed the known Corn AOI validation by predicting `Wheat`.

The currently selected demo model remains `morocco_only_xgboost` because it predicted the known Corn AOI correctly. The merged five-label path should only move forward after full artifacts and compatible AOI inputs are restored, or after a new validated AOI-compatible model is tested across more known-label AOIs.

## Discovered Model Artifacts

### Morocco-Only XGBoost Artifact Set

Folder: `models/Moroco_only_Model`

Discovered files:

- `xgb_tuned_v2_indices_weighted.pkl`
- `label_encoder_v2.pkl`
- `feature_cols_v2.pkl`
- `clip_lower_common.pkl`
- `clip_upper_common.pkl`

Loaded artifact contents:

- Model type: `XGBClassifier`
- Label encoder classes: `corn`, `other_crop`, `soil`, `wheat`
- Model classes: `0`, `1`, `2`, `3`
- Clip-bound columns: `B2`, `B3`, `B4`, `B5`, `B6`, `B7`, `B8`, `B8A`, `B11`, `NDVI`
- Model feature order:
  - `B2`
  - `B3`
  - `B4`
  - `B5`
  - `B6`
  - `B7`
  - `B8`
  - `B8A`
  - `B11`
  - `NDVI`
  - `NDWI`
  - `NDBI`
  - `SAVI`
  - `BSI`
  - `B11_B8_ratio`
  - `B4_B8_ratio`
  - `B8_B4_diff`

Related script:

- `scripts/research/infer_morocco_xgboost_demo.py`

Also used by archive inference script as `morocco_only_xgboost`.

### Full Merged Five-Label XGBoost Model

Referenced model name in outputs:

- `merged_crop_5labels_xgboost`

Referenced model path in outputs:

- `models\Merged_Morocco_AgriNet_Model\xgb_merged_crop_5labels.pkl`

Current local state:

- The referenced full merged model artifact is not present locally.
- Current output status is `blocked`.
- Current blocked reason is: `Missing model artifact: models\Merged_Morocco_AgriNet_Model\xgb_merged_crop_5labels.pkl`

Expected full-band feature schema from the merged notebook:

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

Important input-schema note:

- The current AOI archive lacks `B01`, `B09`, and `B12`.
- Therefore, even if the original full model artifact is restored, this AOI still does not satisfy the full-band feature contract unless a full-band AOI input is provided.
- No missing features should be imputed.

Related script:

- `scripts/research/infer_merged_crop_archive_test.py`

### AOI-Compatible Merged Five-Label XGBoost Artifact Set

Folder: `models/Merged_Morocco_AgriNet_Model`

Discovered files:

- `xgb_merged_crop_5labels_aoi_shared_bands.pkl`
- `label_encoder_merged_crop_5labels_aoi_shared_bands.pkl`
- `feature_cols_merged_crop_5labels_aoi_shared_bands.pkl`
- `clip_lower_merged_crop_5labels_aoi_shared_bands.pkl`
- `clip_upper_merged_crop_5labels_aoi_shared_bands.pkl`

Loaded artifact contents:

- Model type: `XGBClassifier`
- Model classes: `0`, `1`, `2`, `3`, `4`
- Label encoder classes: `Corn`, `Potatoes`, `Rice`, `Sugarcane`, `Wheat`
- Feature count: `9`
- Model feature order:
  - `B02_mean`
  - `B03_mean`
  - `B04_mean`
  - `B05_mean`
  - `B06_mean`
  - `B07_mean`
  - `B08_mean`
  - `B8A_mean`
  - `B11_mean`

Related scripts:

- `scripts/research/infer_merged_crop_archive_test.py`
- `scripts/research/diagnose_aoi_shared_5label.py`

Related notebook discovered:

- `notebooks/Merged_xgboost_training.ipynb`

## Generated Outputs

Inference outputs:

- `data/research/merged_crop_classification/outputs/inference_test_results.json`
- `data/research/merged_crop_classification/outputs/inference_test_results.csv`
- `data/research/morocco_crop_demo/prediction.csv`

Diagnostics outputs:

- `data/research/merged_crop_classification/outputs/aoi_shared_5label_diagnostics.json`
- `data/research/merged_crop_classification/outputs/aoi_shared_5label_feature_diagnostics.csv`

These files are research outputs under ignored local data paths and should not be promoted into canonical FarmTrust assessment output.

## Inference Results

Source of truth: `data/research/merged_crop_classification/outputs/inference_test_results.csv`.

| model_name | status | predicted_label | known_actual_label | is_correct | interpretation |
|---|---|---|---|---:|---|
| `morocco_only_xgboost` | `ok` | `corn` | `Corn` | `True` | Passed current AOI validation. |
| `merged_crop_5labels_xgboost` | `blocked` |  | `Corn` |  | Blocked by missing full model artifact in current local state. |
| `merged_crop_5labels_aoi_shared_bands_xgboost` | `ok` | `Wheat` | `Corn` | `False` | Ran technically, but failed validation. |

## Morocco-Only Model Result

Model name in outputs:

- `morocco_only_xgboost`

Model artifact:

- `models\Moroco_only_Model\xgb_tuned_v2_indices_weighted.pkl`

Preprocessing used:

- Mean aggregate raw AOI Zarr bands.
- Compute `NDVI`.
- Clip common raw features.
- Compute notebook engineered indices.
- Reorder by `feature_cols_v2.pkl`.

Prediction:

- `predicted_label`: `corn`
- `known_actual_label`: `Corn`
- `is_correct`: `True`
- `proba_corn`: `0.42813432216644287`
- `proba_other_crop`: `0.07592978328466415`
- `proba_soil`: `0.20565509796142578`
- `proba_wheat`: `0.290280818939209`

Separate one-row output at `data/research/morocco_crop_demo/prediction.csv` records:

- `pred_class`: `corn`
- `confidence`: `0.42813432216644287`
- `confidence_status`: `low`

Interpretation:

- The Morocco-only model is the only model that currently passed this known Corn AOI test.
- It is selected for current research/demo validation purposes only.
- The confidence is low, so this should not be overstated as production-ready crop classification.

## Full Merged Five-Label Model Result

Model name in outputs:

- `merged_crop_5labels_xgboost`

Referenced artifact path:

- `models\Merged_Morocco_AgriNet_Model\xgb_merged_crop_5labels.pkl`

Current status:

- `blocked`

Blocked reason from output:

- `Missing model artifact: models\Merged_Morocco_AgriNet_Model\xgb_merged_crop_5labels.pkl`

Interpretation:

- The full merged five-label model did not run to prediction in the current local state.
- This is not a failed crop prediction; it is a blocked inference.
- The current AOI also lacks the full-band inputs `B01`, `B09`, and `B12`, so no missing-band imputation should be used to force this model.

## AOI-Compatible Merged Five-Label Model Result

Model name in outputs:

- `merged_crop_5labels_aoi_shared_bands_xgboost`

Model artifact:

- `models\Merged_Morocco_AgriNet_Model\xgb_merged_crop_5labels_aoi_shared_bands.pkl`

Preprocessing used:

- Mean aggregate AOI Zarr bands into shared `B*_mean` features.
- Scale raw digital numbers to reflectance-like values with `10000.0` when required by clip bounds.
- Clip shared feature columns.
- Reorder by `feature_cols_merged_crop_5labels_aoi_shared_bands.pkl`.

Prediction:

- `predicted_label`: `Wheat`
- `known_actual_label`: `Corn`
- `is_correct`: `False`
- `proba_corn`: `0.014917795546352863`
- `proba_potatoes`: `0.0002640655147843063`
- `proba_rice`: `0.00008443059050478041`
- `proba_sugarcane`: `0.00020094447245355695`
- `proba_wheat`: `0.9845327734947205`

Interpretation:

- This model ran technically, but failed validation.
- It must not be selected for integration or product use.
- The failure should be treated as a model validation failure, not an execution failure.

## AOI-Compatible Diagnostics

Source of truth:

- `data/research/merged_crop_classification/outputs/aoi_shared_5label_diagnostics.json`
- `data/research/merged_crop_classification/outputs/aoi_shared_5label_feature_diagnostics.csv`

### Label Mapping

Diagnostics confirm the `Wheat` prediction is real and not a class-order bug.

- Model classes: `0`, `1`, `2`, `3`, `4`
- Label encoder classes: `Corn`, `Potatoes`, `Rice`, `Sugarcane`, `Wheat`
- Probability order: `Corn`, `Potatoes`, `Rice`, `Sugarcane`, `Wheat`
- Predicted numeric class: `4`
- Decoded predicted label: `Wheat`
- Label mapping bug detected: `false`

### Feature Order

- Artifact feature columns match the inference dataframe columns.
- Model expected feature count: `9`
- Actual inference feature count: `9`
- Feature order check passed.

### Scaling And Clipping

- Reflectance scale applied: `10000.0`
- Six of nine AOI-shared features clipped high:
  - `B02_mean`
  - `B03_mean`
  - `B06_mean`
  - `B07_mean`
  - `B08_mean`
  - `B8A_mean`
- This places much of the AOI row at the high edge of the training distribution.
- This is an out-of-distribution warning for the reduced shared-band model.

### NDVI

- `NDVI_mean` was not included in the AOI-shared feature columns.
- The AOI archive has `B08` and `B04`, so NDVI can be computed.
- Computed AOI NDVI from diagnostics: `0.36575296821668`
- The Morocco-only model, which passed this AOI test, uses `NDVI` plus additional engineered indices.

### Holdout Behavior From Notebook

AOI-compatible model notebook metrics:

- Accuracy: `0.8354166666666667`
- Macro F1: `0.7305025296798493`
- Weighted F1: `0.8409700758719112`
- Corn precision: `0.766764`
- Corn recall: `0.845659`
- Corn support: `311`
- Wheat precision: `0.927024`
- Wheat recall: `0.853992`
- Wheat support: `952`
- Corn predicted as Wheat: `35 / 311`, about `11.25%`

Diagnostic conclusion:

- The AOI-compatible five-label model is not ready.
- The likely issue is not class mapping or feature order.
- The likely issue is the combination of reduced features, missing NDVI/indices, and this AOI sitting high against the clipped training distribution.

## Final Decision

Current selected model for AOI/demo validation:

- `morocco_only_xgboost`

Reason:

- It ran successfully.
- The known actual crop is `Corn`.
- It predicted `corn`.
- `is_correct=True`.

Models not selected:

- `merged_crop_5labels_xgboost`: blocked because the referenced full model artifact is missing locally; the current AOI also lacks the full-band inputs needed for that model.
- `merged_crop_5labels_aoi_shared_bands_xgboost`: ran technically, but failed validation by predicting `Wheat` for a known Corn AOI.

Guardrails:

- No missing bands were imputed.
- No training or retraining was run during inference validation.
- No production scoring was changed.
- No canonical FarmTrust assessment output was changed.
- The AOI-compatible five-label model must not be presented as ready.

Conclusion:

- The only current validated AOI/demo model is `morocco_only_xgboost`.
- The merged five-label path is research-only and not selected for current integration.

## Files Changed Or Generated

Research scripts discovered:

- `scripts/research/infer_morocco_xgboost_demo.py`
- `scripts/research/infer_merged_crop_archive_test.py`
- `scripts/research/diagnose_aoi_shared_5label.py`

Documentation files discovered/updated for this work:

- `docs/TASKS/T-07-morocco-crop-xgb-demo-inference.md`
- `docs/PLANS/P-07-crop-model-inference-results.md`
- `docs/PLANS/P-merged-crop-xgboost-baseline.md`

Generated inference outputs:

- `data/research/merged_crop_classification/outputs/inference_test_results.json`
- `data/research/merged_crop_classification/outputs/inference_test_results.csv`
- `data/research/morocco_crop_demo/prediction.csv`

Generated diagnostics outputs:

- `data/research/merged_crop_classification/outputs/aoi_shared_5label_diagnostics.json`
- `data/research/merged_crop_classification/outputs/aoi_shared_5label_feature_diagnostics.csv`

Local model/data artifacts should remain local and should not be committed:

- `models/`
- `data/research/`
- `data/aoi_demo_01/`

## Commands Verified

Compile checks:

```powershell
.venv\Scripts\python.exe -m py_compile scripts\research\infer_merged_crop_archive_test.py
```

```powershell
.venv\Scripts\python.exe -m py_compile scripts\research\diagnose_aoi_shared_5label.py scripts\research\infer_merged_crop_archive_test.py
```

Help checks:

```powershell
.venv\Scripts\python.exe scripts\research\infer_merged_crop_archive_test.py --help
```

```powershell
.venv\Scripts\python.exe scripts\research\diagnose_aoi_shared_5label.py --help
```

Inference command:

```powershell
.venv\Scripts\python.exe scripts\research\infer_merged_crop_archive_test.py `
  --archive-path "D:\My_Downloads\aoi_demo_01 (1).rar"
```

Diagnostics command:

```powershell
.venv\Scripts\python.exe scripts\research\diagnose_aoi_shared_5label.py `
  --archive-path "D:\My_Downloads\aoi_demo_01 (1).rar"
```

## Next Validation Path

For the current AOI/demo:

- Keep using `morocco_only_xgboost` as the current research-validated demo model.
- Keep its low confidence visible.
- Do not promote crop classification into canonical FarmTrust assessment output.

For the full merged five-label model:

- Restore the original full model artifact if it should remain part of the comparison.
- Test only with an AOI archive that includes the full required Sentinel-2 band set: `B01`, `B02`, `B03`, `B04`, `B05`, `B06`, `B07`, `B08`, `B8A`, `B09`, `B11`, `B12`, and `NDVI`.

For the AOI-compatible five-label model:

- Treat the current model as failed validation.
- Validate against more AOIs with known labels.
- Train and compare a safer AOI-compatible variant that uses shared bands plus computed `NDVI_mean`.
- Consider additional indices computable from available bands.
- Do not use this model in any product workflow until the Corn/Wheat failure is resolved.
