# Notebooks

This folder contains exploration and verification notebooks for the FarmTrust current-build pipeline.

## Recommended reading order

1. `01-search-path-and-fallback-story.ipynb`
    - Start here for the readable overview of how the STAC search path works.
    - It explains the normal Sentinel-2 path, the shared search helpers, and fallback exploration context.

2. `00-sentinel2_ingestion_timeseries.ipynb`
    - Read this after the search-path story.
    - It shows the full Sentinel-2 ingestion flow: scene search, AOI window reads, masking, index computation, and expected pipeline outputs.

3. `03-land_assessment_story.ipynb`
    - Use this after an end-to-end current-build run exists in `data/`.
    - It reviews the final assessment output, supporting evidence, and gap diagnostics.

4. `00-landsat8_exploration.ipynb`
    - Read this only when fallback behavior or Landsat-specific handling needs deeper inspection.
    - It is a deeper exploration notebook, not the default first stop.

## Notebook roles

- `01-search-path-and-fallback-story.ipynb`
    - Narrative verification notebook for the shared STAC search path.
- `00-sentinel2_ingestion_timeseries.ipynb`
    - Main ingestion exploration notebook for Sentinel-2 AOI processing.
- `03-land_assessment_story.ipynb`
    - End-to-end assessment review notebook for the current-build output and supporting evidence.
- `00-landsat8_exploration.ipynb`
    - Landsat-specific exploration notebook for fallback and sensor-specific behavior.
- `diagnose.py`
    - Script-style diagnostics helper, not part of the main notebook reading order.

## Team guidance

- Prefer the notebooks above in order instead of jumping straight into the largest notebook.
- Treat notebooks as evidence and exploration artifacts, not the source of truth for shared implementation.
- Shared ingestion behavior belongs in `farmtrust_core/`, with notebooks used to verify and explain it.

## Workflow

- Use notebooks for exploration, diagnostics, validation stories, and reviewer-facing evidence.
- Use `farmtrust_core/` for shared pipeline behavior that should be reused by scripts, API workers, or future runs.
- Use scripts/API runs to produce canonical current-build artifacts under `data/`.
- Use notebooks to read and explain those artifacts when reviewing ingestion, preprocessing, seasonal analysis, and assessment results.
- When notebook exploration produces a useful method, promote the logic into `farmtrust_core/`, then regenerate artifacts through the normal pipeline path.

## Artifact Status

- Notebook output: exploratory evidence for understanding, comparison, or review.
- Experiment result: candidate evidence that may become implementation after review.
- Pipeline artifact: canonical output produced by shared code through scripts/API.

## Data Access

- Current assessment review notebooks read from the current-build artifact layout in `data/`:
    - `data/<aoi_id>/run_metadata.json`
    - `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
    - `data/preprocess/<aoi_id>/quality_metrics.json`
    - `data/seasonal/<aoi_id>/season_windows.json`
    - `data/assessment/<aoi_id>/land_assessment.json`
- Prefer explicit `AOI_ID`, `land_id`, or future `run_id` variables near the top of a notebook so reviewers can see which run is being inspected.
- Keep notebook-specific assumptions visible in markdown near the code that depends on them.

## Promotion Path

1. Explore or diagnose behavior in a notebook.
2. Summarize the evidence and assumptions in notebook markdown.
3. Move reusable logic into `farmtrust_core/` when it should affect shared behavior.
4. Run the relevant script/API path to produce canonical artifacts.
5. Update the relevant canonical doc when the change affects product scope, architecture, interfaces, or decisions.
