"""
Loads trained SITS-BERT model and runs advisory inference for one AOI.

Inference failures are written as error artifacts and are not raised.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from farmtrust_core.ml.normalization import apply_normalization, load_stats
from farmtrust_core.ml.sequence_builder import SequenceBuilder


logger = logging.getLogger(__name__)

CONFIRMED_ACTIVE_THRESHOLD = 0.80
POSSIBLE_ACTIVE_THRESHOLD = 0.65
CLASS_NAMES = ("active", "bare", "sparse", "uncertain")


def run_inference_if_model_available(
    aoi_id: str,
    data_root: str | Path = "data",
    model_dir: str | Path = "models",
) -> dict[str, Any] | None:
    model_path = Path(model_dir) / "sits_bert_finetuned.pt"
    if not model_path.exists():
        return None
    try:
        return run_inference(aoi_id=aoi_id, data_root=data_root, model_dir=model_dir)
    except Exception as exc:  # pragma: no cover - defensive API integration boundary
        logger.warning("ML inference skipped for %s: %s", aoi_id, exc)
        return None


def run_inference(aoi_id: str, data_root: str | Path = "data", model_dir: str | Path = "models") -> dict[str, Any]:
    output_path = Path(data_root) / "ml" / aoi_id / "sits_prediction.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        model_dir = Path(model_dir)
        sequence = SequenceBuilder(data_root=data_root).build(aoi_id)
        stats = load_stats(model_dir / "normalization_stats.json")
        features = apply_normalization(sequence["features"], stats)
        probabilities = _predict_probabilities(features, sequence, model_dir / "sits_bert_finetuned.pt")
        model_card = _load_model_card(model_dir / "model_card.json")
        artifact = _build_artifact(aoi_id, sequence, probabilities, model_card, data_root)
    except Exception as exc:
        logger.exception("ML inference failed for %s", aoi_id)
        artifact = _error_artifact(aoi_id, str(exc))

    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return artifact


def _predict_probabilities(features: np.ndarray, sequence: dict[str, Any], model_path: Path) -> np.ndarray:
    """Load a Kaggle-trained Torch checkpoint when available."""
    import torch

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    model = checkpoint.get("model")
    if model is None:
        model = _load_sits_bert_from_state_dict(checkpoint)
    model.eval()
    with torch.no_grad():
        logits = model(
            torch.from_numpy(features).float(),
            torch.from_numpy(sequence["attention_mask"]).bool(),
            torch.from_numpy(sequence["doy"]).long(),
        )
        if isinstance(logits, dict):
            logits = logits.get("logits")
        probabilities = torch.softmax(logits, dim=-1).cpu().numpy()
    return probabilities


def _load_sits_bert_from_state_dict(checkpoint: dict[str, Any]) -> Any:
    state_dict = checkpoint.get("model_state_dict")
    if state_dict is None:
        raise ValueError("Checkpoint does not contain 'model' or 'model_state_dict'")
    repo_root = Path(__file__).resolve().parents[2]
    kaggle_package_root = repo_root / "kaggle"
    if str(kaggle_package_root) not in sys.path:
        sys.path.insert(0, str(kaggle_package_root))
    from sits_bert.model import SITSBertFinetune

    model = SITSBertFinetune()
    model.load_state_dict(state_dict, strict=False)
    return model


def _load_model_card(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _build_artifact(
    aoi_id: str,
    sequence: dict[str, Any],
    probabilities: np.ndarray,
    model_card: dict[str, Any],
    data_root: str | Path,
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    window_summaries: list[dict[str, Any]] = []
    false_active_gates: list[str] = []

    for cycle_index, cycle in enumerate(sequence["cycle_metadata"]):
        mask = sequence["attention_mask"][cycle_index]
        timestamps = sequence["timestamps"][cycle_index]
        cycle_probs = probabilities[cycle_index]
        real_indices = np.where(mask)[0]
        for index in real_indices:
            probs = {name: float(cycle_probs[index, class_index]) for class_index, name in enumerate(CLASS_NAMES)}
            label = max(probs, key=probs.get)
            observations.append(
                {
                    "timestamp": timestamps[index],
                    "cycle_id": cycle["cycle_id"],
                    "ml_label": label,
                    "ml_probabilities": probs,
                    "ml_confidence": float(max(probs.values())),
                    "is_usable": True,
                }
            )

        summary = _summarize_cycle_window(cycle, real_indices, timestamps, cycle_probs, data_root, aoi_id)
        window_summaries.append(summary)
        false_active_gates.extend(summary.get("false_active_gates_triggered", []))

    active_probs = [row["ml_probabilities"]["active"] for row in observations]
    mean_active = float(np.mean(active_probs)) if active_probs else 0.0
    ml_land_status, lender_decision, confidence, risk, review = _decision_fields(mean_active, not false_active_gates)

    label_counts = {name: 0 for name in CLASS_NAMES}
    for row in observations:
        label_counts[row["ml_label"]] += 1
    total = max(len(observations), 1)

    return {
        "schema_version": "ml-1.1",
        "pipeline_version": "farmtrust-activity-s2-v1",
        "aoi_id": aoi_id,
        "model_version": model_card.get("model_version", "sits-bert-finetune-v1"),
        "research_model_version": "sits-bert-advisory-v0.1",
        "inference_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "thresholds": {
            "confirmed_active": CONFIRMED_ACTIVE_THRESHOLD,
            "possible_active": POSSIBLE_ACTIVE_THRESHOLD,
        },
        "ml_land_status": ml_land_status,
        "ml_lender_decision": lender_decision,
        "ml_assessment_confidence": confidence,
        "ml_false_active_risk": risk,
        "ml_review_recommendation": review,
        "ml_reliability": _load_reliability(data_root, aoi_id),
        "observations": observations,
        "ml_activity_windows": [item for item in window_summaries if item["label"] != "uncertain"],
        "ml_summary": {
            "pct_observations_active": label_counts["active"] / total,
            "pct_observations_bare": label_counts["bare"] / total,
            "pct_observations_sparse": label_counts["sparse"] / total,
            "pct_observations_uncertain": label_counts["uncertain"] / total,
            "ml_activity_window_count": sum(1 for item in window_summaries if item["label"] == "active"),
            "false_active_gates_triggered": sorted(set(false_active_gates)),
        },
        "advisory_note": "ML output is advisory. Rule-based assessment in land_assessment.json remains authoritative until ml_promoted=true.",
    }


def _summarize_cycle_window(
    cycle: dict[str, Any],
    real_indices: np.ndarray,
    timestamps: list[str],
    probabilities: np.ndarray,
    data_root: str | Path,
    aoi_id: str,
) -> dict[str, Any]:
    if len(real_indices) == 0:
        mean_active = 0.0
        active_indices: list[int] = []
    else:
        active = probabilities[real_indices, 0]
        mean_active = float(np.mean(active))
        threshold = CONFIRMED_ACTIVE_THRESHOLD if mean_active >= CONFIRMED_ACTIVE_THRESHOLD else POSSIBLE_ACTIVE_THRESHOLD
        active_indices = [int(index) for index in real_indices if probabilities[index, 0] >= threshold]

    candidate_status = _active_status(mean_active)
    gates = _false_active_gates(
        candidate_status,
        active_indices,
        timestamps,
        data_root,
        aoi_id,
        mean_active,
    )
    gates_pass = not gates
    ml_land_status, lender_decision, _, _, _ = _decision_fields(mean_active, gates_pass)
    if not gates_pass and ml_land_status == "confirmed_active":
        ml_land_status = "possible_active"

    dated = [timestamps[index] for index in active_indices if timestamps[index]]
    return {
        "window_id": f"ml_{cycle['cycle_id']}",
        "cycle_id": cycle["cycle_id"],
        "expected_window": cycle["expected_window"],
        "detected_activity_window": {
            "start_date": dated[0] if dated else None,
            "end_date": dated[-1] if dated else None,
        },
        "label": "active" if ml_land_status in {"confirmed_active", "possible_active"} else "uncertain",
        "ml_lender_decision": lender_decision,
        "mean_confidence": mean_active,
        "min_confidence": float(np.min(probabilities[active_indices, 0])) if active_indices else 0.0,
        "observation_count": int(len(active_indices)),
        "duration_days": _duration_days(dated),
        "false_active_gates_triggered": gates,
    }


def _active_status(mean_active: float) -> str:
    if mean_active >= CONFIRMED_ACTIVE_THRESHOLD:
        return "confirmed_active"
    if mean_active >= POSSIBLE_ACTIVE_THRESHOLD:
        return "possible_active"
    return "not_active"


def _false_active_gates(
    candidate_status: str,
    active_indices: list[int],
    timestamps: list[str],
    data_root: str | Path,
    aoi_id: str,
    mean_active: float,
) -> list[str]:
    gates: list[str] = []
    if candidate_status == "not_active":
        return gates
    if candidate_status == "confirmed_active" and mean_active < CONFIRMED_ACTIVE_THRESHOLD:
        gates.append("mean_active_below_confirmed_threshold")
    if candidate_status == "possible_active" and mean_active < POSSIBLE_ACTIVE_THRESHOLD:
        gates.append("mean_active_below_possible_threshold")
    if _max_consecutive(active_indices) < 3:
        gates.append("fewer_than_3_consecutive_observations")
    dated = [timestamps[index] for index in active_indices if timestamps[index]]
    if _duration_days(dated) < 15:
        gates.append("window_duration_lt_15_days")
    ndvi_mean, valid_fraction_mean = _window_means(data_root, aoi_id, set(dated))
    if ndvi_mean is not None and ndvi_mean < 0.18:
        gates.append("mean_ndvi_below_0_18")
    if valid_fraction_mean is not None and valid_fraction_mean < 0.40:
        gates.append("mean_valid_fraction_below_0_40")
    reliability = _load_reliability(data_root, aoi_id)
    if reliability.get("small_parcel_risk") == "high" or reliability.get("mixed_pixel_risk") == "high" or reliability.get("gap_risk") == "high":
        gates.append("parcel_reliability_gate_failed")
    return gates


def _max_consecutive(indices: list[int]) -> int:
    if not indices:
        return 0
    best = current = 1
    for left, right in zip(indices, indices[1:]):
        if right == left + 1:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def _duration_days(dates: list[str]) -> int:
    if len(dates) < 2:
        return 0
    start = datetime.fromisoformat(dates[0])
    end = datetime.fromisoformat(dates[-1])
    return max((end - start).days, 0)


def _window_means(data_root: str | Path, aoi_id: str, dates: set[str]) -> tuple[float | None, float | None]:
    if not dates:
        return None, None
    path = Path(data_root) / "preprocess" / aoi_id / "ndvi_smoothed.csv"
    if not path.exists():
        return None, None
    import pandas as pd

    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["date"] = pd.to_datetime(df["timestamp"], utc=True).dt.strftime("%Y-%m-%d")
    selected = df[df["date"].isin(dates)]
    if selected.empty:
        return None, None
    return float(selected["ndvi_smoothed"].mean()), float(selected["valid_fraction"].mean())


def _load_reliability(data_root: str | Path, aoi_id: str) -> dict[str, Any]:
    path = Path(data_root) / "preprocess" / aoi_id / "quality_metrics.json"
    if not path.exists():
        return {}
    metrics = json.loads(path.read_text(encoding="utf-8"))
    gap_risk = str(metrics.get("gap_risk", "unknown"))
    area_ha = metrics.get("area_ha")
    pixel_count = int(round(float(area_ha) * 100)) if area_ha is not None else None
    return {
        "small_parcel_risk": "high" if area_ha is not None and float(area_ha) < 0.5 else "unknown",
        "mixed_pixel_risk": "high" if pixel_count is not None and pixel_count < 50 else "unknown",
        "gap_risk": gap_risk,
        "area_ha": area_ha,
        "estimated_s2_pixel_count": pixel_count,
        "mean_valid_fraction": metrics.get("confidence_inputs", {}).get("mean_valid_fraction"),
    }


def _decision_fields(mean_active: float, gates_pass: bool) -> tuple[str, str, str, str, str]:
    if gates_pass and mean_active >= CONFIRMED_ACTIVE_THRESHOLD:
        return "confirmed_active", "confirmed_agricultural_activity", "high", "low", "standard_review"
    if gates_pass and mean_active >= POSSIBLE_ACTIVE_THRESHOLD:
        return "possible_active", "possible_agricultural_activity", "medium", "medium", "review_recommended"
    return "uncertain", "insufficient_evidence", "low", "high", "manual_review_required"


def _error_artifact(aoi_id: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": "ml-1.1",
        "pipeline_version": "farmtrust-activity-s2-v1",
        "aoi_id": aoi_id,
        "inference_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ml_land_status": "uncertain",
        "ml_lender_decision": "insufficient_evidence",
        "ml_assessment_confidence": "low",
        "ml_false_active_risk": "high",
        "ml_review_recommendation": "manual_review_required",
        "ml_summary": {"false_active_gates_triggered": ["inference_error"]},
        "error": message,
        "advisory_note": "ML output is advisory. Rule-based assessment in land_assessment.json remains authoritative until ml_promoted=true.",
    }
