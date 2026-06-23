# Data folder

This folder contains ingestion outputs and intermediate results for each AOI run.

## Structure

```text
data/
  <aoi_id>/
    cube.zarr/                    # Canonical source pixels/provenance
      B02/ B03/ B04/ B08/          # Root 10m bands
      20m/                         # Native 20m bands when requested
        B05/ B06/ B07/ B8A/ B11/ SCL/
    scenes_index.jsonl             # Operational day/band download ledger
    indices_timeseries.csv         # Solar-day index stats
    run_metadata.json              # AOI parameters, band set, thresholds, run config
```

## Example

After running ingestion, you will see:

```text
data/aoi_demo_01/
  cube.zarr/
  indices_timeseries.csv
  scenes_index.jsonl
  run_metadata.json
```

## Caching behavior

`cube.zarr` is the canonical source dataset and acts as the cache:

- Existing source bands are reused when the AOI/grid configuration matches.
- Missing requested bands are backfilled without rewriting already-present bands.
- Use `--force-rerun` to delete the AOI output directory and rebuild from scratch.

## Downstream consumption

- Preprocessing reads `indices_timeseries.csv`.
- Seasonal analysis reads smoothed output from preprocessing.
- Scoring reads seasonal windows and quality metrics.
- Pixel-level / patch-based models can read source pixels directly from `cube.zarr`.
