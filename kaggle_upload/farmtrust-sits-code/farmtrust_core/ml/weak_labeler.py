"""
Generates weak per-observation labels from existing pipeline artifacts.

Label encoding:
    0 = active, 1 = bare, 2 = sparse, 3 = uncertain, -1 = no_label
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


logger = logging.getLogger(__name__)

LOW_VEGETATION_FLOOR = 0.18
LABEL_NAMES = {
    0: "active",
    1: "bare",
    2: "sparse",
    3: "uncertain",
    -1: "no_label",
}


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


@dataclass(frozen=True)
class LabelWindow:
    start: datetime
    end: datetime
    label: int
    confidence: float

    def contains(self, timestamp: datetime) -> bool:
        return self.start <= timestamp <= self.end


class WeakLabeler:
    def __init__(self, data_root: str | Path = "data") -> None:
        self.data_root = Path(data_root)
        self.output_path = self.data_root / "ml" / "labels" / "weak_labels.csv"

    def generate(self, aoi_id: str) -> pd.DataFrame:
        smoothed_path = self.data_root / "preprocess" / aoi_id / "ndvi_smoothed.csv"
        quality_path = self.data_root / "preprocess" / aoi_id / "quality_metrics.json"
        seasons_path = self.data_root / "seasonal" / aoi_id / "season_windows.json"

        for path in (smoothed_path, quality_path, seasons_path):
            if not path.exists():
                raise FileNotFoundError(f"Missing required weak-label input: {path}")

        df = pd.read_csv(smoothed_path, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df[df["is_usable"].map(_is_true)].copy()
        df = df.sort_values("timestamp").reset_index(drop=True)

        quality_metrics = json.loads(quality_path.read_text(encoding="utf-8"))
        season_payload = json.loads(seasons_path.read_text(encoding="utf-8"))
        windows = self._load_activity_windows(season_payload)
        long_gap_windows = self._load_gap_windows(quality_metrics)

        rows: list[dict[str, Any]] = []
        for row in df.itertuples(index=False):
            timestamp = row.timestamp.to_pydatetime().astimezone(timezone.utc)
            label, confidence = self._assign_label(row, timestamp, windows, long_gap_windows)
            rows.append(
                {
                    "aoi_id": aoi_id,
                    "timestamp": timestamp.date().isoformat(),
                    "label": label,
                    "label_name": LABEL_NAMES[label],
                    "weak_confidence": confidence,
                }
            )

        labels = pd.DataFrame(rows, columns=["aoi_id", "timestamp", "label", "label_name", "weak_confidence"])
        self._append_dedup(labels)
        counts = Counter(labels["label_name"].tolist())
        logger.info("Weak labels for %s: %s", aoi_id, dict(sorted(counts.items())))
        return labels

    def _load_activity_windows(self, payload: dict[str, Any]) -> list[LabelWindow]:
        windows: list[LabelWindow] = []
        for item in payload.get("seasons", payload.get("season_windows", [])):
            start_value = item.get("start_date") or item.get("start_timestamp")
            end_value = item.get("end_date") or item.get("end_timestamp")
            if not start_value or not end_value:
                continue
            quality_label = str(item.get("quality_label", "")).lower()
            confirmation = str(item.get("confirmation_level", "")).lower()
            if quality_label == "good" and confirmation in {"strong", "moderate"}:
                windows.append(LabelWindow(_parse_time(start_value), _parse_time(end_value), 0, 0.80))
            elif quality_label == "weak" or confirmation == "weak":
                windows.append(LabelWindow(_parse_time(start_value), _parse_time(end_value), 2, 0.60))
        return windows

    def _load_gap_windows(self, quality_metrics: dict[str, Any]) -> list[LabelWindow]:
        windows: list[LabelWindow] = []
        for item in quality_metrics.get("long_gap_windows", []):
            start_value = item.get("start_timestamp") or item.get("start_date")
            end_value = item.get("end_timestamp") or item.get("end_date")
            if start_value and end_value:
                windows.append(LabelWindow(_parse_time(start_value), _parse_time(end_value), 3, 0.40))
        return windows

    def _assign_label(
        self,
        row: Any,
        timestamp: datetime,
        windows: list[LabelWindow],
        long_gap_windows: list[LabelWindow],
    ) -> tuple[int, float]:
        matching = [window for window in windows if window.contains(timestamp)]
        if any(window.label == 0 for window in matching):
            return 0, 0.80
        if any(window.label == 2 for window in matching):
            return 2, 0.60
        if (
            float(row.ndvi_smoothed) < LOW_VEGETATION_FLOOR
            and not matching
            and float(row.valid_fraction) >= 0.90
        ):
            return 1, 0.75
        if any(window.contains(timestamp) for window in long_gap_windows):
            return 3, 0.40
        return 3, 0.50

    def _append_dedup(self, labels: pd.DataFrame) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.output_path.exists():
            existing = pd.read_csv(self.output_path)
            labels = pd.concat([existing, labels], ignore_index=True)
        labels = labels.drop_duplicates(subset=["aoi_id", "timestamp"], keep="last")
        labels = labels.sort_values(["aoi_id", "timestamp"]).reset_index(drop=True)
        labels.to_csv(self.output_path, index=False)
