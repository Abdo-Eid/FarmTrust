# Sentinel-2 ingestion script — how to use

## Purpose

This script queries Sentinel-2 L2A scenes via STAC (Planetary Computer), **downloads local AOI “chips” (cropped rasters) per scene**, computes vegetation/water indices (NDVI, EVI, NDMI, NDWI, MNDWI), applies SCL-based cloud/shadow masking, and outputs both:

* a per-scene time-series CSV, and
* a **global JSON index** mapping scenes → local chip files + stats.

**Chips are the canonical local dataset** used by downstream roles. The script implements **true caching** by skipping scenes if chips already exist for the same configuration.

## Run (UV)

Use the demo config:

```bash
uv run python worker/scripts/ingest_aoi.py --config worker/scripts/ingest_demo.json
```

Or pass parameters directly:

```bash
uv run python worker/scripts/ingest_aoi.py --aoi-id aoi_demo_01 --bbox 30.9903,30.594356,31.013848,30.616635
```

### Additional options

* `--force-rerun`: clear existing output and rerun ingestion.
* `--debug`: enable debug logging for troubleshooting.
* `--limit-items N`: limit number of scenes (useful for quick testing).
* `--log-signed-hrefs`: log signed STAC asset URLs (very verbose).

## Inputs

* `aoi_id`: stable identifier for the AOI.
* `bbox`: min_lon,min_lat,max_lon,max_lat (EPSG:4326).
* `start_date`, `end_date`, `max_cloud`: optional; defaults are used if missing.
* `output_dir`: optional override (default: `data/<aoi_id>`).

> Note: `cache_dir` is **no longer used**. The `chips/` directory is the canonical dataset.

Config example lives at `worker/scripts/ingest_demo.json`.

## Outputs

The script writes outputs to:

* `data/<aoi_id>/chips/<item_id>/...` (**canonical dataset**)
* `data/<aoi_id>/indices_timeseries.csv`
* `data/<aoi_id>/scenes_index.json`
* `data/<aoi_id>/run_metadata.json`

### Chips layout (per scene)

Each scene writes a folder:

* `data/<aoi_id>/chips/<item_id>/SCL.tif`
* `data/<aoi_id>/chips/<item_id>/B02.tif`
* `data/<aoi_id>/chips/<item_id>/B03.tif`
* `data/<aoi_id>/chips/<item_id>/B04.tif`
* `data/<aoi_id>/chips/<item_id>/B08.tif`
* `data/<aoi_id>/chips/<item_id>/B11.tif`
* `data/<aoi_id>/chips/<item_id>/manifest.json`

### `scenes_index.json` (global index)

This file is a single JSON object that stores:

* scene metadata (timestamp, tile, cloud cover)
* the **relative paths** to chip files for each band
* computed stats (mean + p95)
* a **fingerprint** of the config (bbox/dates/cloud threshold/mask rules) used for caching

### Caching behavior (“skip if chip exists”)

On reruns with the **same config fingerprint**, the script will:

* detect that chip files already exist for a scene, and
* skip downloading/recomputing it,
* still ensuring CSV rows can be produced (from the global index).

Use `--force-rerun` to wipe and rebuild everything.

## How roles use the outputs

* **ML/time-series preprocessing**: reads `indices_timeseries.csv` (and optionally `scenes_index.json` for provenance and paths).
* **ML/seasonal analysis**: reads smoothed outputs produced downstream (not created by this script).
* **ML/scoring**: consumes seasonal windows + quality metrics produced downstream.
* **Any downstream pixel-level logic**: reads chips directly from `chips/<item_id>/...`.

This script fetches Sentinel-2 data via STAC (Planetary Computer) and writes a reproducible local chip dataset for downstream processing.

