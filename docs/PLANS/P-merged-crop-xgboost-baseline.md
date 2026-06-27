# P-merged-crop-xgboost-baseline

## Purpose

Create a reusable, research-only XGBoost baseline for crop classification once the merged field/parcel-season dataset is available.

This is not production inference and is not part of the current FarmTrust land assessment contract.

## Expected Input Schema

The merged dataset may be CSV or Excel (`.csv`, `.xlsx`, `.xls`). It must contain one row per field or parcel-season, with columns in this exact order:

```text
source_dataset
field_id
label
B01_mean
B02_mean
B03_mean
B04_mean
B05_mean
B06_mean
B07_mean
B08_mean
B8A_mean
B09_mean
B11_mean
B12_mean
NDVI_mean
observation_count
zone
irrigation
```

Allowed labels: `Corn`, `Potatoes`, `Rice`, `Sugarcane`, `Wheat`.

Allowed source datasets: `agrifieldnet`, `morocco`.

The baseline model currently trains only on `Corn`, `Potatoes`, `Rice`, `Sugarcane`, and `Wheat`. Unsupported labels in the input dataset are filtered by default and reported during dry-run/training setup; use `--strict-labels` to fail instead.

## Accepted Input Schemas

The training script accepts two research input shapes:

- Canonical research schema: `source_dataset`, `field_id`, `label`, `B01_mean` through `B12_mean`, `NDVI_mean`, `observation_count`, `zone`, `irrigation`.
- Current model-ready alias schema: `field_id`, `source`, `target_class`, `B01`, `B02`, `B03`, `B04`, `B05`, `B06`, `B07`, `B08`, `B8A`, `B09`, `B11`, `B12`, `NDVI`.

Alias inputs are normalized internally before validation, training, splitting, and evaluation. Downstream code still sees only the canonical schema.

## Class Imbalance

The crop classes are imbalanced, so the default training run uses per-row `sample_weight` from `sklearn.utils.class_weight.compute_sample_weight(class_weight="balanced", ...)` on the encoded training labels.

`scale_pos_weight` is not used because this is a multi-class XGBoost classifier (`objective="multi:softprob"`), not a binary classifier.

## Feature Columns

The model trains only on static Sentinel-2 mean features:

```text
B01_mean
B02_mean
B03_mean
B04_mean
B05_mean
B06_mean
B07_mean
B08_mean
B8A_mean
B09_mean
B11_mean
B12_mean
NDVI_mean
```

## Target Column

- `label`

## Excluded Metadata Columns

These columns are retained for evaluation and traceability, but never used as model inputs:

```text
source_dataset
field_id
observation_count
zone
irrigation
```

## Run Commands

Install the research ML extra:

```bash
uv sync --extra ml
```

Check the CLI:

```bash
uv run python -m scripts.research.crop_classification.train_xgboost_crop_model --help
```

Validate and summarize the merged dataset without writing artifacts:

```bash
python -m scripts.research.crop_classification.train_xgboost_crop_model --dry-run
```

Validate a specific Excel file:

```bash
python -m scripts.research.crop_classification.train_xgboost_crop_model \
  --merged-data data/combined_model_ready_scaled.xlsx \
  --dry-run
```

Train the baseline:

```bash
uv run python -m scripts.research.crop_classification.train_xgboost_crop_model \
  --merged-data data/combined_model_ready_scaled.xlsx \
  --output-dir data/research/merged_crop_classification/outputs/xgboost_baseline \
  --test-size 0.2 \
  --random-state 42
```

Train with the default balanced sample weights:

```bash
python -m scripts.research.crop_classification.train_xgboost_crop_model --merged-data data/combined_model_ready_scaled.csv
```

Train without class balancing:

```bash
python -m scripts.research.crop_classification.train_xgboost_crop_model --merged-data data/combined_model_ready_scaled.csv --class-weight none
```

## Output Artifacts

The training run writes:

- `model.joblib`
- `label_encoder.joblib`
- `feature_columns.json`
- `training_config.json`
- `metrics.json`
- `classification_report.csv`
- `confusion_matrix.csv`
- `per_source_metrics.csv`
- `predictions.csv`
- `feature_importance.csv`

## Notes

- The merged dataset is local and research-only. Do not commit merged CSV/Excel files, generated models, pickles, or training outputs.
- Production inference must aggregate Sentinel-2 observations into one field-season row with the agreed feature schema before prediction.
- This baseline intentionally excludes metadata from model features to reduce leakage from dataset source, geography, irrigation context, or sample identity.
