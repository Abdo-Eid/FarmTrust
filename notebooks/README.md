# Notebooks

This folder contains exploration and verification notebooks for the FarmTrust Phase A pipeline.

## Recommended reading order

1. `01-search-path-and-fallback-story.ipynb`
    - Start here for the readable overview of how the STAC search path works.
    - It explains the normal Sentinel-2 path, the shared search helpers, and fallback exploration context.

2. `00-sentinel2_ingestion_timeseries.ipynb`
    - Read this after the search-path story.
    - It shows the full Sentinel-2 ingestion flow: scene search, AOI window reads, masking, index computation, and saved outputs.

3. `03-land_assessment_story.ipynb`
    - Use this after an end-to-end Phase A run exists in `data/`.
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
    - End-to-end assessment review notebook for the Phase A output and supporting evidence.
- `00-landsat8_exploration.ipynb`
    - Landsat-specific exploration notebook for fallback and sensor-specific behavior.
- `diagnose.py`
    - Script-style diagnostics helper, not part of the main notebook reading order.

## Team guidance

- Prefer the notebooks above in order instead of jumping straight into the largest notebook.
- Treat notebooks as evidence and exploration artifacts, not the source of truth for shared implementation.
- Shared ingestion behavior belongs in `farmtrust_core/`, with notebooks used to verify and explain it.
