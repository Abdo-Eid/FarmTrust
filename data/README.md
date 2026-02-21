# Data folder

This folder contains ingestion outputs and intermediate results for each AOI run.

## Structure

```

data/
<aoi_id>/
chips/                        # Canonical local dataset (per-scene AOI chips)
<item_id>/
B02.tif                   # Blue (10m) AOI chip
B03.tif                   # Green (10m) AOI chip
B04.tif                   # Red (10m) AOI chip
B08.tif                   # NIR (10m) AOI chip
B11.tif                   # SWIR1 (20m) AOI chip
SCL.tif                   # Scene Classification Layer (20m) AOI chip
manifest.json             # Per-scene manifest: chip paths, shapes, config fingerprint, provenance
scenes_index.json             # Global index: scene metadata + chip file mapping + stats (easy to load later)
indices_timeseries.csv        # Per-scene index stats (NDVI, EVI, NDMI, NDWI, MNDWI)
run_metadata.json             # AOI parameters, scene count, thresholds, config fingerprint

```

## Example

After running ingestion, you will see:

```

data/aoi_demo_01/
chips/
S2A_MSIL2A_20250812T083521_R021_T36RUU_20250812T105117/
B02.tif
B03.tif
B04.tif
B08.tif
B11.tif
SCL.tif
manifest.json
scenes_index.json
indices_timeseries.csv
run_metadata.json

```

## Caching behavior

Chips are the **canonical** dataset and act as the cache:
- If a scene’s chip directory already exists (and matches the current config fingerprint), ingestion will **skip** downloading/recomputing it.
- Use `--force-rerun` to delete the AOI output directory and rebuild from scratch.

## Downstream consumption

- **ML/time-series preprocessing** reads `indices_timeseries.csv` (optionally `scenes_index.json` for provenance and file paths).
- **ML/seasonal analysis** reads smoothed output from preprocessing.
- **ML/scoring** reads seasonal windows and quality metrics.
- **Pixel-level / patch-based models** can read the per-scene chips directly from `chips/<item_id>/...`.
