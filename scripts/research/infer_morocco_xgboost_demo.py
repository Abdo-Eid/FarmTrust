"""Research-only Morocco XGBoost inference for AOI demo data.

This script uses the notebook-exported XGBoost crop-classification artifacts.
It is not part of FarmTrust canonical land assessment output.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd


MODEL_FILENAME = "xgb_tuned_v2_indices_weighted.pkl"
LABEL_ENCODER_FILENAME = "label_encoder_v2.pkl"
FEATURE_COLUMNS_FILENAME = "feature_cols_v2.pkl"
CLIP_LOWER_FILENAME = "clip_lower_common.pkl"
CLIP_UPPER_FILENAME = "clip_upper_common.pkl"

REQUIRED_BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11"]
COMMON_CLIP_COLUMNS = [*REQUIRED_BANDS, "NDVI"]
EXPECTED_PROBABILITY_LABELS = ["corn", "other_crop", "soil", "wheat"]
ZARR_GROUPS = [None, "20m"]

BAND_ALIASES = {
    "B02": "B2",
    "B03": "B3",
    "B04": "B4",
    "B05": "B5",
    "B06": "B6",
    "B07": "B7",
    "B08": "B8",
    "B8A": "B8A",
    "B11": "B11",
}


class InferenceError(ValueError):
    """User-facing validation or inference setup error."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run research-only Morocco XGBoost crop inference on one AOI demo."
    )
    parser.add_argument("--demo-path", required=True, type=Path, help="CSV file, cube.zarr path, or AOI directory.")
    parser.add_argument("--model-dir", required=True, type=Path, help="Directory containing notebook model artifacts.")
    parser.add_argument("--output-csv", required=True, type=Path, help="Path to write the one-row prediction CSV.")
    return parser


def load_pickle(path: Path) -> Any:
    if not path.exists():
        raise InferenceError(f"Missing required model artifact: {path}")

    try:
        import joblib
    except ImportError as exc:
        raise InferenceError("joblib is required to load model artifacts.") from exc

    try:
        return joblib.load(path)
    except Exception as exc:
        raise InferenceError(f"Failed to load artifact {path}: {exc}") from exc


def load_artifacts(model_dir: Path) -> tuple[Any, Any, list[str], Any, Any]:
    if not model_dir.exists():
        raise InferenceError(f"Model directory does not exist: {model_dir}")
    if not model_dir.is_dir():
        raise InferenceError(f"Model path must be a directory: {model_dir}")

    model = load_pickle(model_dir / MODEL_FILENAME)
    label_encoder = load_pickle(model_dir / LABEL_ENCODER_FILENAME)
    feature_columns = normalize_feature_columns(load_pickle(model_dir / FEATURE_COLUMNS_FILENAME))
    clip_lower = load_pickle(model_dir / CLIP_LOWER_FILENAME)
    clip_upper = load_pickle(model_dir / CLIP_UPPER_FILENAME)
    return model, label_encoder, feature_columns, clip_lower, clip_upper


def normalize_feature_columns(value: Any) -> list[str]:
    if isinstance(value, pd.Index):
        columns = value.tolist()
    elif isinstance(value, pd.Series):
        columns = value.tolist()
    elif isinstance(value, np.ndarray):
        columns = value.tolist()
    elif isinstance(value, (list, tuple)):
        columns = list(value)
    else:
        raise InferenceError("feature_cols_v2.pkl must contain a list-like object of feature names.")

    normalized = [str(column) for column in columns]
    if not normalized:
        raise InferenceError("feature_cols_v2.pkl contains no feature columns.")
    return normalized


