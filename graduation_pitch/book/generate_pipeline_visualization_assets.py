"""Generate book-ready static figures from pipeline visualization HTML data."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
ASSETS_DIR = BASE_DIR / "assets"

DATA_RE = re.compile(
    r'<script id="data" type="application/json">(.*?)</script>',
    re.DOTALL,
)


def load_visualization_data(html_path: Path) -> dict:
    text = html_path.read_text(encoding="utf-8")
    match = DATA_RE.search(text)
    if not match:
        raise ValueError(f"No embedded visualization data found in {html_path}")
    return json.loads(match.group(1))


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def daily_dates(start: str, count: int) -> list[datetime]:
    first = parse_date(start)
    return [first + timedelta(days=i) for i in range(count)]


def plot_short_window_diagnostic() -> None:
    html_path = (
        PROJECT_DIR
        / "outputs"
        / "diagnostics"
        / "land-c92521f9627b4cc1a9e0ef65909a1820"
        / "pipeline_visualization.html"
    )
    data = load_visualization_data(html_path)
    out_path = ASSETS_DIR / "fig15_short_window_pipeline_diagnostic.png"

    curve_dates = daily_dates(data["curve"]["start"], len(data["curve"]["ndvi"]))
    curve_values = data["curve"]["ndvi"]
    observations = data["observations"]
    obs_dates = [parse_date(row["d"]) for row in observations]
    filled_values = [row["filled"] for row in observations]
    usable_dates = [parse_date(row["d"]) for row in observations if row["usable"] and row["raw"] is not None]
    usable_values = [row["raw"] for row in observations if row["usable"] and row["raw"] is not None]
    weak_dates = [parse_date(row["d"]) for row in observations if not row["usable"] and row["raw"] is not None]
    weak_values = [row["raw"] for row in observations if not row["usable"] and row["raw"] is not None]

    detector_cycle = data["cycles"][0]
    hmm_cycle = data["hmm"]["cycles"][0]
    comparison = data["hmm"]["comparison"]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.edgecolor": "#9ca3af",
            "axes.labelcolor": "#263735",
            "xtick.color": "#374151",
            "ytick.color": "#374151",
            "text.color": "#263735",
        }
    )
    fig, ax = plt.subplots(figsize=(12.8, 6.4), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    start = parse_date(detector_cycle["start"])
    peak = parse_date(detector_cycle["peak"])
    end = parse_date(detector_cycle["end"])
    hmm_start = parse_date(hmm_cycle["sos_date"])
    hmm_peak = parse_date(hmm_cycle["pos_date"])
    hmm_end = parse_date(hmm_cycle["eos_date"])

    ax.axvspan(start, end, color="#0f766e", alpha=0.08, label="detected activity cycle")
    ax.axvspan(hmm_start, hmm_end, color="#3b82f6", alpha=0.055, label="HMM diagnostic span")

    ax.plot(obs_dates, filled_values, color="#9ca3af", linewidth=1.6, linestyle=(0, (3, 3)), alpha=0.8, label="interpolated observation path")
    ax.plot(curve_dates, curve_values, color="#166534", linewidth=3.0, label="smoothed greenness curve")
    ax.scatter(usable_dates, usable_values, s=34, color="#15803d", edgecolor="white", linewidth=0.8, zorder=5, label="usable observations")
    if weak_dates:
        ax.scatter(weak_dates, weak_values, s=44, marker="x", color="#ea580c", linewidth=1.8, zorder=6, label="low-quality observations")

    markers = [
        (start, "start", "#15803d", 0.15),
        (peak, "peak", "#d97706", 0.48),
        (end, "end", "#92400e", 0.15),
    ]
    for date, label, color, y_offset in markers:
        ax.axvline(date, color=color, linewidth=1.2, alpha=0.6)
        ax.text(
            date,
            0.84 - y_offset,
            label,
            ha="center",
            va="top",
            fontsize=10,
            color=color,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": color, "linewidth": 0.8},
        )

    ax.scatter([hmm_peak], [hmm_cycle["peak_ndvi"]], s=90, marker="D", color="#2563eb", edgecolor="white", linewidth=1.0, zorder=7, label="HMM peak")
    ax.text(
        hmm_peak,
        hmm_cycle["peak_ndvi"] + 0.045,
        "detector and HMM peaks align",
        ha="center",
        va="bottom",
        fontsize=10,
        color="#1d4ed8",
    )

    ax.set_title(
        "Short-window pipeline diagnostic: one activity cycle with HMM agreement",
        fontsize=16,
        fontweight="bold",
        pad=18,
    )
    ax.set_subtitle = None
    ax.text(
        0,
        1.02,
        "Secondary parcel example; diagnostic cross-check supports timing but remains research-only.",
        transform=ax.transAxes,
        fontsize=11,
        color="#5f6f6c",
    )
    ax.set_ylabel("NDVI")
    ax.set_ylim(0.05, 0.86)
    ax.set_xlim(curve_dates[0] - timedelta(days=3), curve_dates[-1] + timedelta(days=3))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(True, axis="y", color="#e5e7eb", linewidth=0.8)
    ax.grid(True, axis="x", color="#f1f5f9", linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    summary = (
        f"Detector cycles: {comparison['prod_cycle_count']}   "
        f"HMM cycles: {comparison['hmm_cycle_count']}   "
        f"Peak delta: {comparison['mean_abs_pos_delta_days']:.0f} days   "
        f"Start/end mean deltas: {comparison['mean_abs_sos_delta_days']:.0f}/{comparison['mean_abs_eos_delta_days']:.0f} days"
    )
    ax.text(
        0.015,
        0.955,
        summary,
        transform=ax.transAxes,
        fontsize=10.5,
        color="#374151",
        ha="left",
        va="top",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#f8fafc", "edgecolor": "#cbd5e1", "linewidth": 0.8},
    )

    handles, labels = ax.get_legend_handles_labels()
    order = [2, 3, 4, 0, 1, 5]
    ax.legend(
        [handles[i] for i in order if i < len(handles)],
        [labels[i] for i in order if i < len(labels)],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.10),
        ncol=3,
        frameon=False,
        fontsize=9.5,
    )
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    plot_short_window_diagnostic()
