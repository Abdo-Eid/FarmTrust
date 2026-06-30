# outputs/

Non-production material: exploratory analysis, diagnostic tooling, and generated
diagnostic artifacts. **Nothing here is imported by the production pipeline**
(`farmtrust_core/`, `api/`, or the production `scripts/`). Production pipeline
artifacts live under `data/` instead.

## Layout

- `exploration/` — the original isolated one-parcel (Menofia / `aoi_demo_01`)
  analysis: scripts, process report, figures, and HTML used as a design
  reference for tasks T-11 / T-04 / T-12.
- `tools/` — non-production diagnostic tooling:
  - `hmm_phenology.py` — deterministic 4-state Gaussian HMM phenology decoder
    (research cross-check, **not** the production detector).
  - `hmm_comparison.py` — compares the production detector windows against the
    HMM cycles.
  - `season_detector_comparison.py` — CLI: write the HMM cross-check artifact.
  - `visualize_pipeline_outputs.py` — CLI: render the pipeline visualization HTML.
- `diagnostics/<aoi>/` — generated diagnostic artifacts per AOI:
  - `pipeline_visualization.html` — raw observations + linear interpolation +
    Whittaker curve + per-point hover + detected cycles + HMM comparison
    (open in a browser).
  - `hmm_cross_check.{json,md}` — HMM-vs-detector comparison.

## Regenerate

From the repo root, after a pipeline run has produced `data/preprocess/<aoi>/`
and `data/seasonal/<aoi>/`:

    uv run python outputs/tools/season_detector_comparison.py --aoi-id <aoi>
    uv run python outputs/tools/visualize_pipeline_outputs.py --aoi-id <aoi>

Both default their output to `outputs/diagnostics/<aoi>/`.
