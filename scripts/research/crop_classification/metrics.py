"""Evaluation outputs for crop classification research models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def evaluate_classifier(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    label_encoder: Any,
    metadata: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Any]:
    """Evaluate a fitted classifier and write reusable research artifacts."""

    accuracy_score, f1_score, classification_report, confusion_matrix = _require_sklearn_metrics()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    class_names = [str(label) for label in label_encoder.classes_]
    class_ids = list(range(len(class_names)))
    y_true = np.asarray(y_test, dtype=int)
    y_pred = np.asarray(model.predict(X_test), dtype=int)

    true_labels = label_encoder.inverse_transform(y_true)
    predicted_labels = label_encoder.inverse_transform(y_pred)

    report = classification_report(
        y_true,
        y_pred,
        labels=class_ids,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    report_df = pd.DataFrame(report).transpose()
    report_df.index.name = "label"
    report_df.to_csv(output_path / "classification_report.csv")

    confusion_df = pd.DataFrame(
        confusion_matrix(y_true, y_pred, labels=class_ids),
        index=class_names,
        columns=class_names,
    )
    confusion_df.index.name = "true_label"
    confusion_df.to_csv(output_path / "confusion_matrix.csv")

    predictions_df = _predictions_frame(
        model=model,
        X_test=X_test,
        metadata=metadata,
        true_labels=true_labels,
        predicted_labels=predicted_labels,
        label_encoder=label_encoder,
    )
    predictions_df.to_csv(output_path / "predictions.csv", index=False)

    per_source_rows, per_source_accuracy = _per_source_metrics(predictions_df)
    pd.DataFrame(
        per_source_rows,
        columns=["source_dataset", "label", "sample_count", "correct_count", "accuracy"],
    ).to_csv(output_path / "per_source_metrics.csv", index=False)

    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", labels=class_ids, zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", labels=class_ids, zero_division=0)),
        "per_label": {
            label: {
                "precision": float(report[label]["precision"]),
                "recall": float(report[label]["recall"]),
                "f1": float(report[label]["f1-score"]),
                "support": int(report[label]["support"]),
            }
            for label in class_names
        },
        "per_source_accuracy": per_source_accuracy,
        "per_source_label_counts": [
            {
                "source_dataset": row["source_dataset"],
                "label": row["label"],
                "sample_count": row["sample_count"],
            }
            for row in per_source_rows
            if row["label"] != "ALL"
        ],
    }

    with (output_path / "metrics.json").open("w", encoding="utf-8") as file:
        json.dump(_json_safe(metrics), file, indent=2)

    return metrics


def _require_sklearn_metrics() -> tuple[Any, Any, Any, Any]:
    try:
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for model evaluation. Run `uv sync --extra ml`.") from exc

    return accuracy_score, f1_score, classification_report, confusion_matrix


def _predictions_frame(
    model: Any,
    X_test: pd.DataFrame,
    metadata: pd.DataFrame,
    true_labels: np.ndarray,
    predicted_labels: np.ndarray,
    label_encoder: Any,
) -> pd.DataFrame:
    metadata_frame = metadata.reset_index(drop=True).copy()
    for column in ["field_id", "source_dataset"]:
        if column not in metadata_frame.columns:
            metadata_frame[column] = pd.NA

    predictions_df = pd.DataFrame(
        {
            "field_id": metadata_frame["field_id"],
            "source_dataset": metadata_frame["source_dataset"],
            "true_label": true_labels,
            "predicted_label": predicted_labels,
        }
    )

    probability_df = _probability_frame(model, X_test, label_encoder)
    return pd.concat([predictions_df, probability_df], axis=1)


def _probability_frame(model: Any, X_test: pd.DataFrame, label_encoder: Any) -> pd.DataFrame:
    probabilities = np.asarray(model.predict_proba(X_test))
    model_classes = list(np.asarray(getattr(model, "classes_", range(probabilities.shape[1])), dtype=int))
    class_positions = {class_id: position for position, class_id in enumerate(model_classes)}

    probability_columns: dict[str, np.ndarray] = {}
    for encoded_label, label in enumerate(label_encoder.classes_):
        position = class_positions.get(encoded_label)
        if position is None:
            probability_columns[f"proba_{label}"] = np.zeros(len(X_test), dtype=float)
        else:
            probability_columns[f"proba_{label}"] = probabilities[:, position]

    return pd.DataFrame(probability_columns)


def _per_source_metrics(predictions_df: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, float]]:
    rows: list[dict[str, Any]] = []
    per_source_accuracy: dict[str, float] = {}

    if "source_dataset" not in predictions_df.columns or not predictions_df["source_dataset"].notna().any():
        return rows, per_source_accuracy

    for source, source_group in predictions_df.groupby("source_dataset", dropna=False):
        source_name = "<missing>" if pd.isna(source) else str(source)
        correct_mask = source_group["true_label"] == source_group["predicted_label"]
        correct_count = int(correct_mask.sum())
        accuracy = float(correct_count / len(source_group)) if len(source_group) else 0.0
        per_source_accuracy[source_name] = accuracy
        rows.append(
            {
                "source_dataset": source_name,
                "label": "ALL",
                "sample_count": int(len(source_group)),
                "correct_count": correct_count,
                "accuracy": accuracy,
            }
        )

        for label, label_group in source_group.groupby("true_label", dropna=False):
            label_name = "<missing>" if pd.isna(label) else str(label)
            label_correct_count = int((label_group["true_label"] == label_group["predicted_label"]).sum())
            label_accuracy = float(label_correct_count / len(label_group)) if len(label_group) else 0.0
            rows.append(
                {
                    "source_dataset": source_name,
                    "label": label_name,
                    "sample_count": int(len(label_group)),
                    "correct_count": label_correct_count,
                    "accuracy": label_accuracy,
                }
            )

    return rows, per_source_accuracy


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value
