"""Generate the figures used by docs/session.md.

Run from the repository root:

    uv run python docs/assets/generate_session_images.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from farmtrust_core.preprocess.pipeline import build_preprocess_artifacts
from farmtrust_core.seasonal.seasons import (
    SeasonalObservation,
    build_activity_signal_model,
    detect_activity_windows,
)


AOI_ID = "land-5f9a0269b2ea4f96b0a120098b6c65c4"
ASSET_DIR = Path(__file__).resolve().parent


def _load_artifacts() -> dict[str, object]:
    data_dir = REPO_ROOT / "data" / AOI_ID
    return build_preprocess_artifacts(
        csv_path=data_dir / "indices_timeseries.csv",
        metadata_path=data_dir / "run_metadata.json",
    )


def _seasonal_observations(processed_observations: list[object]) -> list[SeasonalObservation]:
    observations: list[SeasonalObservation] = []
    for row in processed_observations:
        if not row.is_usable:
            continue
        if row.ndvi_smoothed is None:
            continue
        if row.evi_smoothed is None or row.ndmi_smoothed is None or row.ndwi_smoothed is None:
            continue
        observations.append(
            SeasonalObservation(
                timestamp=row.timestamp,
                ndvi_smoothed=float(row.ndvi_smoothed),
                evi_smoothed=float(row.evi_smoothed),
                ndmi_smoothed=float(row.ndmi_smoothed),
                ndwi_smoothed=float(row.ndwi_smoothed),
                valid_fraction=float(row.valid_fraction),
                source_row_count=int(row.source_row_count),
            )
        )
    return observations


def generate_smoothing_figure(artifacts: dict[str, object]) -> Path:
    processed = artifacts["processed_observations"]
    output_path = ASSET_DIR / "session-ses_1244_smoothing.png"

    dates = [row.timestamp for row in processed]
    raw_ndvi = [row.ndvi_raw for row in processed]
    usable_dates = [row.timestamp for row in processed if row.is_usable]
    usable_raw = [row.ndvi_raw for row in processed if row.is_usable]
    smoothed_dates = [row.timestamp for row in processed if row.ndvi_smoothed is not None]
    smoothed_ndvi = [row.ndvi_smoothed for row in processed if row.ndvi_smoothed is not None]
    dropped_dates = [row.timestamp for row in processed if not row.is_usable]
    dropped_raw = [row.ndvi_raw for row in processed if not row.is_usable]

    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.plot(dates, raw_ndvi, color="#9ca3af", linewidth=1.2, alpha=0.6, label="Merged raw NDVI")
    ax.scatter(usable_dates, usable_raw, color="#2563eb", s=28, label="Usable raw observations")
    if dropped_dates:
        ax.scatter(dropped_dates, dropped_raw, color="#ef4444", marker="x", s=42, label="Non-usable observations")
    ax.plot(smoothed_dates, smoothed_ndvi, color="#16a34a", linewidth=2.6, marker="o", markersize=4, label="Gap-aware smoothed NDVI")

    ax.set_title("NDVI Before and After Gap-Aware Smoothing", fontsize=15, weight="bold")
    ax.set_ylabel("NDVI")
    ax.set_xlabel("Observation date")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def _timestamp_for_date(observations: list[SeasonalObservation], date_text: str):
    return next(row.timestamp for row in observations if row.timestamp.date().isoformat() == date_text)


def _observation_for_date(observations: list[SeasonalObservation], date_text: str) -> SeasonalObservation:
    return next(row for row in observations if row.timestamp.date().isoformat() == date_text)


def generate_activity_detection_figure(artifacts: dict[str, object]) -> Path:
    processed = artifacts["processed_observations"]
    quality_metrics = artifacts["quality_metrics"]
    output_path = ASSET_DIR / "session-ses_1244_season_detection.png"

    observations = _seasonal_observations(processed)
    confirmed, borderline = detect_activity_windows(
        observations,
        long_gap_windows=quality_metrics.get("long_gap_windows", []),
    )
    model = build_activity_signal_model(observations)

    dates = [row.timestamp for row in observations]
    ndvi = [row.ndvi_smoothed for row in observations]

    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.plot(dates, ndvi, color="#1f77b4", linewidth=2.4, marker="o", markersize=4, label="Smoothed usable NDVI")
    ax.plot(dates, model.low_envelope, color="#6b7280", linewidth=1.8, linestyle="--", label="Local low envelope (p20)")

    for index, window in enumerate(confirmed):
        start = _timestamp_for_date(observations, window.start_date)
        end = _timestamp_for_date(observations, window.end_date)
        peak = _observation_for_date(observations, window.peak_date)
        ax.axvspan(start, end, color="#22c55e", alpha=0.18, label="Confirmed activity window" if index == 0 else None)
        ax.scatter([peak.timestamp], [peak.ndvi_smoothed], color="#15803d", s=80, zorder=5)
        ax.annotate(
            f"{window.lifecycle_status}\nratio={window.prominence_to_noise_ratio:.2f}",
            xy=(peak.timestamp, peak.ndvi_smoothed),
            xytext=(0, 30),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color="#14532d",
            arrowprops={"arrowstyle": "->", "color": "#15803d", "lw": 1},
        )

    for index, window in enumerate(borderline):
        start = _timestamp_for_date(observations, window.start_date)
        end = _timestamp_for_date(observations, window.end_date)
        peak = _observation_for_date(observations, window.peak_date)
        ax.axvspan(start, end, color="#f97316", alpha=0.18, label="Borderline activity candidate" if index == 0 else None)
        ax.scatter([peak.timestamp], [peak.ndvi_smoothed], color="#c2410c", s=80, zorder=5)
        ax.annotate(
            f"borderline\nratio={window.prominence_to_noise_ratio:.2f}",
            xy=(peak.timestamp, peak.ndvi_smoothed),
            xytext=(0, 30),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color="#7c2d12",
            arrowprops={"arrowstyle": "->", "color": "#c2410c", "lw": 1},
        )

    if not confirmed and not borderline:
        best_index = max(range(len(ndvi)), key=lambda index: ndvi[index])
        ax.scatter([dates[best_index]], [ndvi[best_index]], color="#9333ea", s=90, zorder=5, label="Highest observed NDVI")
        ax.annotate(
            "No confirmed or borderline\nactivity window detected",
            xy=(dates[best_index], ndvi[best_index]),
            xytext=(0, 35),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color="#581c87",
            arrowprops={"arrowstyle": "->", "color": "#9333ea", "lw": 1},
        )

    summary = (
        f"Adaptive detector: confirmed={len(confirmed)}, borderline={len(borderline)}, "
        f"noise_floor={model.noise_floor_ndvi:.3f}, usable_observations={len(observations)}"
    )
    ax.set_title("Vegetation Activity Detection: Adaptive Prominence vs Field Noise", fontsize=15, weight="bold")
    ax.text(
        0.01,
        0.98,
        summary,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=10,
        bbox={"facecolor": "white", "edgecolor": "#d1d5db", "alpha": 0.9, "boxstyle": "round,pad=0.35"},
    )
    ax.set_ylabel("Smoothed NDVI")
    ax.set_xlabel("Observation date")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def main() -> int:
    artifacts = _load_artifacts()
    smoothing_path = generate_smoothing_figure(artifacts)
    detection_path = generate_activity_detection_figure(artifacts)
    print(f"Wrote {smoothing_path}")
    print(f"Wrote {detection_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
