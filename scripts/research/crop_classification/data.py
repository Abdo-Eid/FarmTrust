"""Data loading and split helpers for the crop classification research baseline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schema import (
    FEATURE_COLUMNS,
    METADATA_COLUMNS,
    TARGET_COLUMN,
    filter_to_valid_labels,
    normalize_to_canonical_schema,
    validate_schema,
)


def load_merged_dataset(path: Path, *, filter_invalid_labels: bool = True) -> pd.DataFrame:
    """Load the merged crop-classification table from a local research path."""

    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError("Merged dataset not found. Build or place the merged dataset first.")

    suffix = dataset_path.suffix.lower()
    if suffix == ".csv":
        df = normalize_to_canonical_schema(pd.read_csv(dataset_path))
    elif suffix in {".xlsx", ".xls"}:
        df = normalize_to_canonical_schema(pd.read_excel(dataset_path))
    else:
        raise ValueError("Unsupported merged dataset format. Expected .csv, .xlsx, or .xls.")

    if filter_invalid_labels:
        return filter_to_valid_labels(df)
    return df


def validate_and_prepare_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Validate the dataset and return model features plus labels.

    Metadata columns are deliberately excluded from `X` because source, field ID,
    geography, irrigation, and observation count can leak collection or context
    shortcuts that do not represent crop spectral behavior.
    """

    validate_schema(df)
    X = df.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="raise").copy()
    y = df[TARGET_COLUMN].astype(str).copy()
    return X, y


def split_dataset(
    df: pd.DataFrame,
    test_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.DataFrame]:
    """Split features, labels, and evaluation metadata with label stratification."""

    try:
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for dataset splitting. Run `uv sync --extra ml`.") from exc

    X, y = validate_and_prepare_dataset(df)
    metadata = _metadata_frame(df)

    X_train, X_test, y_train, y_test, metadata_train, metadata_test = train_test_split(
        X,
        y,
        metadata,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    return (
        X_train.reset_index(drop=True),
        X_test.reset_index(drop=True),
        y_train.reset_index(drop=True),
        y_test.reset_index(drop=True),
        metadata_train.reset_index(drop=True),
        metadata_test.reset_index(drop=True),
    )


def _metadata_frame(df: pd.DataFrame) -> pd.DataFrame:
    metadata_columns = [column for column in [*METADATA_COLUMNS, TARGET_COLUMN] if column in df.columns]
    return df.loc[:, metadata_columns].copy()
