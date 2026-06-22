"""
Builds agricultural-cycle input tensors from existing preprocessing artifacts.

Reads:
    data/preprocess/<aoi_id>/ndvi_smoothed.csv
    data/preprocess/<aoi_id>/quality_metrics.json
    data/<aoi_id>/run_metadata.json
    configs/egypt_agricultural_cycles.yaml
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from farmtrust_core.ml.calendar import load_egypt_cycles


logger = logging.getLogger(__name__)

MAX_SEQ_LEN = 64
FEATURE_NAMES = [
    "ndvi",
    "evi",
    "ndmi",
    "ndwi",
    "bare_soil_proxy",
    "valid_fraction",
    "doy_sin",
    "doy_cos",
    "observation_gap_days",
    "is_usable_float",
]

FEATURE_COLUMNS = [
    "ndvi_smoothed",
    "evi_smoothed",
    "ndmi_smoothed",
    "ndwi_smoothed",
    "bare_soil_proxy",
    "valid_fraction",
    "doy_sin",
    "doy_cos",
    "observation_gap_days",
    "is_usable_float",
]


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class SequenceBuilder:
    def __init__(
        self,
        data_root: str | Path = "data",
        calendar_path: str | Path = "configs/egypt_agricultural_cycles.yaml",
    ) -> None:
        self.data_root = Path(data_root)
        self.calendar_path = Path(calendar_path)

    def build(self, aoi_id: str) -> dict[str, Any]:
        """
        Build one padded sequence per Egypt agricultural cycle.

        The AOI history is split by cycle first. Padding and truncation are then
        applied inside each cycle, never across the full AOI history.
        """
        preprocess_dir = self.data_root / "preprocess" / aoi_id
        smoothed_path = preprocess_dir / "ndvi_smoothed.csv"
        quality_path = preprocess_dir / "quality_metrics.json"
        metadata_path = self.data_root / aoi_id / "run_metadata.json"

        for path in (smoothed_path, quality_path, metadata_path):
            if not path.exists():
                raise FileNotFoundError(f"Missing required ML input: {path}")

        quality_metrics = _read_json(quality_path)
        run_metadata = _read_json(metadata_path)

        df = pd.read_csv(smoothed_path, parse_dates=["timestamp"])
        missing = [column for column in ("timestamp", *FEATURE_COLUMNS[:4], "valid_fraction", "is_usable") if column not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns {missing}: {smoothed_path}")

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df[df["is_usable"].map(_is_true)].copy()
        df = df.dropna(subset=FEATURE_COLUMNS[:4])
        df = df.sort_values("timestamp").reset_index(drop=True)
        if df.empty:
            raise ValueError(f"No usable observations for {aoi_id}")

        df["doy"] = df["timestamp"].dt.dayofyear
        df["doy_sin"] = np.sin(2 * np.pi * df["doy"] / 365.0)
        df["doy_cos"] = np.cos(2 * np.pi * df["doy"] / 365.0)
        df["bare_soil_proxy"] = (df["ndmi_smoothed"] - df["ndvi_smoothed"]) / (
            df["ndmi_smoothed"] + df["ndvi_smoothed"] + 1e-6
        )
        df["observation_gap_days"] = df["timestamp"].diff().dt.days.fillna(0).clip(0, 90)
        df["is_usable_float"] = 1.0

        cycles = load_egypt_cycles(self.calendar_path, df["timestamp"].min(), df["timestamp"].max())
        cycle_features: list[np.ndarray] = []
        cycle_masks: list[np.ndarray] = []
        cycle_doy: list[np.ndarray] = []
        cycle_timestamps: list[list[str]] = []
        cycle_metadata: list[dict[str, Any]] = []

        for cycle in cycles:
            start = pd.Timestamp(cycle["start_date"])
            end = pd.Timestamp(cycle["end_date"])
            cdf = df[(df["timestamp"] >= start) & (df["timestamp"] <= end)].copy()
            if cdf.empty:
                continue

            raw = cdf[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
            raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
            doy_raw = cdf["doy"].to_numpy(dtype=np.int16)
            ts_raw = cdf["timestamp"].dt.strftime("%Y-%m-%d").tolist()

            if len(raw) >= MAX_SEQ_LEN:
                raw = raw[-MAX_SEQ_LEN:]
                doy_raw = doy_raw[-MAX_SEQ_LEN:]
                ts_raw = ts_raw[-MAX_SEQ_LEN:]
                mask = np.ones(MAX_SEQ_LEN, dtype=bool)
            else:
                pad = MAX_SEQ_LEN - len(raw)
                raw = np.vstack([np.zeros((pad, len(FEATURE_NAMES)), dtype=np.float32), raw])
                doy_raw = np.concatenate([np.zeros(pad, dtype=np.int16), doy_raw])
                ts_raw = [""] * pad + ts_raw
                mask = np.concatenate([np.zeros(pad, dtype=bool), np.ones(len(cdf), dtype=bool)])

            metadata = {
                "cycle_id": cycle["cycle_id"],
                "expected_window": cycle["expected_window"],
                "observation_count": int(len(cdf)),
                "aoi_area_ha": run_metadata.get("area_ha"),
                "gap_risk": quality_metrics.get("gap_risk"),
            }
            cycle_features.append(raw)
            cycle_masks.append(mask)
            cycle_doy.append(doy_raw)
            cycle_timestamps.append(ts_raw)
            cycle_metadata.append(metadata)

        if not cycle_features:
            raise ValueError(f"No agricultural cycles contained usable observations for {aoi_id}")

        return {
            "features": np.stack(cycle_features).astype(np.float32),
            "attention_mask": np.stack(cycle_masks),
            "doy": np.stack(cycle_doy).astype(np.int16),
            "timestamps": cycle_timestamps,
            "cycle_metadata": cycle_metadata,
            "feature_names": FEATURE_NAMES,
            "aoi_id": aoi_id,
            "usable_count": int(len(df)),
        }
