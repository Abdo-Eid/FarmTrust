"""CLI for training the research-only merged crop XGBoost baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from .data import load_merged_dataset, split_dataset
from .metrics import evaluate_classifier
from .schema import (
    FEATURE_COLUMNS,
    METADATA_COLUMNS,
    TARGET_COLUMN,
    filter_to_valid_labels,
    get_unsupported_label_counts,
    validate_schema,
)

DEFAULT_MERGED_DATA = Path("data/combined_model_ready_scaled.xlsx")
DEFAULT_OUTPUT_DIR = Path("data/research/merged_crop_classification/outputs/xgboost_baseline")
MISSING_DATA_MESSAGE = (
    "Merged dataset not found. Expected data/combined_model_ready_scaled.xlsx or pass --merged-data."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train a research-only XGBoost baseline for merged crop classification data."
    )
    parser.add_argument(
        "--merged-data",
        type=Path,
        default=DEFAULT_MERGED_DATA,
        help="Path to the merged crop-classification dataset (.csv, .xlsx, or .xls).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where model and evaluation artifacts will be written.",
    )
    parser.add_argument("--test-size", type=float, default=0.2, help="Held-out test split fraction.")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed for splitting and XGBoost.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize the merged dataset without training or writing artifacts.",
    )
    parser.add_argument(
        "--strict-labels",
        action="store_true",
        help="Fail on unsupported labels instead of filtering to the current research label scope.",
    )
    parser.add_argument(
        "--class-weight",
        choices=["none", "balanced"],
        default="balanced",
        help="Class weighting strategy for the imbalanced multi-class training split.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        raw_df = load_merged_dataset(args.merged_data, filter_invalid_labels=False)
        if args.strict_labels:
            df = raw_df
            removed_label_counts: dict[str, int] = get_unsupported_label_counts(raw_df)
        else:
            removed_label_counts = get_unsupported_label_counts(raw_df)
            df = filter_to_valid_labels(raw_df)

        validate_schema(df)

        if args.dry_run:
            print_dry_run_summary(
                df,
                original_row_count=len(raw_df),
                removed_label_counts=removed_label_counts,
            )
            return 0

        train_baseline(
            df=df,
            output_dir=args.output_dir,
            merged_data_path=args.merged_data,
            test_size=args.test_size,
            random_state=args.random_state,
            class_weight=args.class_weight,
        )
    except FileNotFoundError:
        parser.exit(2, f"{MISSING_DATA_MESSAGE}\n")
    except (RuntimeError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")

    return 0


def train_baseline(
    df: pd.DataFrame,
    output_dir: Path,
    merged_data_path: Path,
    test_size: float,
    random_state: int,
    class_weight: str,
) -> None:
    """Train XGBoost on spectral features while retaining metadata for evaluation only."""

    LabelEncoder, XGBClassifier, compute_sample_weight, joblib_dump = _require_training_dependencies()

    X_train, X_test, y_train_text, y_test_text, _metadata_train, metadata_test = split_dataset(
        df=df,
        test_size=test_size,
        random_state=random_state,
    )

    label_encoder = LabelEncoder()
    label_encoder.fit(pd.concat([y_train_text, y_test_text], ignore_index=True))
    y_train = label_encoder.transform(y_train_text)
    y_test = label_encoder.transform(y_test_text)

    model_config: dict[str, Any] = {
        "objective": "multi:softprob",
        "eval_metric": "mlogloss",
        "n_estimators": 300,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "random_state": random_state,
        "n_jobs": -1,
    }

    model = XGBClassifier(**model_config)
    sample_weight = None
    if class_weight == "balanced":
        sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)
        if len(sample_weight) != len(y_train):
            raise ValueError("sample_weight length must equal len(y_train).")
        print("Balanced sample weights are enabled for the training split.")
        model.fit(X_train, y_train, sample_weight=sample_weight)
    elif class_weight == "none":
        print("No class weighting is used.")
        model.fit(X_train, y_train)
    else:
        raise ValueError("class_weight must be 'none' or 'balanced'.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    joblib_dump(model, output_path / "model.joblib")
    joblib_dump(label_encoder, output_path / "label_encoder.joblib")

    with (output_path / "feature_columns.json").open("w", encoding="utf-8") as file:
        json.dump(FEATURE_COLUMNS, file, indent=2)

    training_config = {
        "merged_data": str(merged_data_path),
        "test_size": test_size,
        "random_state": random_state,
        "row_count": int(len(df)),
        "train_row_count": int(len(X_train)),
        "test_row_count": int(len(X_test)),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "metadata_columns_excluded_from_model": METADATA_COLUMNS,
        "label_classes": [str(label) for label in label_encoder.classes_],
        "class_weight": class_weight,
        "sample_weight_used": sample_weight is not None,
        "model_config": model_config,
        "early_stopping": None,
    }
    with (output_path / "training_config.json").open("w", encoding="utf-8") as file:
        json.dump(training_config, file, indent=2)

    evaluate_classifier(
        model=model,
        X_test=X_test,
        y_test=pd.Series(y_test, name=TARGET_COLUMN),
        label_encoder=label_encoder,
        metadata=metadata_test,
        output_dir=output_path,
    )

    _write_feature_importance(model, output_path)
    print(f"Saved XGBoost crop baseline artifacts to {output_path}")


def print_dry_run_summary(
    df: pd.DataFrame,
    *,
    original_row_count: int | None = None,
    removed_label_counts: dict[str, int] | None = None,
) -> None:
    """Print validation summaries without training or writing any artifacts."""

    original_count = len(df) if original_row_count is None else original_row_count
    filtered_count = len(df)
    removed_counts = removed_label_counts or {}
    removed_count = int(sum(removed_counts.values()))

    print(f"Original row count: {original_count}")
    print(f"Filtered row count: {filtered_count}")
    print(f"Removed row count: {removed_count}")
    print(f"Removed unsupported label counts: {removed_counts}")
    print()

    print("Rows by source_dataset:")
    print(df["source_dataset"].value_counts(dropna=False).to_string())
    print()

    label_counts = df[TARGET_COLUMN].value_counts(dropna=False).sort_index()
    print("Class distribution after filtering:")
    print(label_counts.to_string())
    print()

    majority_count = int(label_counts.max())
    minority_count = int(label_counts.min())
    imbalance_ratio = float("inf") if minority_count == 0 else majority_count / minority_count
    print("Class imbalance summary:")
    print(f"Majority class count: {majority_count}")
    print(f"Minority class count: {minority_count}")
    print(f"Majority/minority ratio: {imbalance_ratio:.4f}")
    print()

    print("Rows by source_dataset + label:")
    source_label_counts = (
        df.groupby(["source_dataset", TARGET_COLUMN], dropna=False).size().rename("row_count").reset_index()
    )
    print(source_label_counts.to_string(index=False))
    print()

    print("Feature min/max/mean:")
    feature_summary = df.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="raise").agg(["min", "max", "mean"]).T
    print(feature_summary.to_string())


def _require_training_dependencies() -> tuple[Any, Any, Any, Any]:
    try:
        from joblib import dump as joblib_dump
        from sklearn.preprocessing import LabelEncoder
        from sklearn.utils.class_weight import compute_sample_weight
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError("ML training dependencies are required. Run `uv sync --extra ml`.") from exc

    return LabelEncoder, XGBClassifier, compute_sample_weight, joblib_dump


def _write_feature_importance(model: Any, output_dir: Path) -> None:
    importance_df = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    importance_df.to_csv(output_dir / "feature_importance.csv", index=False)


if __name__ == "__main__":
    raise SystemExit(main())
