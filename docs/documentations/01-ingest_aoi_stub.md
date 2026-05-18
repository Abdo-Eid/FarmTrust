# Sentinel-2 ingestion script — how to use

## Purpose

This script queries Sentinel-2 L2A scenes via STAC (Planetary Computer), **downloads local AOI “chips” (cropped rasters) per scene**, computes vegetation/water indices (NDVI, EVI, NDMI, NDWI, MNDWI), applies SCL-based cloud/shadow masking, and outputs both:

* a per-scene time-series CSV, and
* a **global JSON index** mapping scenes → local chip files + stats.

**Chips are the canonical local dataset** used by downstream roles. The script implements local scene/chip reuse by skipping scenes if chips already exist for the same configuration. STAC search results are not cached; the pipeline queries STAC each run, then decides which returned scenes can skip download/reprocessing.

## Run (UV)

Install ingestion dependencies first:

```bash
uv sync --extra data
```

Use the demo config:

```bash
uv run ingest-aoi --config scripts/ingest_demo.json
```

Or pass parameters directly:

```bash
uv run ingest-aoi --aoi-id aoi_demo_01 --bbox 30.9903,30.594356,31.013848,30.616635
```

For team-consistent installs:

```bash
uv sync --frozen --extra data
```

### Additional options

* `--force-rerun`: clear existing output and rerun ingestion.
* `--debug`: enable debug logging for troubleshooting.
* `--limit-items N`: limit number of scenes (useful for quick testing).
* `--log-signed-hrefs`: log signed STAC asset URLs (very verbose).
* `--no-dedupe`: skip pre-download deduplication; emit all STAC scenes as-is (raw/debug mode).
* `--workers N`: number of parallel download workers (default: 4; set to 1 for sequential debugging). Can also be set as `"workers": N` in the JSON config file.

## Inputs

* `aoi_id`: stable identifier for the AOI.
* `bbox`: min_lon,min_lat,max_lon,max_lat (EPSG:4326).
* `start_date`, `end_date`, `max_cloud`: optional; defaults are used if missing.
* `output_dir`: optional override (default: `data/<aoi_id>`).

> Note: `cache_dir` is **no longer used**. The `chips/` directory is the canonical dataset.

Config example lives at `scripts/ingest_demo.json`.

## Deduplication

STAC returns multiple scenes per calendar date when the AOI spans tile boundaries, or when both S2A and S2B satellites acquire on the same day. By default, the script keeps only one scene per (calendar date, spacecraft) before downloading — the one with the lowest `eo:cloud_cover`. If two scenes tie on cloud cover, the lexicographically lower `item_id` wins (deterministic).

The log shows which scenes are dropped:
```
Pre-dedup: 2025-08-03 S2C kept=S2C_..._T36RUU dropped=['S2C_..._T36RTU'] (cloud_cover=1.79)
```

Use `--no-dedupe` to skip this filter and process all STAC results.

## Parallel downloads

By default, up to 4 scenes are downloaded simultaneously (`--workers 4`). Each worker is a thread — safe for I/O-bound COG reads. Planetary Computer handles up to ~8 concurrent connections without throttling.

Each failed scene is retried up to 3 times with exponential backoff (1s, 2s, 4s). SAS tokens are re-signed before each retry to handle token expiry.

To run sequentially (useful when debugging a single scene): `--workers 1`.

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
* `platform`: raw STAC platform string (e.g. `"Sentinel-2C"`)
* `spacecraft`: normalized spacecraft ID (`"S2A"`, `"S2B"`, `"S2C"`)
* `aoi_geometry`: the AOI bbox as a GeoJSON Polygon — load with `shapely.geometry.shape(scenes_index["aoi_geometry"])` for coverage or containment calculations

### Local reuse behavior (“skip if chip exists”)

On reruns with the **same config fingerprint**, the script will:

* detect that chip files already exist for a scene, and
* skip downloading/recomputing it,
* still ensuring CSV rows can be produced (from the global index).

Use `--force-rerun` to wipe and rebuild everything.

This is not a STAC query-result cache. The removed STAC TTL/env-var cache helper is no longer part of the codebase.

## How roles use the outputs

* **ML/time-series preprocessing**: reads `indices_timeseries.csv` (and optionally `scenes_index.json` for provenance and paths).
* **ML/seasonal analysis**: reads smoothed outputs produced downstream (not created by this script).
* **ML/scoring**: consumes seasonal windows + quality metrics produced downstream.
* **Any downstream pixel-level logic**: reads chips directly from `chips/<item_id>/...`.

## Implementation

The CLI entry point is `scripts/ingest_aoi.py` (~100 lines, argument parsing only). All pipeline logic lives in `farmtrust_core/ingest/`:

| Module | Responsibility |
|---|---|
| `pipeline.py` | `write_outputs()` orchestrator |
| `processor.py` | `process_one_scene()` thread-safe worker |
| `dedup.py` | Pre-download deduplication |
| `scene_index.py` | `scenes_index.json` CRUD + cache-skip logic |
| `window_read.py` | COG window reads, reprojection, chip writing |
| `indices.py` | NDVI, EVI, NDMI, NDWI, MNDWI computation |
| `stac_client.py` | STAC search with endpoint fallback |
| `config.py` | Config parsing, bbox normalization |
| `utils.py` | Fingerprint, atomic file write, UTC timestamp |
