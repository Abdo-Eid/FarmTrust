"""Season window detection utilities."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from pathlib import Path
from typing import Any, Optional

from farmtrust_core.ingest.utils import safe_write_text


REQUIRED_PREPROCESS_COLUMNS = (
    "timestamp",
    "ndvi_smoothed",
    "evi_raw",
    "ndmi_raw",
    "ndwi_raw",
    "is_usable",
    "valid_fraction",
    "source_row_count",
)
REQUIRED_QUALITY_KEYS = (
    "aoi_id",
    "usable_observation_count",
    "gap_ratio",
    "max_gap_days",
    "gap_risk",
)

ACTIVITY_THRESHOLD = 0.18
MIN_SEASON_DURATION_DAYS = 20.0
MIN_SEASON_OBSERVATIONS = 4
GOOD_PEAK_THRESHOLD = 0.30
WEAK_PEAK_THRESHOLD = 0.24
INTERRUPTED_DROP_THRESHOLD = 0.05
GOOD_RISE_GAIN = 0.08
EVI_CONFIRMATION_MIN = 0.20
NDMI_CONFIRMATION_MIN = 0.05
NDWI_CONFIRMATION_MAX = 0.20


@dataclass(frozen=True)
class SeasonalObservation:
    timestamp: datetime
    ndvi_smoothed: float
    evi_raw: float
    ndmi_raw: float
    ndwi_raw: float
    valid_fraction: float
    source_row_count: int


@dataclass(frozen=True)
class SeasonWindow:
    season_id: str
    crossing_date: str
    start_date: str
    peak_date: str
    end_date: str
    is_open: bool
    peak_ndvi: float
    duration_days: float
    quality_label: str
    evidence_summary: str
    confirmation_level: str


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_date(value: datetime) -> str:
    return value.astimezone(timezone.utc).date().isoformat()


def _load_quality_metrics(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing_keys = [key for key in REQUIRED_QUALITY_KEYS if key not in data]
    if missing_keys:
        raise ValueError(f"Quality metrics missing required keys {missing_keys}: {path}")
    return data


def _build_season_confidence_note(quality_metrics: dict[str, Any]) -> str:
    gap_risk = str(quality_metrics["gap_risk"])
    reason = str(quality_metrics.get("gap_risk_reason", "")).strip()
    if reason:
        return f"Gap risk is {gap_risk}. {reason}"
    return f"Gap risk is {gap_risk}."


def load_preprocess_observations(csv_path: Path) -> list[SeasonalObservation]:
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {csv_path}")

        missing_columns = [column for column in REQUIRED_PREPROCESS_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                f"Preprocess CSV is missing required columns {missing_columns}: {csv_path}"
            )

        observations: list[SeasonalObservation] = []
        for row in reader:
            if row["is_usable"].strip().lower() != "true":
                continue
            if not row["ndvi_smoothed"].strip():
                continue

            observations.append(
                SeasonalObservation(
                    timestamp=_parse_timestamp(row["timestamp"]),
                    ndvi_smoothed=float(row["ndvi_smoothed"]),
                    evi_raw=float(row["evi_raw"]),
                    ndmi_raw=float(row["ndmi_raw"]),
                    ndwi_raw=float(row["ndwi_raw"]),
                    valid_fraction=float(row["valid_fraction"]),
                    source_row_count=int(row["source_row_count"]),
                )
            )

    if not observations:
        raise ValueError(f"No usable smoothed observations found in {csv_path}")

    observations.sort(key=lambda row: row.timestamp)
    return observations


def compute_activity_threshold(
    observations: list[SeasonalObservation],
    *,
    activity_threshold: float = ACTIVITY_THRESHOLD,
) -> float:
    if not observations:
        raise ValueError("Cannot compute activity threshold without observations")
    return activity_threshold


def _segment_active_periods(
    observations: list[SeasonalObservation],
    *,
    activity_threshold: float,
) -> list[tuple[int, list[SeasonalObservation]]]:
    segments: list[tuple[int, list[SeasonalObservation]]] = []
    current: list[SeasonalObservation] = []
    current_start_index: int | None = None

    for index, observation in enumerate(observations):
        if observation.ndvi_smoothed >= activity_threshold:
            if not current:
                current_start_index = index
            current.append(observation)
        elif current:
            assert current_start_index is not None
            segments.append((current_start_index, current))
            current = []
            current_start_index = None

    if current:
        assert current_start_index is not None
        segments.append((current_start_index, current))

    return segments


def _backtrack_start_index(
    observations: list[SeasonalObservation],
    crossing_index: int,
) -> int:
    start_index = crossing_index

    while start_index > 0:
        previous = observations[start_index - 1]
        current = observations[start_index]
        if previous.ndvi_smoothed <= current.ndvi_smoothed:
            start_index -= 1
            continue
        break

    return start_index


def _duration_days(observations: list[SeasonalObservation]) -> float:
    start = observations[0].timestamp
    end = observations[-1].timestamp
    return max(0.0, (end - start).total_seconds() / 86400.0)


def _max_single_step_drop(values: list[float]) -> float:
    drops = [left - right for left, right in zip(values[:-1], values[1:]) if right < left]
    if not drops:
        return 0.0
    return max(drops)


def _label_quality(
    segment: list[SeasonalObservation],
    *,
    is_open: bool = False,
) -> tuple[str, str, str]:
    values = [row.ndvi_smoothed for row in segment]
    peak_row = max(segment, key=lambda row: row.ndvi_smoothed)
    peak_ndvi = peak_row.ndvi_smoothed
    duration_days = _duration_days(segment)
    rise_gain = peak_ndvi - segment[0].ndvi_smoothed
    max_drop = _max_single_step_drop(values)

    if peak_ndvi < WEAK_PEAK_THRESHOLD or duration_days < MIN_SEASON_DURATION_DAYS:
        label = (
            "weak",
            f"Weak season: peak_ndvi={peak_ndvi:.3f}, duration_days={duration_days:.1f}.",
        )
        quality_label, evidence_summary = _append_open_note(label, is_open=is_open)
        return quality_label, evidence_summary, "weak"

    if max_drop >= INTERRUPTED_DROP_THRESHOLD:
        label = (
            "interrupted",
            f"Interrupted season: peak_ndvi={peak_ndvi:.3f}, max_drop={max_drop:.3f}.",
        )
        quality_label, evidence_summary = _append_open_note(label, is_open=is_open)
        return quality_label, evidence_summary, "moderate"

    if peak_ndvi >= GOOD_PEAK_THRESHOLD and rise_gain >= GOOD_RISE_GAIN:
        label = (
            "good",
            f"Good season: peak_ndvi={peak_ndvi:.3f}, rise_gain={rise_gain:.3f}.",
        )
        quality_label, evidence_summary = _append_open_note(label, is_open=is_open)
        return quality_label, evidence_summary, "strong"

    label = (
        "weak",
        f"Weak season: peak_ndvi={peak_ndvi:.3f}, rise_gain={rise_gain:.3f}.",
    )
    quality_label, evidence_summary = _append_open_note(label, is_open=is_open)
    return quality_label, evidence_summary, "weak"


def _append_open_note(
    label: tuple[str, str],
    *,
    is_open: bool,
) -> tuple[str, str]:
    if not is_open:
        return label

    quality_label, evidence_summary = label
    return quality_label, f"{evidence_summary[:-1]} Still active at end of available series."


def _compute_multi_index_confirmation(segment: list[SeasonalObservation]) -> tuple[str, str]:
    evi_peak = max(row.evi_raw for row in segment)
    ndmi_median = float(median(row.ndmi_raw for row in segment))
    ndwi_median = float(median(row.ndwi_raw for row in segment))

    checks = [
        evi_peak >= EVI_CONFIRMATION_MIN,
        ndmi_median >= NDMI_CONFIRMATION_MIN,
        ndwi_median <= NDWI_CONFIRMATION_MAX,
    ]
    support_count = sum(1 for flag in checks if flag)
    if support_count == 3:
        level = "strong"
    elif support_count == 2:
        level = "moderate"
    else:
        level = "weak"

    evidence = (
        f"Multi-index confirmation={level} "
        f"(evi_peak={evi_peak:.3f}, ndmi_median={ndmi_median:.3f}, ndwi_median={ndwi_median:.3f})."
    )
    return level, evidence


def _apply_confirmation_adjustment(
    *,
    quality_label: str,
    base_evidence: str,
    base_level: str,
    confirmation_level: str,
    confirmation_evidence: str,
) -> tuple[str, str]:
    adjusted_label = quality_label
    if quality_label == "good" and confirmation_level == "weak":
        adjusted_label = "interrupted"
    elif quality_label == "interrupted" and confirmation_level == "strong" and base_level == "moderate":
        adjusted_label = "good"

    return adjusted_label, f"{base_evidence} {confirmation_evidence}"


def _is_left_edge_partial_tail(
    observations: list[SeasonalObservation],
    crossing_index: int,
    season_observations: list[SeasonalObservation],
) -> bool:
    if crossing_index != 0:
        return False
    if not season_observations:
        return False

    peak_row = max(season_observations, key=lambda row: row.ndvi_smoothed)
    first_row = season_observations[0]
    return peak_row.timestamp == first_row.timestamp


def detect_season_windows(
    observations: list[SeasonalObservation],
    *,
    activity_threshold: float = ACTIVITY_THRESHOLD,
) -> list[SeasonWindow]:
    seasons: list[SeasonWindow] = []
    activity_threshold = compute_activity_threshold(
        observations,
        activity_threshold=activity_threshold,
    )
    segments = _segment_active_periods(observations, activity_threshold=activity_threshold)

    for crossing_index, segment in segments:
        start_index = _backtrack_start_index(observations, crossing_index)
        end_index = crossing_index + len(segment) - 1
        season_observations = observations[start_index : end_index + 1]
        is_open = end_index == len(observations) - 1

        if _is_left_edge_partial_tail(observations, crossing_index, season_observations):
            continue

        duration_days = _duration_days(season_observations)
        if len(segment) < MIN_SEASON_OBSERVATIONS:
            continue
        if duration_days < MIN_SEASON_DURATION_DAYS:
            continue

        peak_row = max(season_observations, key=lambda row: row.ndvi_smoothed)
        quality_label, evidence_summary, base_level = _label_quality(
            season_observations,
            is_open=is_open,
        )
        confirmation_level, confirmation_evidence = _compute_multi_index_confirmation(season_observations)
        quality_label, evidence_summary = _apply_confirmation_adjustment(
            quality_label=quality_label,
            base_evidence=evidence_summary,
            base_level=base_level,
            confirmation_level=confirmation_level,
            confirmation_evidence=confirmation_evidence,
        )

        seasons.append(
            SeasonWindow(
                season_id=f"season_{len(seasons) + 1:02d}",
                crossing_date=_iso_date(observations[crossing_index].timestamp),
                start_date=_iso_date(season_observations[0].timestamp),
                peak_date=_iso_date(peak_row.timestamp),
                end_date=_iso_date(season_observations[-1].timestamp),
                is_open=is_open,
                peak_ndvi=round(peak_row.ndvi_smoothed, 6),
                duration_days=round(duration_days, 2),
                quality_label=quality_label,
                evidence_summary=evidence_summary,
                confirmation_level=confirmation_level,
            )
        )

    return seasons


def build_season_payload(
    smoothed_csv_path: Path,
    quality_metrics_path: Path,
) -> dict[str, Any]:
    quality_metrics = _load_quality_metrics(quality_metrics_path)
    observations = load_preprocess_observations(smoothed_csv_path)
    seasons = detect_season_windows(observations)
    season_confidence_note = _build_season_confidence_note(quality_metrics)

    if not seasons:
        raise ValueError(
            "No season windows detected from the current preprocessing output. "
            "Adjust the detector or inspect the NDVI series."
        )

    return {
        "aoi_id": quality_metrics["aoi_id"],
        "season_count": len(seasons),
        "gap_risk": quality_metrics["gap_risk"],
        "seasons": [
            {
                "season_id": season.season_id,
                "crossing_date": season.crossing_date,
                "start_date": season.start_date,
                "peak_date": season.peak_date,
                "end_date": season.end_date,
                "is_open": season.is_open,
                "peak_ndvi": season.peak_ndvi,
                "duration_days": season.duration_days,
                "quality_label": season.quality_label,
                "evidence_summary": season.evidence_summary,
                "confirmation_level": season.confirmation_level,
                "season_confidence_note": season_confidence_note,
            }
            for season in seasons
        ],
    }


def write_season_payload(output_dir: Path, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "season_windows.json"
    safe_write_text(output_path, json.dumps(payload, indent=2, sort_keys=True))
    return output_path
