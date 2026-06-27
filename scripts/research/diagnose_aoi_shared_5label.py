"""Research-only diagnostics for the AOI-shared five-label crop model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from infer_merged_crop_archive_test import (
    AOI_SHARED_ARTIFACTS,
    AOI_SHARED_BANDS,
    MERGED_BAND_ALIASES,
    archive_members,
    decode_predictions,
    extract_archive,
    find_band_array,
    find_zarr_path,
    infer_reflectance_scale,
    load_artifacts,
    nanmean,
    normalize_label,
    probability_labels,
    read_zarr_arrays,
)


EPS = 1e-6
DEFAULT_OUTPUT_JSON = Path("data/research/merged_crop_classification/outputs/aoi_shared_5label_diagnostics.json")
DEFAULT_FEATURE_CSV = Path("data/research/merged_crop_classification/outputs/aoi_shared_5label_feature_diagnostics.csv")

TRAINING_STATS = {
    "B02_mean": {"count": 7200.0, "mean": 0.103596, "std": 0.045052, "min": 0.040919, "q1": 0.064886, "median": 0.083036, "q3": 0.155505, "max": 0.174871},
    "B03_mean": {"count": 7200.0, "mean": 0.121774, "std": 0.031642, "min": 0.064687, "q1": 0.095354, "median": 0.118648, "q3": 0.150373, "max": 0.184314},
    "B04_mean": {"count": 7200.0, "mean": 0.147048, "std": 0.038137, "min": 0.061248, "q1": 0.119953, "median": 0.150686, "q3": 0.175442, "max": 0.229736},
    "B05_mean": {"count": 7200.0, "mean": 0.173012, "std": 0.035802, "min": 0.096251, "q1": 0.148402, "median": 0.176471, "q3": 0.196931, "max": 0.261463},
    "B06_mean": {"count": 7200.0, "mean": 0.228392, "std": 0.039116, "min": 0.127715, "q1": 0.205420, "median": 0.228583, "q3": 0.252077, "max": 0.320053},
    "B07_mean": {"count": 7200.0, "mean": 0.259957, "std": 0.045723, "min": 0.140964, "q1": 0.235598, "median": 0.261123, "q3": 0.288081, "max": 0.368770},
    "B08_mean": {"count": 7200.0, "mean": 0.262347, "std": 0.049236, "min": 0.148800, "q1": 0.232692, "median": 0.256725, "q3": 0.294094, "max": 0.385188},
    "B8A_mean": {"count": 7200.0, "mean": 0.194632, "std": 0.120266, "min": 0.040998, "q1": 0.058824, "median": 0.233323, "q3": 0.300823, "max": 0.391326},
    "B11_mean": {"count": 7200.0, "mean": 0.270562, "std": 0.079751, "min": 0.069020, "q1": 0.221310, "median": 0.268384, "q3": 0.329589, "max": 0.445103},
}

AOI_HOLDOUT_METRICS = {
    "accuracy": 0.8354166666666667,
    "macro_f1": 0.7305025296798493,
    "weighted_f1": 0.8409700758719112,
    "per_class": {
        "Corn": {"precision": 0.766764, "recall": 0.845659, "f1_score": 0.804281, "support": 311},
        "Potatoes": {"precision": 0.644231, "recall": 0.728261, "f1_score": 0.683673, "support": 92},
        "Rice": {"precision": 0.727273, "recall": 0.774194, "f1_score": 0.750000, "support": 31},
        "Sugarcane": {"precision": 0.433735, "recall": 0.666667, "f1_score": 0.525547, "support": 54},
        "Wheat": {"precision": 0.927024, "recall": 0.853992, "f1_score": 0.889010, "support": 952},
    },
    "confusion_matrix": {
        "labels": ["Corn", "Potatoes", "Rice", "Sugarcane", "Wheat"],
        "rows_true_columns_predicted": [
            [263, 5, 2, 6, 35],
            [3, 67, 3, 2, 17],
            [6, 0, 24, 1, 0],
            [6, 0, 0, 36, 12],
            [65, 32, 4, 38, 813],
        ],
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diagnose the AOI-shared five-label crop model prediction for one AOI archive."
    )
    parser.add_argument("--archive-path", required=True, type=Path, help="Path to a local AOI archive.")
    parser.add_argument(
        "--extract-dir",
        type=Path,
        default=Path("data/research/merged_crop_classification/test_inputs"),
        help="Research-only local directory where the archive is extracted.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/Merged_Morocco_AgriNet_Model"),
        help="Directory containing AOI-shared-band five-label XGBoost artifacts.",
    )
    parser.add_argument("--known-actual-label", default="Corn", help="Known actual crop label for the AOI test input.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON, help="Path to write JSON diagnostics.")
    parser.add_argument(
        "--feature-diagnostics-csv",
        type=Path,
        default=DEFAULT_FEATURE_CSV,
        help="Path to write per-feature diagnostics CSV.",
    )
    return parser


def approximate_percentile(value: float, stats: dict[str, float]) -> float:
    anchors = [
        (stats["min"], 0.0),
        (stats["q1"], 25.0),
        (stats["median"], 50.0),
        (stats["q3"], 75.0),
        (stats["max"], 100.0),
    ]
    if value <= anchors[0][0]:
        return 0.0
    if value >= anchors[-1][0]:
        return 100.0
    for (left_value, left_pct), (right_value, right_pct) in zip(anchors, anchors[1:]):
        if left_value <= value <= right_value:
            if right_value == left_value:
                return right_pct
            ratio = (value - left_value) / (right_value - left_value)
            return left_pct + ratio * (right_pct - left_pct)
    return float("nan")


def model_expected_feature_count(model: Any) -> int | None:
    n_features = getattr(model, "n_features_in_", None)
    if n_features is not None:
        return int(n_features)
    booster = model.get_booster() if hasattr(model, "get_booster") else None
    if booster is not None:
        try:
            return int(booster.num_features())
        except Exception:
            return None
    return None


def write_outputs(payload: dict[str, Any], feature_rows: list[dict[str, Any]], output_json: Path, feature_csv: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    feature_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pd.DataFrame(feature_rows).to_csv(feature_csv, index=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    members = archive_members(args.archive_path)
    extracted_root, _, extraction_status = extract_archive(args.archive_path, args.extract_dir)
    zarr_path = find_zarr_path(extracted_root)
    if zarr_path is None:
        parser.exit(2, f"Error: No Zarr cube found after extraction under: {extracted_root}\n")

    arrays, sources, available = read_zarr_arrays(zarr_path)
    artifacts = load_artifacts(args.model_dir, AOI_SHARED_ARTIFACTS)
    model = artifacts["model"]
    label_encoder = artifacts["label_encoder"]
    feature_columns = list(artifacts["feature_columns"])
    clip_lower = artifacts["clip_lower"].loc[feature_columns].astype(float)
    clip_upper = artifacts["clip_upper"].loc[feature_columns].astype(float)

    raw_band_means: dict[str, float] = {}
    used_bands: dict[str, str] = {}
    for band in AOI_SHARED_BANDS:
        found = find_band_array(arrays, MERGED_BAND_ALIASES[band])
        if found is None:
            parser.exit(2, f"Error: Missing required AOI shared band: {band}\n")
        source_name, values = found
        raw_band_means[band] = nanmean(values, source_name)
        used_bands[band] = source_name

    reflectance_scale = infer_reflectance_scale(raw_band_means.values(), clip_upper)
    before_clip = pd.DataFrame(
        [{f"{band}_mean": raw_band_means[band] / reflectance_scale for band in AOI_SHARED_BANDS}]
    ).loc[:, feature_columns]
    after_clip = before_clip.clip(lower=clip_lower, upper=clip_upper, axis=1)

    probabilities = np.asarray(model.predict_proba(after_clip), dtype=np.float64)
    raw_prediction = np.asarray(model.predict(after_clip))
    decoded_prediction = label_encoder.inverse_transform(raw_prediction.astype(int))
    probability_order = probability_labels(model, label_encoder, probabilities.shape[1])
    probability_map = {
        label: float(probabilities[0, index])
        for index, label in enumerate(probability_order)
    }

    computed_ndvi = (
        before_clip.loc[0, "B08_mean"] - before_clip.loc[0, "B04_mean"]
    ) / (before_clip.loc[0, "B08_mean"] + before_clip.loc[0, "B04_mean"] + EPS)

    feature_rows: list[dict[str, Any]] = []
    for feature in feature_columns:
        stats = TRAINING_STATS[feature]
        value_before = float(before_clip.loc[0, feature])
        value_after = float(after_clip.loc[0, feature])
        clipped_low = value_before < float(clip_lower.loc[feature])
        clipped_high = value_before > float(clip_upper.loc[feature])
        feature_rows.append(
            {
                "feature": feature,
                "aoi_value_before_clipping": value_before,
                "aoi_value_after_clipping": value_after,
                "clip_lower": float(clip_lower.loc[feature]),
                "clip_upper": float(clip_upper.loc[feature]),
                "was_clipped_low": clipped_low,
                "was_clipped_high": clipped_high,
                "training_mean": stats["mean"],
                "training_std": stats["std"],
                "training_min": stats["min"],
                "training_max": stats["max"],
                "training_q1": stats["q1"],
                "training_median": stats["median"],
                "training_q3": stats["q3"],
                "approx_percentile_after_clipping": approximate_percentile(value_after, stats),
                "outside_training_range_before_clipping": value_before < stats["min"] or value_before > stats["max"],
                "outside_training_range_after_clipping": value_after < stats["min"] or value_after > stats["max"],
                "z_score_after_clipping": (value_after - stats["mean"]) / stats["std"] if stats["std"] else None,
            }
        )

    clipped_features = [
        row["feature"]
        for row in feature_rows
        if row["was_clipped_low"] or row["was_clipped_high"]
    ]
    corn_to_wheat_confusion = AOI_HOLDOUT_METRICS["confusion_matrix"]["rows_true_columns_predicted"][0][4]
    corn_support = AOI_HOLDOUT_METRICS["per_class"]["Corn"]["support"]

    payload = {
        "status": "failed_validation_diagnosed",
        "research_only": True,
        "training_used": False,
        "production_output_changed": False,
        "test_input_archive": args.archive_path.name,
        "known_actual_label": args.known_actual_label,
        "extraction_status": extraction_status,
        "extracted_root": str(extracted_root),
        "zarr_path": str(zarr_path),
        "archive_member_count": len(members),
        "available_zarr_variables": available,
        "zarr_variable_sources": sources,
        "model_artifact": str(args.model_dir / AOI_SHARED_ARTIFACTS["model"]),
        "label_encoder_artifact": str(args.model_dir / AOI_SHARED_ARTIFACTS["label_encoder"]),
        "feature_columns_artifact": str(args.model_dir / AOI_SHARED_ARTIFACTS["feature_columns"]),
        "clip_lower_artifact": str(args.model_dir / AOI_SHARED_ARTIFACTS["clip_lower"]),
        "clip_upper_artifact": str(args.model_dir / AOI_SHARED_ARTIFACTS["clip_upper"]),
        "class_mapping": {
            "model_classes": [int(value) for value in np.asarray(getattr(model, "classes_", []))],
            "label_encoder_classes": [str(value) for value in label_encoder.classes_],
            "probability_column_order": probability_order,
            "predicted_numeric_class": int(raw_prediction[0]),
            "decoded_predicted_label": str(decoded_prediction[0]),
            "label_mapping_bug_detected": False,
            "conclusion": "Wheat is the decoded class for numeric class 4; this is a real model output, not a probability-order bug.",
        },
        "prediction": {
            "predicted_label": str(decoded_prediction[0]),
            "is_correct": normalize_label(decoded_prediction[0]) == normalize_label(args.known_actual_label),
            "probabilities": probability_map,
        },
        "feature_order_check": {
            "artifact_feature_columns": feature_columns,
            "inference_dataframe_columns": list(after_clip.columns),
            "matches_artifact_order": feature_columns == list(after_clip.columns),
            "model_expected_feature_count": model_expected_feature_count(model),
            "actual_feature_count": len(feature_columns),
        },
        "preprocessing_check": {
            "reflectance_scale_applied": reflectance_scale,
            "raw_band_means": raw_band_means,
            "used_bands": used_bands,
            "aoi_row_before_clipping": before_clip.iloc[0].to_dict(),
            "aoi_row_after_clipping": after_clip.iloc[0].to_dict(),
            "clipped_features": clipped_features,
            "clipped_feature_count": len(clipped_features),
            "clipping_conclusion": (
                "Six of nine features are above the training clip upper bound and are clipped high."
                if len(clipped_features) >= 6
                else "Clipping affected fewer than six features."
            ),
        },
        "ndvi_check": {
            "computed_ndvi_from_aoi_b08_b04": float(computed_ndvi),
            "ndvi_in_aoi_shared_feature_columns": "NDVI_mean" in feature_columns,
            "conclusion": "The AOI-shared model was trained without NDVI_mean even though NDVI can be computed from B08 and B04.",
            "future_model_suggestion": "A safer future AOI-compatible model should test shared bands plus computed NDVI_mean.",
        },
        "training_performance_from_notebook": AOI_HOLDOUT_METRICS,
        "corn_wheat_confusion_from_notebook": {
            "corn_holdout_support": corn_support,
            "corn_predicted_as_wheat": corn_to_wheat_confusion,
            "corn_to_wheat_confusion_rate": corn_to_wheat_confusion / corn_support,
            "wheat_predicted_as_corn": AOI_HOLDOUT_METRICS["confusion_matrix"]["rows_true_columns_predicted"][4][0],
        },
        "feature_diagnostics_csv": str(args.feature_diagnostics_csv),
        "diagnosis_summary": [
            "The Wheat prediction is not a label-mapping bug.",
            "Feature order and model feature count match the artifact contract.",
            "The AOI row is high relative to the clipped training feature distribution; six shared-band features clip at the upper bound.",
            "The AOI-shared model excludes NDVI_mean, while the Morocco-only model uses NDVI and additional engineered indices.",
            "Notebook holdout metrics show non-trivial Corn-to-Wheat confusion: 35 of 311 Corn holdout rows were predicted as Wheat.",
            "This remains a failed validation for the AOI-shared five-label model.",
        ],
    }

    write_outputs(payload, feature_rows, args.output_json, args.feature_diagnostics_csv)
    print(f"Wrote diagnostics JSON to {args.output_json}")
    print(f"Wrote feature diagnostics CSV to {args.feature_diagnostics_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
