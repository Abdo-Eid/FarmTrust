"""Research-only archive inference test for local crop XGBoost artifacts.

The archive is inference input only. Training is external and is not reproduced
in this project.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd


EPS = 1e-6

MOROCCO_ARTIFACTS = {
    "model": "xgb_tuned_v2_indices_weighted.pkl",
    "label_encoder": "label_encoder_v2.pkl",
    "feature_columns": "feature_cols_v2.pkl",
    "clip_lower": "clip_lower_common.pkl",
    "clip_upper": "clip_upper_common.pkl",
}
MERGED_ARTIFACTS = {
    "model": "xgb_merged_crop_5labels.pkl",
    "label_encoder": "label_encoder_merged_crop_5labels.pkl",
    "feature_columns": "feature_cols_merged_crop_5labels.pkl",
    "clip_lower": "clip_lower_merged_crop_5labels.pkl",
    "clip_upper": "clip_upper_merged_crop_5labels.pkl",
}
AOI_SHARED_ARTIFACTS = {
    "model": "xgb_merged_crop_5labels_aoi_shared_bands.pkl",
    "label_encoder": "label_encoder_merged_crop_5labels_aoi_shared_bands.pkl",
    "feature_columns": "feature_cols_merged_crop_5labels_aoi_shared_bands.pkl",
    "clip_lower": "clip_lower_merged_crop_5labels_aoi_shared_bands.pkl",
    "clip_upper": "clip_upper_merged_crop_5labels_aoi_shared_bands.pkl",
}

MOROCCO_BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11"]
MOROCCO_COMMON_CLIP_COLUMNS = [*MOROCCO_BANDS, "NDVI"]
MOROCCO_BAND_ALIASES = {
    "B2": ["B2", "B02"],
    "B3": ["B3", "B03"],
    "B4": ["B4", "B04"],
    "B5": ["B5", "B05"],
    "B6": ["B6", "B06"],
    "B7": ["B7", "B07"],
    "B8": ["B8", "B08"],
    "B8A": ["B8A"],
    "B11": ["B11"],
}

MERGED_BANDS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"]
MERGED_FEATURE_COLUMNS = [f"{band}_mean" for band in MERGED_BANDS] + ["NDVI_mean"]
AOI_SHARED_BANDS = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11"]
AOI_SHARED_FEATURE_COLUMNS = [f"{band}_mean" for band in AOI_SHARED_BANDS]
MERGED_BAND_ALIASES = {
    "B01": ["B01", "B1"],
    "B02": ["B02", "B2"],
    "B03": ["B03", "B3"],
    "B04": ["B04", "B4"],
    "B05": ["B05", "B5"],
    "B06": ["B06", "B6"],
    "B07": ["B07", "B7"],
    "B08": ["B08", "B8"],
    "B8A": ["B8A"],
    "B09": ["B09", "B9"],
    "B11": ["B11"],
    "B12": ["B12"],
}


class InferenceError(ValueError):
    """User-facing setup or validation error."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run research-only crop inference against a local AOI archive."
    )
    parser.add_argument("--archive-path", required=True, type=Path, help="Path to a local AOI archive.")
    parser.add_argument(
        "--extract-dir",
        type=Path,
        default=Path("data/research/merged_crop_classification/test_inputs"),
        help="Research-only local directory where the archive is extracted.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/research/merged_crop_classification/outputs/inference_test_results.json"),
        help="Path to write JSON results.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/research/merged_crop_classification/outputs/inference_test_results.csv"),
        help="Path to write CSV results.",
    )
    parser.add_argument(
        "--known-actual-label",
        default="Corn",
        help="Known actual crop label for the AOI test input.",
    )
    parser.add_argument(
        "--morocco-model-dir",
        type=Path,
        default=Path("models/Moroco_only_Model"),
        help="Directory containing Morocco-only XGBoost artifacts.",
    )
    parser.add_argument(
        "--merged-model-dir",
        type=Path,
        default=Path("models/Merged_Morocco_AgriNet_Model"),
        help="Directory containing merged five-label XGBoost artifacts.",
    )
    parser.add_argument(
        "--aoi-shared-model-dir",
        type=Path,
        default=Path("models/Merged_Morocco_AgriNet_Model"),
        help="Directory containing AOI-shared-band five-label XGBoost artifacts.",
    )
    return parser


