"""
Convert EuroCropsML Latvia 2021 data to FarmTrust SITS-BERT .npz format.

Usage:
  python scripts/convert_eurocrops.py \
    --input-dir data/eurocrops/ \
    --output data/eurocrops/eurocrops_transfer.npz \
    --max-parcels 5000
"""

from __future__ import annotations

import argparse
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

MAX_SEQ_LEN = 64
SEED = 42
FEATURE_COUNT = 10

LABEL_TO_ID = {
    "active": 0,
    "bare": 1,
    "sparse": 2,
    "uncertain": 3,
}
ID_TO_LABEL = {value: key for key, value in LABEL_TO_ID.items()}

# EuroCropsML Sentinel-2 raw band order from eurocropsml.acquisition.config.S2_BANDS.
BAND_INDEX = {
    "B02": 1,
    "B03": 2,
    "B04": 3,
    "B08": 7,
    "B11": 11,
}


def _find_latvia_parquet(input_dir: Path) -> Path:
    candidates = sorted(input_dir.rglob("Latvia.parquet"))
    if not candidates:
        candidates = [
            path
            for path in sorted(input_dir.rglob("*.parquet"))
            if "label" not in path.name.lower()
        ]
    if not candidates:
        raise FileNotFoundError(f"No EuroCrops observation parquet found under {input_dir}")
    return candidates[0]


def _date_columns(columns: list[str]) -> list[str]:
    return [col for col in columns if re.match(r"^\d{4}-\d{2}-\d{2}$", str(col))]


def _label_name(row: pd.Series) -> str:
    if "EC_hcat_n" in row and pd.notna(row["EC_hcat_n"]):
        return str(row["EC_hcat_n"]).lower()
    if "crop_label" in row and pd.notna(row["crop_label"]):
        return str(row["crop_label"]).lower()
    if "EC_hcat_c" in row and pd.notna(row["EC_hcat_c"]):
        return str(row["EC_hcat_c"]).lower()
    return ""


def _map_label(row: pd.Series) -> int:
    name = _label_name(row)
    if any(token in name for token in ("wheat", "triticale", "grassland", "meadow")):
        return LABEL_TO_ID["active"]
    if any(token in name for token in ("grass", "clover", "alfalfa", "lucerne", "berseem")):
        return LABEL_TO_ID["active"]
    if any(token in name for token in ("fallow", "bare", "set_aside", "set-aside")):
        return LABEL_TO_ID["bare"]
    if any(token in name for token in ("catch_crop", "cover_crop", "green_manure")):
        return LABEL_TO_ID["sparse"]
    return LABEL_TO_ID["uncertain"]


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) < 1e-6:
        return 0.0
    value = numerator / denominator
    if not np.isfinite(value):
        return 0.0
    return float(value)


def _features_from_observation(observation: Any, timestamp: pd.Timestamp, gap_days: int) -> list[float] | None:
    if observation is None:
        return None

    values = np.asarray(observation, dtype=np.float32)
    if values.ndim != 1 or values.size <= max(BAND_INDEX.values()):
        return None
    if np.all(values == -999):
        return None

    reflectance = values / 10000.0
    blue = float(reflectance[BAND_INDEX["B02"]])
    green = float(reflectance[BAND_INDEX["B03"]])
    red = float(reflectance[BAND_INDEX["B04"]])
    nir = float(reflectance[BAND_INDEX["B08"]])
    swir = float(reflectance[BAND_INDEX["B11"]])

    ndvi = _safe_ratio(nir - red, nir + red)
    evi = _safe_ratio(2.5 * (nir - red), nir + 6.0 * red - 7.5 * blue + 1.0)
    ndmi = _safe_ratio(nir - swir, nir + swir)
    ndwi = _safe_ratio(green - nir, green + nir)
    bare_soil_proxy = _safe_ratio(ndmi - ndvi, ndmi + ndvi + 1e-6)

    doy_value = int(timestamp.dayofyear)
    radians = 2.0 * math.pi * doy_value / 365.0
    return [
        ndvi,
        evi,
        ndmi,
        ndwi,
        bare_soil_proxy,
        1.0,
        math.sin(radians),
        math.cos(radians),
        float(gap_days),
        1.0,
    ]


