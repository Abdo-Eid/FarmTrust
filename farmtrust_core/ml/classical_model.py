"""LightGBM/CatBoost agricultural-cycle activity model helpers."""

from __future__ import annotations

import argparse
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, classification_report, f1_score, precision_score

from farmtrust_core.ml.cycle_features import CLASSICAL_FEATURE_NAMES, build_cycle_feature_table


RANDOM_SEED = 42
CLASS_NAMES = ("active", "bare", "sparse", "uncertain")
CONFIRMED_ACTIVE_THRESHOLD = 0.80
POSSIBLE_ACTIVE_THRESHOLD = 0.65


def train_lightgbm(
    data_root: str | Path = "data",
    model_dir: str | Path = "models",
) -> dict[str, Any]:
    """Train the priority production candidate and save model/metrics artifacts."""
    from lightgbm import LGBMClassifier

    table = build_cycle_feature_table(data_root=data_root)
    X = table[CLASSICAL_FEATURE_NAMES].to_numpy(dtype=np.float32)
    y = table["label"].to_numpy(dtype=np.int64)
    unique_labels = sorted(set(int(value) for value in y.tolist()))
    if len(unique_labels) < 2:
        raise ValueError(f"Need at least two weak-label classes to train LightGBM, got {unique_labels}")

    model = LGBMClassifier(
        objective="multiclass",
        num_class=4,
        n_estimators=30,
        learning_rate=0.05,
        max_depth=3,
        min_child_samples=1,
        subsample=1.0,
        colsample_bytree=1.0,
        random_state=RANDOM_SEED,
        class_weight=None,
        verbosity=-1,
    )
    model.fit(X, y)
    probabilities = _expand_probabilities(model.predict_proba(X), model.classes_)
    predictions = probabilities.argmax(axis=1)
    metrics = _metrics(y, predictions, probabilities)

    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "activity_lightgbm.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(
            {
                "model": model,
                "feature_names": CLASSICAL_FEATURE_NAMES,
                "class_names": CLASS_NAMES,
                "thresholds": {
                    "confirmed_active": CONFIRMED_ACTIVE_THRESHOLD,
                    "possible_active": POSSIBLE_ACTIVE_THRESHOLD,
                },
            },
            handle,
        )

    report = {
        "model_version": "activity-lightgbm-v1",
        "trained_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rows": int(len(table)),
        "label_distribution": {CLASS_NAMES[label]: int((y == label).sum()) for label in unique_labels},
        "metrics": metrics,
        "thresholds": {
            "confirmed_active": CONFIRMED_ACTIVE_THRESHOLD,
            "possible_active": POSSIBLE_ACTIVE_THRESHOLD,
        },
        "validation_source": "manual_validation.csv not present; metrics are training-set smoke metrics",
    }
    (model_dir / "activity_lightgbm_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"model_path": str(model_path), "report": report, "feature_table": table}


def train_catboost(
    data_root: str | Path = "data",
    model_dir: str | Path = "models",
) -> dict[str, Any]:
    """Optionally train CatBoost with the same cycle-level features."""
    from catboost import CatBoostClassifier

    table = build_cycle_feature_table(data_root=data_root)
    X = table[CLASSICAL_FEATURE_NAMES].to_numpy(dtype=np.float32)
    y = table["label"].to_numpy(dtype=np.int64)
    unique_labels = sorted(set(int(value) for value in y.tolist()))
    if len(unique_labels) < 2:
        raise ValueError(f"Need at least two weak-label classes to train CatBoost, got {unique_labels}")

    model = CatBoostClassifier(
        loss_function="MultiClass",
        iterations=30,
        learning_rate=0.05,
        depth=3,
        random_seed=RANDOM_SEED,
        verbose=False,
    )
    model.fit(X, y)
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "activity_catboost.cbm"
    model.save_model(str(model_path))
    return {"model_path": str(model_path), "rows": int(len(table))}


def load_lightgbm(model_path: str | Path = "models/activity_lightgbm.pkl") -> dict[str, Any]:
    with Path(model_path).open("rb") as handle:
        return pickle.load(handle)


def predict_lightgbm(feature_table: pd.DataFrame, model_path: str | Path = "models/activity_lightgbm.pkl") -> pd.DataFrame:
    bundle = load_lightgbm(model_path)
    model = bundle["model"]
    X = feature_table[bundle["feature_names"]].to_numpy(dtype=np.float32)
    probabilities = _expand_probabilities(model.predict_proba(X), model.classes_)
    output = feature_table[["aoi_id", "cycle_id"]].copy()
    for index, class_name in enumerate(CLASS_NAMES):
        output[f"p_{class_name}"] = probabilities[:, index]
    output["ml_lender_decision"] = [
        _decision(row[0], int(np.argmax(row))) for row in probabilities
    ]
    return output


def _expand_probabilities(raw_probabilities: np.ndarray, classes: np.ndarray) -> np.ndarray:
    expanded = np.zeros((raw_probabilities.shape[0], len(CLASS_NAMES)), dtype=np.float32)
    for column_index, label in enumerate(classes):
        expanded[:, int(label)] = raw_probabilities[:, column_index]
    return expanded


def _metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    return {
        "precision_active": float(precision_score(y_true, y_pred, labels=[0], average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "false_active_rate": _false_active_rate(y_true, y_pred),
        "mean_p_active": float(np.mean(y_prob[:, 0])),
    }


def _false_active_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    negatives = y_true != 0
    if int(negatives.sum()) == 0:
        return 0.0
    false_active = (y_pred == 0) & negatives
    return float(false_active.sum() / negatives.sum())


def _decision(p_active: float, top_class: int) -> str:
    if p_active >= CONFIRMED_ACTIVE_THRESHOLD:
        return "confirmed_agricultural_activity"
    if p_active >= POSSIBLE_ACTIVE_THRESHOLD:
        return "possible_agricultural_activity"
    if top_class == 1:
        return "no_agricultural_activity_detected"
    if top_class == 2:
        return "weak_or_sparse_vegetation"
    return "insufficient_evidence"


def main() -> int:
    parser = argparse.ArgumentParser(description="Train FarmTrust classical agricultural activity model.")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--model-dir", default="models")
    parser.add_argument("--catboost", action="store_true", help="Also train optional CatBoost candidate")
    args = parser.parse_args()

    result = train_lightgbm(data_root=args.data_root, model_dir=args.model_dir)
    print(json.dumps(result["report"], indent=2))
    if args.catboost:
        catboost_result = train_catboost(data_root=args.data_root, model_dir=args.model_dir)
        print(json.dumps(catboost_result, indent=2))
    print(f"Saved LightGBM model: {result['model_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