def archive_members(archive_path: Path) -> list[str]:
    if not archive_path.exists():
        raise InferenceError(f"Archive does not exist: {archive_path}")

    result = subprocess.run(
        ["tar", "-tf", str(archive_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise InferenceError(f"Could not list archive with tar: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def extract_archive(archive_path: Path, extract_dir: Path) -> tuple[Path, list[str], str]:
    members = archive_members(archive_path)
    top_level_names = sorted({member.replace("\\", "/").split("/", 1)[0] for member in members})
    if not top_level_names:
        raise InferenceError(f"Archive has no members: {archive_path}")

    extract_dir.mkdir(parents=True, exist_ok=True)
    extracted_root = extract_dir / top_level_names[0] if len(top_level_names) == 1 else extract_dir
    zarr_already_present = find_zarr_path(extracted_root) is not None

    if zarr_already_present:
        return extracted_root, members, "already_present"

    result = subprocess.run(
        ["tar", "-xf", str(archive_path), "-C", str(extract_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise InferenceError(f"Could not extract archive with tar: {result.stderr.strip()}")
    return extracted_root, members, "extracted"


def find_zarr_path(root: Path) -> Path | None:
    if is_zarr_store(root):
        return root
    cube = root / "cube.zarr"
    if is_zarr_store(cube):
        return cube
    if root.exists():
        for path in root.rglob("*.zarr"):
            if is_zarr_store(path):
                return path
    return None


def is_zarr_store(path: Path) -> bool:
    return path.exists() and path.is_dir() and (
        path.suffix.lower() == ".zarr"
        or (path / "zarr.json").exists()
        or (path / ".zgroup").exists()
        or (path / ".zmetadata").exists()
    )


def load_pickle(path: Path) -> Any:
    if not path.exists():
        raise InferenceError(f"Missing model artifact: {path}")
    try:
        import joblib
    except ImportError as exc:
        raise InferenceError("joblib is required to load model artifacts.") from exc
    return joblib.load(path)


def load_artifacts(model_dir: Path, artifact_names: dict[str, str]) -> dict[str, Any]:
    if not model_dir.exists():
        raise InferenceError(f"Model directory does not exist: {model_dir}")
    return {key: load_pickle(model_dir / filename) for key, filename in artifact_names.items()}


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
        raise InferenceError("Feature columns artifact must contain a list-like value.")

    normalized = [str(column) for column in columns]
    if not normalized:
        raise InferenceError("Feature columns artifact is empty.")
    return normalized


def coerce_clip_bounds(bounds: Any, columns: list[str], artifact_label: str) -> pd.Series:
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
            raise InferenceError(f"{artifact_label} DataFrame does not contain required bounds.")
    else:
        array = np.asarray(bounds, dtype=np.float64)
        if array.ndim == 0:
            series = pd.Series(float(array), index=columns)
        elif array.ndim == 1 and len(array) == len(columns):
            series = pd.Series(array, index=columns)
        else:
            raise InferenceError(f"{artifact_label} must align with {len(columns)} columns.")

    missing = [column for column in columns if column not in series.index]
    if missing:
        raise InferenceError(f"{artifact_label} is missing bounds for columns: {missing}")

    coerced = pd.to_numeric(series.loc[columns], errors="coerce")
    if coerced.isna().any():
        raise InferenceError(f"{artifact_label} contains non-numeric bounds.")
    return coerced.astype(float)


def read_zarr_arrays(zarr_path: Path) -> tuple[dict[str, np.ndarray], dict[str, str], list[str]]:
    try:
        import xarray as xr
    except ImportError as exc:
        raise InferenceError("xarray is required to read Zarr AOI data.") from exc

    arrays: dict[str, np.ndarray] = {}
    sources: dict[str, str] = {}
    available: list[str] = []

    for group in [None, "20m"]:
        try:
            dataset = xr.open_zarr(zarr_path, group=group, consolidated=False)
        except Exception:
            continue
        group_name = "<root>" if group is None else group
        try:
            for name in dataset.data_vars:
                available.append(str(name))
                try:
                    values = np.asarray(dataset[name].values, dtype=np.float64)
                except Exception:
                    continue
                if values.ndim == 0:
                    continue
                arrays[str(name)] = values
                sources[str(name)] = group_name
        finally:
            dataset.close()

    if not arrays:
        raise InferenceError(f"No numeric band arrays found in Zarr store: {zarr_path}")
    return arrays, sources, sorted(set(available))


def find_band_array(arrays: dict[str, np.ndarray], aliases: Iterable[str]) -> tuple[str, np.ndarray] | None:
    for alias in aliases:
        if alias in arrays:
            return alias, arrays[alias]
    return None


def nanmean(values: np.ndarray, label: str) -> float:
    mean = float(np.nanmean(values.astype(np.float64)))
    if not np.isfinite(mean):
        raise InferenceError(f"{label} has no finite values.")
    return mean


def validate_finite_frame(df: pd.DataFrame, label: str) -> None:
    invalid = [
        column
        for column in df.columns
        if not np.isfinite(pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=np.float64)).all()
    ]
    if invalid:
        raise InferenceError(f"{label} contains NaN or infinite values in columns: {invalid}")


def prepare_morocco_features(
    arrays: dict[str, np.ndarray],
    artifacts: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw: dict[str, float] = {}
    used_bands: dict[str, str] = {}
    for band in MOROCCO_BANDS:
        found = find_band_array(arrays, MOROCCO_BAND_ALIASES[band])
        if found is None:
            raise InferenceError(f"Missing required Morocco-only band: {band}")
        source_name, values = found
        raw[band] = nanmean(values, source_name)
        used_bands[band] = source_name

    features = pd.DataFrame([raw])
    features["NDVI"] = (features["B8"] - features["B4"]) / (features["B8"] + features["B4"] + EPS)

    lower = coerce_clip_bounds(artifacts["clip_lower"], MOROCCO_COMMON_CLIP_COLUMNS, "clip_lower_common.pkl")
    upper = coerce_clip_bounds(artifacts["clip_upper"], MOROCCO_COMMON_CLIP_COLUMNS, "clip_upper_common.pkl")
    features.loc[:, MOROCCO_COMMON_CLIP_COLUMNS] = features.loc[:, MOROCCO_COMMON_CLIP_COLUMNS].clip(
        lower=lower,
        upper=upper,
        axis=1,
    )

    features["NDWI"] = (features["B3"] - features["B8"]) / (features["B3"] + features["B8"] + EPS)
    features["NDBI"] = (features["B11"] - features["B8"]) / (features["B11"] + features["B8"] + EPS)
    features["SAVI"] = 1.5 * (features["B8"] - features["B4"]) / (features["B8"] + features["B4"] + 0.5 + EPS)
    features["BSI"] = ((features["B11"] + features["B4"]) - (features["B8"] + features["B2"])) / (
        (features["B11"] + features["B4"]) + (features["B8"] + features["B2"]) + EPS
    )
    features["B11_B8_ratio"] = features["B11"] / (features["B8"] + EPS)
    features["B4_B8_ratio"] = features["B4"] / (features["B8"] + EPS)
    features["B8_B4_diff"] = features["B8"] - features["B4"]

    feature_columns = normalize_feature_columns(artifacts["feature_columns"])
    missing = [column for column in feature_columns if column not in features.columns]
    if missing:
        raise InferenceError(f"Morocco-only prepared row is missing model columns: {missing}")

    model_features = features.loc[:, feature_columns].apply(pd.to_numeric, errors="coerce")
    validate_finite_frame(model_features, "Morocco-only model feature row")
    metadata = {
        "used_bands": used_bands,
        "feature_columns": feature_columns,
        "raw_aggregated_bands": raw,
    }
    return model_features, metadata


def prepare_merged_features(
    arrays: dict[str, np.ndarray],
    artifacts: dict[str, Any],
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    raw_band_means: dict[str, float] = {}
    used_bands: dict[str, str] = {}
    missing_bands: list[str] = []

    for band in MERGED_BANDS:
        found = find_band_array(arrays, MERGED_BAND_ALIASES[band])
        if found is None:
            missing_bands.append(band)
            continue
        source_name, values = found
        raw_band_means[band] = nanmean(values, source_name)
        used_bands[band] = source_name

    missing_features = [f"{band}_mean" for band in missing_bands]
    metadata: dict[str, Any] = {
        "used_bands": used_bands,
        "raw_aggregated_band_means": raw_band_means,
        "missing_required_features": missing_features,
        "feature_columns": normalize_feature_columns(artifacts["feature_columns"]),
    }
    if missing_features:
        return None, metadata

    lower = coerce_clip_bounds(artifacts["clip_lower"], MERGED_FEATURE_COLUMNS, "clip_lower_merged_crop_5labels.pkl")
    upper = coerce_clip_bounds(artifacts["clip_upper"], MERGED_FEATURE_COLUMNS, "clip_upper_merged_crop_5labels.pkl")
    reflectance_scale = infer_reflectance_scale(raw_band_means.values(), upper)

    scaled_band_means = {
        f"{band}_mean": raw_band_means[band] / reflectance_scale
        for band in MERGED_BANDS
    }
    scaled_band_means["NDVI_mean"] = (
        scaled_band_means["B08_mean"] - scaled_band_means["B04_mean"]
    ) / (scaled_band_means["B08_mean"] + scaled_band_means["B04_mean"] + EPS)

    features = pd.DataFrame([scaled_band_means]).loc[:, MERGED_FEATURE_COLUMNS]
    features.loc[:, MERGED_FEATURE_COLUMNS] = features.loc[:, MERGED_FEATURE_COLUMNS].clip(
        lower=lower,
        upper=upper,
        axis=1,
    )

    feature_columns = metadata["feature_columns"]
    missing_model_columns = [column for column in feature_columns if column not in features.columns]
    if missing_model_columns:
        raise InferenceError(f"Merged prepared row is missing model columns: {missing_model_columns}")

    model_features = features.loc[:, feature_columns].apply(pd.to_numeric, errors="coerce")
    validate_finite_frame(model_features, "merged five-label model feature row")
    metadata["reflectance_scale_applied"] = reflectance_scale
    metadata["prepared_feature_values"] = model_features.iloc[0].to_dict()
    return model_features, metadata


def prepare_aoi_shared_features(
    arrays: dict[str, np.ndarray],
    artifacts: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw_band_means: dict[str, float] = {}
    used_bands: dict[str, str] = {}
    missing_bands: list[str] = []

    for band in AOI_SHARED_BANDS:
        found = find_band_array(arrays, MERGED_BAND_ALIASES[band])
        if found is None:
            missing_bands.append(band)
            continue
        source_name, values = found
        raw_band_means[band] = nanmean(values, source_name)
        used_bands[band] = source_name

    if missing_bands:
        missing_features = [f"{band}_mean" for band in missing_bands]
        raise InferenceError(f"Missing AOI-shared-band model features: {missing_features}")

    feature_columns = normalize_feature_columns(artifacts["feature_columns"])
    missing_from_contract = [column for column in feature_columns if column not in AOI_SHARED_FEATURE_COLUMNS]
    if missing_from_contract:
        raise InferenceError(
            f"AOI-shared feature artifact requires unavailable or unsupported columns: {missing_from_contract}"
        )

    lower = coerce_clip_bounds(
        artifacts["clip_lower"],
        feature_columns,
        "clip_lower_merged_crop_5labels_aoi_shared_bands.pkl",
    )
    upper = coerce_clip_bounds(
        artifacts["clip_upper"],
        feature_columns,
        "clip_upper_merged_crop_5labels_aoi_shared_bands.pkl",
    )
    reflectance_scale = infer_reflectance_scale(raw_band_means.values(), upper)

    scaled_band_means = {
        f"{band}_mean": raw_band_means[band] / reflectance_scale
        for band in AOI_SHARED_BANDS
    }
    features = pd.DataFrame([scaled_band_means]).loc[:, AOI_SHARED_FEATURE_COLUMNS]
    features.loc[:, feature_columns] = features.loc[:, feature_columns].clip(
        lower=lower,
        upper=upper,
        axis=1,
    )

    model_features = features.loc[:, feature_columns].apply(pd.to_numeric, errors="coerce")
    validate_finite_frame(model_features, "AOI-shared-band five-label model feature row")
    metadata = {
        "used_bands": used_bands,
        "raw_aggregated_band_means": raw_band_means,
        "feature_columns": feature_columns,
        "reflectance_scale_applied": reflectance_scale,
        "prepared_feature_values": model_features.iloc[0].to_dict(),
    }
    return model_features, metadata


def infer_reflectance_scale(raw_values: Iterable[float], clip_upper: pd.Series) -> float:
    finite_values = [float(value) for value in raw_values if np.isfinite(float(value))]
    if finite_values and max(finite_values) > 2.0 and float(clip_upper.max()) <= 2.0:
        return 10000.0
    return 1.0


def predict_row(
    *,
    model_name: str,
    model_path: Path,
    preprocessing_used: str,
    model_features: pd.DataFrame,
    artifacts: dict[str, Any],
    archive_name: str,
    known_actual_label: str,
) -> dict[str, Any]:
    model = artifacts["model"]
    label_encoder = artifacts["label_encoder"]
    probabilities = np.asarray(model.predict_proba(model_features), dtype=np.float64)
    raw_prediction = np.asarray(model.predict(model_features))
    labels = probability_labels(model, label_encoder, probabilities.shape[1])
    predicted_label = decode_predictions(label_encoder, raw_prediction)[0]

    row: dict[str, Any] = {
        "status": "ok",
        "test_input_archive": archive_name,
        "known_actual_label": known_actual_label,
        "model_name": model_name,
        "model_path": str(model_path),
        "preprocessing_used": preprocessing_used,
        "predicted_label": predicted_label,
        "is_correct": normalize_label(predicted_label) == normalize_label(known_actual_label),
    }
    for index, label in enumerate(labels):
        row[f"proba_{normalize_label(label)}"] = float(probabilities[0, index])
    return row


def blocked_row(
    *,
    status: str,
    reason: str,
    model_name: str,
    model_path: Path,
    preprocessing_used: str,
    archive_name: str,
    known_actual_label: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "status": status,
        "reason": reason,
        "test_input_archive": archive_name,
        "known_actual_label": known_actual_label,
        "model_name": model_name,
        "model_path": str(model_path),
        "preprocessing_used": preprocessing_used,
        "predicted_label": None,
        "is_correct": None,
    }
    if extra:
        row.update(extra)
    return row


def decode_predictions(label_encoder: Any, raw_prediction: np.ndarray) -> list[str]:
    if hasattr(label_encoder, "inverse_transform"):
        try:
            return [str(value) for value in label_encoder.inverse_transform(raw_prediction.astype(int))]
        except Exception:
            pass
    return [str(value) for value in raw_prediction]


def probability_labels(model: Any, label_encoder: Any, n_classes: int) -> list[str]:
    model_classes = getattr(model, "classes_", None)
    if model_classes is not None:
        model_classes_array = np.asarray(model_classes)
        if hasattr(label_encoder, "inverse_transform"):
            try:
                return [str(value) for value in label_encoder.inverse_transform(model_classes_array.astype(int))]
            except Exception:
                pass
        return [str(value) for value in model_classes_array]

    encoder_classes = getattr(label_encoder, "classes_", None)
    if encoder_classes is not None and len(encoder_classes) == n_classes:
        return [str(value) for value in encoder_classes]
    raise InferenceError("Could not determine probability class labels.")


def normalize_label(label: Any) -> str:
    return str(label).strip().lower().replace(" ", "_").replace("-", "_")


def write_outputs(payload: dict[str, Any], rows: list[dict[str, Any]], output_json: Path, output_csv: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(output_csv, index=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        extracted_root, members, extraction_status = extract_archive(args.archive_path, args.extract_dir)
        zarr_path = find_zarr_path(extracted_root)
        if zarr_path is None:
            raise InferenceError(f"No Zarr cube found after extraction under: {extracted_root}")

        arrays, sources, available = read_zarr_arrays(zarr_path)
        archive_name = args.archive_path.name
        rows: list[dict[str, Any]] = []
        model_metadata: dict[str, Any] = {}

        morocco_artifacts = load_artifacts(args.morocco_model_dir, MOROCCO_ARTIFACTS)
        try:
            morocco_features, morocco_metadata = prepare_morocco_features(arrays, morocco_artifacts)
            model_metadata["morocco_only_xgboost"] = morocco_metadata
            rows.append(
                predict_row(
                    model_name="morocco_only_xgboost",
                    model_path=args.morocco_model_dir / MOROCCO_ARTIFACTS["model"],
                    preprocessing_used=(
                        "Mean aggregate raw AOI Zarr bands; compute NDVI; clip common raw features; "
                        "compute notebook engineered indices; reorder feature_cols_v2."
                    ),
                    model_features=morocco_features,
                    artifacts=morocco_artifacts,
                    archive_name=archive_name,
                    known_actual_label=args.known_actual_label,
                )
            )
        except InferenceError as exc:
            rows.append(
                blocked_row(
                    status="blocked",
                    reason=str(exc),
                    model_name="morocco_only_xgboost",
                    model_path=args.morocco_model_dir / MOROCCO_ARTIFACTS["model"],
                    preprocessing_used="Morocco-only notebook preprocessing.",
                    archive_name=archive_name,
                    known_actual_label=args.known_actual_label,
                )
            )

        try:
            merged_artifacts = load_artifacts(args.merged_model_dir, MERGED_ARTIFACTS)
            merged_features, merged_metadata = prepare_merged_features(arrays, merged_artifacts)
            model_metadata["merged_crop_5labels_xgboost"] = merged_metadata
            if merged_features is None:
                missing = merged_metadata["missing_required_features"]
                rows.append(
                    blocked_row(
                        status="blocked_missing_required_features",
                        reason=(
                            "Archive does not contain all bands required by the merged five-label model. "
                            "No missing-band imputation was applied."
                        ),
                        model_name="merged_crop_5labels_xgboost",
                        model_path=args.merged_model_dir / MERGED_ARTIFACTS["model"],
                        preprocessing_used=(
                            "Static mean feature schema B01_mean..B12_mean plus NDVI_mean; "
                            "clip with merged five-label bounds when all required features are present."
                        ),
                        archive_name=archive_name,
                        known_actual_label=args.known_actual_label,
                        extra={"missing_required_features": ";".join(missing)},
                    )
                )
            else:
                rows.append(
                    predict_row(
                        model_name="merged_crop_5labels_xgboost",
                        model_path=args.merged_model_dir / MERGED_ARTIFACTS["model"],
                        preprocessing_used=(
                            "Mean aggregate AOI Zarr bands into B*_mean features; scale raw DNs to reflectance "
                            "when required by clip bounds; compute NDVI_mean; clip merged feature columns; "
                            "reorder feature_cols_merged_crop_5labels."
                        ),
                        model_features=merged_features,
                        artifacts=merged_artifacts,
                        archive_name=archive_name,
                        known_actual_label=args.known_actual_label,
                    )
                )
        except InferenceError as exc:
            rows.append(
                blocked_row(
                    status="blocked",
                    reason=str(exc),
                    model_name="merged_crop_5labels_xgboost",
                    model_path=args.merged_model_dir / MERGED_ARTIFACTS["model"],
                    preprocessing_used="Merged five-label notebook preprocessing.",
                    archive_name=archive_name,
                    known_actual_label=args.known_actual_label,
                )
            )

        try:
            aoi_shared_artifacts = load_artifacts(args.aoi_shared_model_dir, AOI_SHARED_ARTIFACTS)
            aoi_shared_features, aoi_shared_metadata = prepare_aoi_shared_features(arrays, aoi_shared_artifacts)
            model_metadata["merged_crop_5labels_aoi_shared_bands_xgboost"] = aoi_shared_metadata
            rows.append(
                predict_row(
                    model_name="merged_crop_5labels_aoi_shared_bands_xgboost",
                    model_path=args.aoi_shared_model_dir / AOI_SHARED_ARTIFACTS["model"],
                    preprocessing_used=(
                        "Mean aggregate AOI Zarr bands into shared B*_mean features; scale raw DNs to "
                        "reflectance when required by clip bounds; clip shared feature columns; reorder "
                        "feature_cols_merged_crop_5labels_aoi_shared_bands."
                    ),
                    model_features=aoi_shared_features,
                    artifacts=aoi_shared_artifacts,
                    archive_name=archive_name,
                    known_actual_label=args.known_actual_label,
                )
            )
        except InferenceError as exc:
            rows.append(
                blocked_row(
                    status="blocked",
                    reason=str(exc),
                    model_name="merged_crop_5labels_aoi_shared_bands_xgboost",
                    model_path=args.aoi_shared_model_dir / AOI_SHARED_ARTIFACTS["model"],
                    preprocessing_used="AOI-shared-band five-label notebook preprocessing.",
                    archive_name=archive_name,
                    known_actual_label=args.known_actual_label,
                )
            )

        payload = {
            "status": "ok",
            "research_only": True,
            "training_used": False,
            "test_input_archive": archive_name,
            "known_actual_label": args.known_actual_label,
            "archive_path": str(args.archive_path),
            "extraction_status": extraction_status,
            "extracted_root": str(extracted_root),
            "zarr_path": str(zarr_path),
            "archive_member_count": len(members),
            "available_zarr_variables": available,
            "zarr_variable_sources": sources,
            "model_metadata": model_metadata,
            "results": rows,
        }
        write_outputs(payload, rows, args.output_json, args.output_csv)
    except InferenceError as exc:
        parser.exit(2, f"Error: {exc}\n")

    print(f"Wrote JSON results to {args.output_json}")
    print(f"Wrote CSV results to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