def _convert_row(row: pd.Series, date_cols: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    observations: list[list[float]] = []
    doys: list[int] = []
    last_timestamp: pd.Timestamp | None = None

    for col in date_cols:
        timestamp = pd.Timestamp(col)
        gap_days = 0 if last_timestamp is None else int((timestamp - last_timestamp).days)
        features = _features_from_observation(row[col], timestamp, gap_days)
        if features is None:
            continue
        observations.append(features)
        doys.append(int(timestamp.dayofyear))
        last_timestamp = timestamp

    if len(observations) < 5:
        return None

    obs_array = np.asarray(observations[-MAX_SEQ_LEN:], dtype=np.float32)
    doy_array = np.asarray(doys[-MAX_SEQ_LEN:], dtype=np.int16)
    length = obs_array.shape[0]
    pad = MAX_SEQ_LEN - length

    features = np.zeros((MAX_SEQ_LEN, FEATURE_COUNT), dtype=np.float32)
    attention_mask = np.zeros(MAX_SEQ_LEN, dtype=bool)
    doy = np.zeros(MAX_SEQ_LEN, dtype=np.int16)

    features[pad:] = obs_array
    attention_mask[pad:] = True
    doy[pad:] = doy_array
    return features, attention_mask, doy


def convert(input_dir: Path, output_path: Path, max_parcels: int) -> None:
    parquet_path = _find_latvia_parquet(input_dir)
    parquet_file = pq.ParquetFile(parquet_path)
    columns = parquet_file.schema_arrow.names
    date_cols = _date_columns(columns)
    if not date_cols:
        raise ValueError(f"No daily observation columns found in {parquet_path}")

    rng = np.random.default_rng(SEED)
    features_out: list[np.ndarray] = []
    masks_out: list[np.ndarray] = []
    doy_out: list[np.ndarray] = []
    labels_out: list[np.ndarray] = []
    parcel_ids: list[str] = []
    sequence_lengths: list[int] = []
    skipped_too_short = 0

    for batch in parquet_file.iter_batches(batch_size=512):
        df = batch.to_pandas()
        order = rng.permutation(len(df))
        for index in order:
            row = df.iloc[int(index)]
            converted = _convert_row(row, date_cols)
            if converted is None:
                skipped_too_short += 1
                continue

            features, attention_mask, doy = converted
            label = _map_label(row)
            labels = np.full(MAX_SEQ_LEN, label, dtype=np.int8)

            features_out.append(features)
            masks_out.append(attention_mask)
            doy_out.append(doy)
            labels_out.append(labels)
            parcel_ids.append(str(row.get("parcel_id", len(parcel_ids))))
            sequence_lengths.append(int(attention_mask.sum()))

            if len(features_out) >= max_parcels:
                break
        if len(features_out) >= max_parcels:
            break

    if not features_out:
        raise ValueError("No EuroCrops parcels converted")

    features_array = np.stack(features_out).astype(np.float32)
    masks_array = np.stack(masks_out).astype(bool)
    doy_array = np.stack(doy_out).astype(np.int16)
    labels_array = np.stack(labels_out).astype(np.int8)
    parcel_ids_array = np.asarray(parcel_ids, dtype=object)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        features=features_array,
        attention_mask=masks_array,
        doy=doy_array,
        labels=labels_array,
        parcel_ids=parcel_ids_array,
    )

    label_distribution = Counter(int(row[0]) for row in labels_array)
    named_distribution = {
        ID_TO_LABEL[label_id]: count for label_id, count in sorted(label_distribution.items())
    }
    print(f"Total parcels converted: {features_array.shape[0]}")
    print(f"Label distribution: {named_distribution}")
    print(f"Skipped (too short < 5 obs): {skipped_too_short}")
    print(f"Mean sequence length before padding: {float(np.mean(sequence_lengths)):.2f}")
    print(f"Output file size: {output_path.stat().st_size / 1_000_000:.2f} MB")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert EuroCropsML Latvia to FarmTrust SITS .npz.")
    parser.add_argument("--input-dir", default="data/eurocrops/", help="EuroCrops input directory")
    parser.add_argument("--output", default="data/eurocrops/eurocrops_transfer.npz", help="Output .npz")
    parser.add_argument("--max-parcels", type=int, default=5000, help="Maximum parcels to convert")
    args = parser.parse_args()

    convert(Path(args.input_dir), Path(args.output), args.max_parcels)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
