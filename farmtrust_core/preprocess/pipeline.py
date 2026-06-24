"""Core pipeline for Phase A preprocessing."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from farmtrust_core.ingest.utils import safe_write_text

from .gaps import (
    EXPECTED_CADENCE_DAYS,
    build_confidence_inputs,
    classify_gap_risk,
    compute_gap_metrics,
    compute_gap_windows,
)
from .smoothing import smoothing_metadata, smooth_usable_values
from .smoothing import build_analysis_values


REQUIRED_COLUMNS = (
    "item_id",
    "timestamp",
    "valid_fraction",
    "ndvi_mean",
    "evi_mean",
    "ndmi_mean",
    "ndwi_mean",
)
DEFAULT_VALID_FRACTION_THRESHOLD = 0.90


@dataclass(frozen=True)
class RawObservation:
    item_id: str
    timestamp: datetime
    valid_fraction: float
    ndvi_raw: float
    evi_raw: float
    ndmi_raw: float
    ndwi_raw: float


@dataclass(frozen=True)
class MergedObservation:
    timestamp: datetime
    valid_fraction: float
    ndvi_raw: float
    evi_raw: float
    ndmi_raw: float
    ndwi_raw: float
    source_row_count: int


@dataclass(frozen=True)
class ProcessedObservation:
    timestamp: datetime
    valid_fraction: float
    ndvi_raw: float
    ndvi_filled: float
    ndvi_smoothed: Optional[float]
    evi_raw: float
    evi_filled: float
    evi_smoothed: Optional[float]
    ndmi_raw: float
    ndmi_filled: float
    ndmi_smoothed: Optional[float]
    ndwi_raw: float
    ndwi_filled: float
    ndwi_smoothed: Optional[float]
    is_usable: bool
    source_row_count: int


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp value: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _weighted_average(values: Iterable[float], weights: Iterable[float]) -> float:
    values_list = list(values)
    weights_list = [max(float(weight), 0.0) for weight in weights]
    total_weight = sum(weights_list)

    if total_weight <= 0:
        return float(sum(values_list) / len(values_list))

    weighted_sum = sum(value * weight for value, weight in zip(values_list, weights_list))
    return float(weighted_sum / total_weight)


def _isoformat_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def load_ingestion_observations(csv_path: Path) -> list[RawObservation]:
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {csv_path}")

        missing_columns = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                f"CSV is missing required columns {missing_columns}: {csv_path}"
            )

        observations: list[RawObservation] = []
        for row in reader:
            observations.append(
                RawObservation(
                    item_id=row["item_id"],
                    timestamp=_parse_timestamp(row["timestamp"]),
                    valid_fraction=float(row["valid_fraction"]),
                    ndvi_raw=float(row["ndvi_mean"]),
                    evi_raw=float(row["evi_mean"]),
                    ndmi_raw=float(row["ndmi_mean"]),
                    ndwi_raw=float(row["ndwi_mean"]),
                )
            )

    if not observations:
        raise ValueError(f"No observations found in {csv_path}")

    observations.sort(key=lambda row: row.timestamp)
    return observations


def collapse_same_day_observations(observations: list[RawObservation]) -> list[MergedObservation]:
    grouped: dict[str, list[RawObservation]] = {}
    for observation in observations:
        day_key = observation.timestamp.astimezone(timezone.utc).date().isoformat()
        grouped.setdefault(day_key, []).append(observation)

    merged: list[MergedObservation] = []
    for day_key in sorted(grouped):
        group = grouped[day_key]
        group.sort(key=lambda row: row.timestamp)
        weights = [row.valid_fraction for row in group]
        merged.append(
            MergedObservation(
                timestamp=group[0].timestamp,
                valid_fraction=_weighted_average(
                    [row.valid_fraction for row in group],
                    weights,
                ),
                ndvi_raw=_weighted_average(
                    [row.ndvi_raw for row in group],
                    weights,
                ),
                evi_raw=_weighted_average(
                    [row.evi_raw for row in group],
                    weights,
                ),
                ndmi_raw=_weighted_average(
                    [row.ndmi_raw for row in group],
                    weights,
                ),
                ndwi_raw=_weighted_average(
                    [row.ndwi_raw for row in group],
                    weights,
                ),
                source_row_count=len(group),
            )
        )

    return merged


def build_processed_observations(
    merged_observations: list[MergedObservation],
    *,
    valid_fraction_threshold: float = DEFAULT_VALID_FRACTION_THRESHOLD,
) -> list[ProcessedObservation]:
    timestamps = [observation.timestamp for observation in merged_observations]
    usable_flags = [
        observation.valid_fraction >= valid_fraction_threshold
        for observation in merged_observations
    ]
    ndvi_filled_values, ndvi_smoothed_values = build_analysis_values(
        timestamps=timestamps,
        values=[observation.ndvi_raw for observation in merged_observations],
        is_usable=usable_flags,
    )
    evi_filled_values, evi_smoothed_values = build_analysis_values(
        timestamps=timestamps,
        values=[observation.evi_raw for observation in merged_observations],
        is_usable=usable_flags,
    )
    ndmi_filled_values, ndmi_smoothed_values = build_analysis_values(
        timestamps=timestamps,
        values=[observation.ndmi_raw for observation in merged_observations],
        is_usable=usable_flags,
    )
    ndwi_filled_values, ndwi_smoothed_values = build_analysis_values(
        timestamps=timestamps,
        values=[observation.ndwi_raw for observation in merged_observations],
        is_usable=usable_flags,
    )

    processed: list[ProcessedObservation] = []
    for index, observation in enumerate(merged_observations):
        processed.append(
            ProcessedObservation(
                timestamp=observation.timestamp,
                valid_fraction=observation.valid_fraction,
                ndvi_raw=observation.ndvi_raw,
                ndvi_filled=ndvi_filled_values[index],
                ndvi_smoothed=ndvi_smoothed_values[index],
                evi_raw=observation.evi_raw,
                evi_filled=evi_filled_values[index],
                evi_smoothed=evi_smoothed_values[index],
                ndmi_raw=observation.ndmi_raw,
                ndmi_filled=ndmi_filled_values[index],
                ndmi_smoothed=ndmi_smoothed_values[index],
                ndwi_raw=observation.ndwi_raw,
                ndwi_filled=ndwi_filled_values[index],
                ndwi_smoothed=ndwi_smoothed_values[index],
                is_usable=usable_flags[index],
                source_row_count=observation.source_row_count,
            )
        )

    return processed


def _read_run_metadata(metadata_path: Path) -> dict[str, Any]:
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _derive_aoi_id(metadata: dict[str, Any], csv_path: Path) -> str:
    return str(metadata.get("aoi_id") or csv_path.parent.name)


def build_preprocess_artifacts(
    csv_path: Path,
    metadata_path: Path,
    *,
    valid_fraction_threshold: float = DEFAULT_VALID_FRACTION_THRESHOLD,
    expected_cadence_days: float = EXPECTED_CADENCE_DAYS,
) -> dict[str, Any]:
    metadata = _read_run_metadata(metadata_path)
    aoi_id = _derive_aoi_id(metadata, csv_path)
    raw_observations = load_ingestion_observations(csv_path)
    merged_observations = collapse_same_day_observations(raw_observations)
    processed_observations = build_processed_observations(
        merged_observations,
        valid_fraction_threshold=valid_fraction_threshold,
    )

    usable_timestamps = [
        observation.timestamp
        for observation in processed_observations
        if observation.is_usable
    ]
    if not usable_timestamps:
        raise ValueError(
            "No usable observations remain after applying "
            f"valid_fraction >= {valid_fraction_threshold:.2f} for AOI {aoi_id}"
        )

    gap_metrics = compute_gap_metrics(
        usable_timestamps,
        expected_cadence_days=expected_cadence_days,
    )
    gap_windows = compute_gap_windows(
        usable_timestamps,
        expected_cadence_days=expected_cadence_days,
    )
    gap_risk = classify_gap_risk(
        gap_ratio=gap_metrics["gap_ratio"],
        max_gap_days=gap_metrics["max_gap_days"],
    )

    usable_observation_count = len(usable_timestamps)
    quality_metrics = {
        "aoi_id": aoi_id,
        "total_observation_count": len(raw_observations),
        "merged_observation_count": len(merged_observations),
        "usable_observation_count": usable_observation_count,
        "dropped_observation_count": len(merged_observations) - usable_observation_count,
        "gap_ratio": gap_metrics["gap_ratio"],
        "max_gap_days": gap_metrics["max_gap_days"],
        "median_gap_days": gap_metrics["median_gap_days"],
        "long_gap_count": gap_windows["long_gap_count"],
        "long_gap_windows": gap_windows["long_gap_windows"],
        **smoothing_metadata(),
        "usable_valid_fraction_threshold": float(valid_fraction_threshold),
        "gap_risk": gap_risk["gap_risk"],
        "confidence_penalty": gap_risk["confidence_penalty"],
        "gap_risk_reason": gap_risk["gap_risk_reason"],
        "confidence_inputs": build_confidence_inputs(
            usable_observation_count=usable_observation_count,
            gap_ratio=gap_metrics["gap_ratio"],
            max_gap_days=gap_metrics["max_gap_days"],
        ),
    }

    return {
        "metadata": metadata,
        "raw_observations": raw_observations,
        "merged_observations": merged_observations,
        "processed_observations": processed_observations,
        "quality_metrics": quality_metrics,
    }


def write_preprocess_outputs(
    output_dir: Path,
    processed_observations: list[ProcessedObservation],
    quality_metrics: dict[str, Any],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "ndvi_smoothed.csv"
    metrics_path = output_dir / "quality_metrics.json"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "timestamp",
                "ndvi_raw",
                "ndvi_filled",
                "ndvi_smoothed",
                "evi_raw",
                "evi_filled",
                "evi_smoothed",
                "ndmi_raw",
                "ndmi_filled",
                "ndmi_smoothed",
                "ndwi_raw",
                "ndwi_filled",
                "ndwi_smoothed",
                "valid_fraction",
                "is_usable",
                "source_row_count",
            ]
        )
        for observation in processed_observations:
            writer.writerow(
                [
                    _isoformat_utc(observation.timestamp),
                    observation.ndvi_raw,
                    observation.ndvi_filled,
                    observation.ndvi_smoothed,
                    observation.evi_raw,
                    observation.evi_filled,
                    observation.evi_smoothed,
                    observation.ndmi_raw,
                    observation.ndmi_filled,
                    observation.ndmi_smoothed,
                    observation.ndwi_raw,
                    observation.ndwi_filled,
                    observation.ndwi_smoothed,
                    observation.valid_fraction,
                    str(observation.is_usable).lower(),
                    observation.source_row_count,
                ]
            )

    safe_write_text(metrics_path, json.dumps(quality_metrics, indent=2, sort_keys=True))

    return {
        "csv_path": csv_path,
        "metrics_path": metrics_path,
    }
