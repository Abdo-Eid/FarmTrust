"""Schema validation for the merged crop classification research dataset."""

from __future__ import annotations

import warnings

import pandas as pd

MERGED_SCHEMA: list[str] = [
    "source_dataset",
    "field_id",
    "label",
    "B01_mean",
    "B02_mean",
    "B03_mean",
    "B04_mean",
    "B05_mean",
    "B06_mean",
    "B07_mean",
    "B08_mean",
    "B8A_mean",
    "B09_mean",
    "B11_mean",
    "B12_mean",
    "NDVI_mean",
    "observation_count",
    "zone",
    "irrigation",
]

FEATURE_COLUMNS: list[str] = [
    "B01_mean",
    "B02_mean",
    "B03_mean",
    "B04_mean",
    "B05_mean",
    "B06_mean",
    "B07_mean",
    "B08_mean",
    "B8A_mean",
    "B09_mean",
    "B11_mean",
    "B12_mean",
    "NDVI_mean",
]

TARGET_COLUMN = "label"

METADATA_COLUMNS: list[str] = [
    "source_dataset",
    "field_id",
    "observation_count",
    "zone",
    "irrigation",
]

VALID_LABELS: tuple[str, ...] = (
    "Corn",
    "Potatoes",
    "Rice",
    "Sugarcane",
    "Wheat",
)

BAND_COLUMNS: tuple[str, ...] = tuple(column for column in FEATURE_COLUMNS if column.startswith("B"))
VALID_SOURCE_DATASETS: frozenset[str] = frozenset({"agrifieldnet", "morocco"})

ALIAS_SCHEMA: list[str] = [
    "field_id",
    "source",
    "target_class",
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B8A",
    "B09",
    "B11",
    "B12",
    "NDVI",
]

ALIAS_COLUMN_MAP: dict[str, str] = {
    "source": "source_dataset",
    "target_class": "label",
    "B01": "B01_mean",
    "B02": "B02_mean",
    "B03": "B03_mean",
    "B04": "B04_mean",
    "B05": "B05_mean",
    "B06": "B06_mean",
    "B07": "B07_mean",
    "B08": "B08_mean",
    "B8A": "B8A_mean",
    "B09": "B09_mean",
    "B11": "B11_mean",
    "B12": "B12_mean",
    "NDVI": "NDVI_mean",
}


def normalize_to_canonical_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Return a canonical-schema dataframe from canonical or current alias input.

    The canonical schema remains the only schema used by training and
    evaluation. This adapter exists only at the file-loading boundary for the
    current model-ready research export.
    """

    if list(df.columns) == MERGED_SCHEMA:
        return df.copy()

    if list(df.columns) != ALIAS_SCHEMA:
        raise ValueError(
            "Merged dataset columns must match MERGED_SCHEMA or the current alias schema. "
            f"Expected alias columns {ALIAS_SCHEMA}; got {list(df.columns)}."
        )

    normalized = df.rename(columns=ALIAS_COLUMN_MAP).copy()
    normalized["observation_count"] = 1
    normalized["zone"] = None
    normalized["irrigation"] = None
    normalized = normalized.loc[:, MERGED_SCHEMA].copy()

    normalized["source_dataset"] = _normalize_source_dataset_values(normalized["source_dataset"])
    normalized["label"] = _strip_label_values(normalized["label"])
    return normalized


def filter_to_valid_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Strip label whitespace and keep only rows in the current research label scope."""

    filtered = df.copy()
    filtered[TARGET_COLUMN] = _strip_label_values(filtered[TARGET_COLUMN])
    unsupported_counts = get_unsupported_label_counts(filtered)

    if unsupported_counts:
        warnings.warn(
            f"Filtered unsupported labels: {unsupported_counts}",
            RuntimeWarning,
            stacklevel=2,
        )

    valid_mask = filtered[TARGET_COLUMN].isin(VALID_LABELS)
    filtered = filtered.loc[valid_mask].copy()

    if filtered.empty:
        raise ValueError("No rows remain after filtering to VALID_LABELS.")

    return filtered


def get_unsupported_label_counts(df: pd.DataFrame) -> dict[str, int]:
    """Count labels that are outside the current research label scope."""

    labels = _strip_label_values(df[TARGET_COLUMN])
    counts = labels.map(lambda value: "<missing>" if pd.isna(value) else value).value_counts(dropna=False)
    unsupported_counts = {
        str(label): int(count)
        for label, count in counts.items()
        if label not in VALID_LABELS
    }
    return dict(sorted(unsupported_counts.items()))