def load_demo_band_row(demo_path: Path) -> pd.DataFrame:
    if not demo_path.exists():
        raise InferenceError(f"Demo path does not exist: {demo_path}")

    if demo_path.is_file() and demo_path.suffix.lower() == ".csv":
        return load_csv_band_row(demo_path)

    zarr_path = resolve_zarr_path(demo_path)
    if zarr_path is not None:
        return load_zarr_band_row(zarr_path)

    if demo_path.is_file():
        raise InferenceError(f"Unsupported demo file format: {demo_path}. Expected .csv or .zarr directory.")
    raise InferenceError(
        f"Unsupported demo directory: {demo_path}. Expected a .zarr store or a directory containing cube.zarr."
    )


def load_csv_band_row(csv_path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        raise InferenceError(f"Failed to read demo CSV {csv_path}: {exc}") from exc

    if df.empty:
        raise InferenceError(f"Demo CSV has no rows: {csv_path}")

    df = apply_band_aliases(df)
    validate_required_bands(list(df.columns), context=str(csv_path))

    band_values = df.loc[:, REQUIRED_BANDS].apply(pd.to_numeric, errors="coerce")
    row = band_values.mean(axis=0, skipna=True).to_frame().T
    validate_finite_frame(row, "aggregated CSV band row")
    return row


def resolve_zarr_path(demo_path: Path) -> Path | None:
    if is_zarr_store(demo_path):
        return demo_path

    if demo_path.is_dir():
        cube_path = demo_path / "cube.zarr"
        if is_zarr_store(cube_path):
            return cube_path

    return None


def is_zarr_store(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return (
        path.suffix.lower() == ".zarr"
        or (path / "zarr.json").exists()
        or (path / ".zgroup").exists()
        or (path / ".zmetadata").exists()
    )


def load_zarr_band_row(zarr_path: Path) -> pd.DataFrame:
    try:
        import xarray as xr
    except ImportError as exc:
        raise InferenceError("xarray is required to read Zarr demo data.") from exc

    datasets = []
    open_errors: list[str] = []
    for group in ZARR_GROUPS:
        try:
            datasets.append(xr.open_zarr(zarr_path, group=group, consolidated=False))
        except Exception as exc:
            group_name = "<root>" if group is None else group
            open_errors.append(f"{group_name}: {exc}")

    if not datasets:
        raise InferenceError(f"Failed to open Zarr store {zarr_path}. Errors: {open_errors}")

    values: dict[str, float] = {}
    available: list[str] = []
    try:
        for band in REQUIRED_BANDS:
            data_array = find_band_dataarray(datasets, band)
            if data_array is None:
                continue
            values[band] = mean_dataarray(data_array, band)

        for dataset in datasets:
            available.extend(str(name) for name in dataset.data_vars)
    finally:
        for dataset in datasets:
            dataset.close()

    missing = [band for band in REQUIRED_BANDS if band not in values]
    if missing:
        raise InferenceError(
            f"Missing required bands in Zarr cube {zarr_path}: {missing}. "
            f"Available Zarr variables: {sorted(set(available))}"
        )

    row = pd.DataFrame([values]).loc[:, REQUIRED_BANDS].apply(pd.to_numeric, errors="coerce")
    validate_finite_frame(row, "aggregated Zarr band row")
    return row


def find_band_dataarray(datasets: list[Any], canonical_band: str) -> Any | None:
    candidate_names = [canonical_band]
    candidate_names.extend(alias for alias, canonical in BAND_ALIASES.items() if canonical == canonical_band)

    for dataset in datasets:
        for name in candidate_names:
            if name in dataset.data_vars:
                return dataset[name]
    return None


def mean_dataarray(data_array: Any, band: str) -> float:
    value = float(np.nanmean(np.asarray(data_array.values, dtype=np.float64)))
    if not np.isfinite(value):
        raise InferenceError(f"Band {band} has no finite values after mean aggregation.")
    return value


def apply_band_aliases(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for alias, canonical in BAND_ALIASES.items():
        if alias in normalized.columns and canonical not in normalized.columns:
            normalized[canonical] = normalized[alias]
    return normalized


def validate_required_bands(columns: Sequence[str], *, context: str) -> None:
    missing = [band for band in REQUIRED_BANDS if band not in columns]
    if missing:
        raise InferenceError(
            f"Missing required bands in {context}: {missing}. Available columns/bands: {list(columns)}"
        )


def prepare_model_features(
    raw_band_row: pd.DataFrame,
    clip_lower: Any,
    clip_upper: Any,
    feature_columns: list[str],
) -> pd.DataFrame:
    features = raw_band_row.loc[:, REQUIRED_BANDS].copy()

    features["NDVI"] = (features["B8"] - features["B4"]) / (features["B8"] + features["B4"] + 1e-6)

    lower = coerce_clip_bounds(clip_lower, COMMON_CLIP_COLUMNS, "clip_lower_common.pkl")
    upper = coerce_clip_bounds(clip_upper, COMMON_CLIP_COLUMNS, "clip_upper_common.pkl")
    features.loc[:, COMMON_CLIP_COLUMNS] = features.loc[:, COMMON_CLIP_COLUMNS].clip(
        lower=lower,
        upper=upper,
        axis=1,
    )

    features["NDWI"] = (features["B3"] - features["B8"]) / (features["B3"] + features["B8"] + 1e-6)
    features["NDBI"] = (features["B11"] - features["B8"]) / (features["B11"] + features["B8"] + 1e-6)
    features["SAVI"] = 1.5 * (features["B8"] - features["B4"]) / (features["B8"] + features["B4"] + 0.5 + 1e-6)
    features["BSI"] = ((features["B11"] + features["B4"]) - (features["B8"] + features["B2"])) / (
        (features["B11"] + features["B4"]) + (features["B8"] + features["B2"]) + 1e-6
    )
    features["B11_B8_ratio"] = features["B11"] / (features["B8"] + 1e-6)
    features["B4_B8_ratio"] = features["B4"] / (features["B8"] + 1e-6)
    features["B8_B4_diff"] = features["B8"] - features["B4"]

    missing_features = [column for column in feature_columns if column not in features.columns]
    if missing_features:
        raise InferenceError(
            f"Prepared feature row is missing columns required by feature_cols_v2.pkl: {missing_features}. "
            f"Prepared columns: {list(features.columns)}"
        )

    model_features = features.loc[:, feature_columns].apply(pd.to_numeric, errors="coerce")
    validate_finite_frame(model_features, "model feature row")
    return model_features


def coerce_clip_bounds(bounds: Any, columns: list[str], artifact_name: str) -> pd.Series:
    if isinstance(bounds, pd.Series):
        series = bounds
    elif isinstance(bounds, dict):
        series = pd.Series(bounds)
    elif isinstance(bounds, pd.DataFrame):
        if len(bounds) == 1 and set(columns).issubset(bounds.columns):
            series = bounds.iloc[0]
        elif bounds.shape[1] == 1 and set(columns).issubset(bounds.index):
            series = bounds.iloc[:, 0]
        else:
            raise InferenceError(f"{artifact_name} DataFrame must contain bounds for columns {columns}.")
    else:
        array = np.asarray(bounds, dtype=np.float64)
        if array.ndim == 0:
            series = pd.Series(float(array), index=columns)
        elif array.ndim == 1 and len(array) == len(columns):
            series = pd.Series(array, index=columns)
        else:
            raise InferenceError(
                f"{artifact_name} must be a Series, dict, scalar, or 1D array with {len(columns)} values."
            )

    missing = [column for column in columns if column not in series.index]
    if missing:
        raise InferenceError(f"{artifact_name} is missing clipping bounds for columns: {missing}")

    coerced = pd.to_numeric(series.loc[columns], errors="coerce")
    if coerced.isna().any():
        invalid = coerced[coerced.isna()].index.tolist()
        raise InferenceError(f"{artifact_name} has non-numeric clipping bounds for columns: {invalid}")
    return coerced.astype(float)


def validate_finite_frame(df: pd.DataFrame, label: str) -> None:
    invalid_columns = [
        column
        for column in df.columns
        if not np.isfinite(pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=np.float64)).all()
    ]
    if invalid_columns:
        raise InferenceError(f"{label} contains NaN or infinite values in columns: {invalid_columns}")


def predict(model: Any, label_encoder: Any, model_features: pd.DataFrame) -> pd.DataFrame:
    if not hasattr(model, "predict_proba"):
        raise InferenceError("Loaded model does not expose predict_proba().")

    try:
        probabilities = np.asarray(model.predict_proba(model_features), dtype=np.float64)
        raw_prediction = np.asarray(model.predict(model_features))
    except Exception as exc:
        raise InferenceError(f"Model prediction failed: {exc}") from exc

    if probabilities.ndim != 2 or probabilities.shape[0] != 1:
        raise InferenceError(f"Expected predict_proba shape [1, n_classes], got {list(probabilities.shape)}")

    pred_class = decode_predictions(label_encoder, raw_prediction)[0]
    probability_labels = probability_class_labels(model, label_encoder, probabilities.shape[1])
    probability_map = {
        normalize_label(label): float(probabilities[0, index])
        for index, label in enumerate(probability_labels)
    }

    missing_labels = [label for label in EXPECTED_PROBABILITY_LABELS if label not in probability_map]
    if missing_labels:
        raise InferenceError(
            f"Model/label encoder is missing expected probability labels: {missing_labels}. "
            f"Available labels: {list(probability_map)}"
        )

    confidence = max(probability_map[label] for label in EXPECTED_PROBABILITY_LABELS)
    return pd.DataFrame(
        [
            {
                "pred_class": str(pred_class),
                "proba_corn": probability_map["corn"],
                "proba_other_crop": probability_map["other_crop"],
                "proba_soil": probability_map["soil"],
                "proba_wheat": probability_map["wheat"],
                "confidence": confidence,
                "confidence_status": confidence_status(confidence),
            }
        ]
    )


def decode_predictions(label_encoder: Any, raw_prediction: np.ndarray) -> list[str]:
    if hasattr(label_encoder, "inverse_transform"):
        try:
            decoded = label_encoder.inverse_transform(raw_prediction.astype(int))
            return [str(value) for value in decoded]
        except Exception:
            pass
    return [str(value) for value in raw_prediction]


def probability_class_labels(model: Any, label_encoder: Any, n_classes: int) -> list[str]:
    model_classes = getattr(model, "classes_", None)
    if model_classes is not None:
        model_classes_array = np.asarray(model_classes)
        if hasattr(label_encoder, "inverse_transform"):
            try:
                decoded = label_encoder.inverse_transform(model_classes_array.astype(int))
                return [str(value) for value in decoded]
            except Exception:
                pass
        return [str(value) for value in model_classes_array]

    encoder_classes = getattr(label_encoder, "classes_", None)
    if encoder_classes is not None and len(encoder_classes) == n_classes:
        return [str(value) for value in encoder_classes]

    raise InferenceError("Could not determine class labels for predict_proba columns.")


def normalize_label(label: Any) -> str:
    return str(label).strip().lower().replace(" ", "_").replace("-", "_")


def confidence_status(confidence: float) -> str:
    if confidence >= 0.60:
        return "high"
    if confidence >= 0.45:
        return "medium"
    return "low"


def write_output(predictions: pd.DataFrame, output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_csv, index=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        model, label_encoder, feature_columns, clip_lower, clip_upper = load_artifacts(args.model_dir)
        raw_band_row = load_demo_band_row(args.demo_path)
        model_features = prepare_model_features(raw_band_row, clip_lower, clip_upper, feature_columns)
        predictions = predict(model, label_encoder, model_features)
        write_output(predictions, args.output_csv)
    except InferenceError as exc:
        parser.exit(2, f"Error: {exc}\n")

    print(f"Wrote prediction CSV to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
