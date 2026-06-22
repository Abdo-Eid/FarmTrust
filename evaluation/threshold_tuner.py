"""Tune active-class thresholds against the held-out proxy test set."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from evaluation.metrics import LABEL_TO_INDEX, load_prediction_for_aoi, load_test_set


DEFAULT_CONFIRMED_ACTIVE = 0.80
DEFAULT_POSSIBLE_ACTIVE = 0.65


def main() -> int:
    rows = load_test_set()
    y_true: list[int] = []
    active_prob: list[float] = []
    missing_predictions: list[str] = []

    for row in rows:
        aoi_id = row["aoi_id"]
        prediction = load_prediction_for_aoi(aoi_id)
        if prediction is None:
            missing_predictions.append(aoi_id)
            continue
        _pred, prob = prediction
        y_true.append(LABEL_TO_INDEX[row["label"]])
        active_prob.append(float(prob[0]))

    if missing_predictions:
        print("FAIL: cannot tune thresholds; missing prediction artifacts:")
        for aoi_id in missing_predictions:
            print(f"  data/ml/{aoi_id}/sits_prediction.json")
        return 0

    y_true_arr = np.asarray(y_true, dtype=int)
    active_prob_arr = np.asarray(active_prob, dtype=float)
    thresholds = np.round(np.arange(0.40, 0.91, 0.01), 2)
    sweep_rows = []

    for threshold in thresholds:
        y_pred_active = active_prob_arr >= threshold
        true_active = y_true_arr == LABEL_TO_INDEX["active"]
        tp = int((y_pred_active & true_active).sum())
        fp = int((y_pred_active & ~true_active).sum())
        fn = int((~y_pred_active & true_active).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        sweep_rows.append(
            {
                "threshold": float(threshold),
                "precision_active": precision,
                "recall_active": recall,
            }
        )

    eligible = [row for row in sweep_rows if row["precision_active"] >= 0.90]
    if eligible:
        best = max(eligible, key=lambda row: (row["recall_active"], row["threshold"]))
    else:
        best = max(sweep_rows, key=lambda row: (row["precision_active"], row["recall_active"]))

    policy = {
        "confirmed_active": DEFAULT_CONFIRMED_ACTIVE,
        "possible_active": DEFAULT_POSSIBLE_ACTIVE,
        "tuned_active_threshold": best["threshold"],
        "precision_active": best["precision_active"],
        "recall_active": best["recall_active"],
        "selection_rule": "highest recall where precision_active >= 0.90",
        "test_set_warning": "rule-based proxy test set, not manually annotated ground truth",
    }

    models_dir = Path("models")
    models_dir.mkdir(parents=True, exist_ok=True)
    policy_path = models_dir / "threshold_policy.json"
    policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")

    plot_path = models_dir / "threshold_pr_curve.png"
    plt.figure(figsize=(8, 5))
    plt.plot(
        [row["recall_active"] for row in sweep_rows],
        [row["precision_active"] for row in sweep_rows],
        marker="o",
        linewidth=1.5,
    )
    plt.scatter([best["recall_active"]], [best["precision_active"]], color="red", zorder=3)
    plt.annotate(
        f"t={best['threshold']:.2f}",
        (best["recall_active"], best["precision_active"]),
        textcoords="offset points",
        xytext=(8, 8),
    )
    plt.xlabel("Recall active")
    plt.ylabel("Precision active")
    plt.title("Active threshold sweep")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150)
    plt.close()

    print(f"Wrote threshold policy: {policy_path}")
    print(f"Wrote PR curve: {plot_path}")
    print(json.dumps(policy, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