def validate_schema(df: pd.DataFrame, strict_order: bool = True) -> None:
    """Validate the agreed merged crop-classification dataset schema.

    The returned model inputs are handled elsewhere. This function only verifies
    that metadata, labels, and Sentinel-2 summary features are safe to consume.
    """

    if df.empty:
        raise ValueError("Merged crop classification dataset must contain at least one row.")

    if strict_order and list(df.columns) != MERGED_SCHEMA:
        raise ValueError(
            "Merged dataset columns must exactly match MERGED_SCHEMA when strict_order=True. "
            f"Expected {MERGED_SCHEMA}; got {list(df.columns)}."
        )

    missing_columns = [column for column in MERGED_SCHEMA if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Merged dataset is missing required columns: {missing_columns}.")

    _validate_labels(df)
    feature_values = _validate_numeric_features(df)
    _warn_for_unusual_band_ranges(feature_values)
    _validate_ndvi_range(feature_values)
    _validate_source_dataset(df)
    _validate_observation_count(df)


def _validate_labels(df: pd.DataFrame) -> None:
    labels = df[TARGET_COLUMN]
    if labels.isna().any():
        raise ValueError("Target column 'label' must not contain missing values.")

    invalid_labels = sorted(set(labels.astype(str)) - set(VALID_LABELS))
    if invalid_labels:
        raise ValueError(f"Invalid label values found: {invalid_labels}. Allowed labels: {list(VALID_LABELS)}.")


def _normalize_source_dataset_values(source_values: pd.Series) -> pd.Series:
    normalized_values: list[str | None] = []
    unknown_values: set[str] = set()

    for value in source_values:
        if pd.isna(value):
            unknown_values.add("<missing>")
            normalized_values.append(None)
            continue

        raw_value = str(value).strip()
        compact_value = "".join(character for character in raw_value.lower() if character.isalnum())

        if "agrifieldnet" in compact_value or "agrfieldnet" in compact_value:
            normalized_values.append("agrifieldnet")
        elif "morocco" in compact_value:
            normalized_values.append("morocco")
        else:
            unknown_values.add(raw_value)
            normalized_values.append(raw_value)

    if unknown_values:
        raise ValueError(f"Unknown source_dataset values found during alias normalization: {sorted(unknown_values)}.")

    return pd.Series(normalized_values, index=source_values.index, name=source_values.name)


def _strip_label_values(label_values: pd.Series) -> pd.Series:
    return label_values.map(lambda value: None if pd.isna(value) else str(value).strip())


def _validate_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    feature_values = df.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    invalid_counts = {
        column: int(feature_values[column].isna().sum())
        for column in FEATURE_COLUMNS
        if feature_values[column].isna().any()
    }

    if invalid_counts:
        raise ValueError(
            "Feature columns must be numeric-compatible and non-missing. "
            f"Invalid or missing value counts: {invalid_counts}."
        )

    return feature_values


def _warn_for_unusual_band_ranges(feature_values: pd.DataFrame) -> None:
    for column in BAND_COLUMNS:
        minimum = float(feature_values[column].min())
        maximum = float(feature_values[column].max())
        if minimum < 0 or maximum > 1.5:
            warnings.warn(
                f"{column} has values outside the usual scaled reflectance-like range "
                f"[0, 1.5] (min={minimum:.4f}, max={maximum:.4f}).",
                RuntimeWarning,
                stacklevel=2,
            )


def _validate_ndvi_range(feature_values: pd.DataFrame) -> None:
    ndvi = feature_values["NDVI_mean"]
    invalid_mask = (ndvi < -1) | (ndvi > 1)
    if invalid_mask.any():
        raise ValueError(
            "NDVI_mean must be between -1 and 1. "
            f"Observed min={float(ndvi.min()):.4f}, max={float(ndvi.max()):.4f}."
        )


def _validate_source_dataset(df: pd.DataFrame) -> None:
    observed_sources = set(df["source_dataset"].dropna().astype(str))
    invalid_sources = sorted(observed_sources - VALID_SOURCE_DATASETS)
    if invalid_sources:
        raise ValueError(
            "source_dataset must only contain 'agrifieldnet' or 'morocco'. "
            f"Invalid values: {invalid_sources}."
        )


def _validate_observation_count(df: pd.DataFrame) -> None:
    present_mask = df["observation_count"].notna()
    if not present_mask.any():
        return

    observation_count = pd.to_numeric(df.loc[present_mask, "observation_count"], errors="coerce")
    if observation_count.isna().any():
        raise ValueError("observation_count must be numeric when present.")

    if (observation_count <= 0).any():
        raise ValueError("observation_count must be positive when present.")
