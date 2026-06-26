# Sentinel-2 ingestion script — how to use

> **Superseded by T-06 (2026-06-20).** Describes the legacy per-scene rasterio path (`pipeline.py` / `write_outputs()`), now removed. `scripts/ingest_aoi.py` delegates to `farmtrust_core.ingest.runner.run_ingestion` (odc.stac.load solar-day cube path). The `--loader`/`--no-dedupe` flags and per-scene chip outputs no longer exist. Historical context only. Current outputs are `cube.zarr`, `indices_timeseries.csv`, `scenes_index.jsonl`, and `run_metadata.json`; see `docs/PIPELINE.md` for authoritative current behavior.

## Purpose

Legacy behavior: this script queried Sentinel-2 L2A scenes via STAC (Planetary Computer), **downloaded local AOI “chips” (cropped rasters) per scene**, computed vegetation/water indices (NDVI, EVI, NDMI, NDWI, MNDWI), applied SCL-based cloud/shadow masking, and output both:

* a per-scene time-series CSV, and
* a **global JSON index** mapping scenes → local chip files + stats.

Legacy chips were the canonical local dataset used by downstream roles. Current ingestion uses `cube.zarr` as the canonical local source dataset and can backfill missing bands independently. STAC search results are not cached; the pipeline queries STAC each run, then decides which returned solar days/bands can skip download.

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

### Current options

* `--force-rerun`: clear existing output and rerun ingestion.
* `--debug`: enable debug logging for troubleshooting.
* `--limit-items N`: limit number of scenes (useful for quick testing).
* `--log-signed-hrefs`: log signed STAC asset URLs (very verbose).
* `--workers N`: number of parallel solar-day download workers. Can also be set as `"workers": N` in the JSON config file.
* `--bands B02,B03,...`: requested source bands to store/backfill. Missing 20m bands are repaired in `cube.zarr/20m` without rewriting existing 10m bands.

## Inputs

* `aoi_id`: stable identifier for the AOI.
* `bbox`: min_lon,min_lat,max_lon,max_lat (EPSG:4326).
* `start_date`, `end_date`, `max_cloud`: optional; defaults are used if missing.
* `output_dir`: optional override (default: `data/<aoi_id>`).

> Note: `cache_dir` is **no longer used**. The canonical local source dataset is now `cube.zarr`, not `chips/`.

Config example lives at `scripts/ingest_demo.json`.

## Legacy Deduplication

STAC returns multiple scenes per calendar date when the AOI spans tile boundaries, or when both S2A and S2B satellites acquire on the same day. By default, the script keeps only one scene per (calendar date, spacecraft) before downloading — the one with the lowest `eo:cloud_cover`. If two scenes tie on cloud cover, the lexicographically lower `item_id` wins (deterministic).

The log shows which scenes are dropped:
```
Pre-dedup: 2025-08-03 S2C kept=S2C_..._T36RUU dropped=['S2C_..._T36RTU'] (cloud_cover=1.79)
```

`--no-dedupe` no longer exists. Current ingestion groups STAC items by solar day and mosaics overlapping tiles.

## Parallel downloads

Current ingestion parallelizes solar-day loads. Each worker is a thread — safe for I/O-bound COG reads.

Each failed scene is retried up to 3 times with exponential backoff (1s, 2s, 4s). SAS tokens are re-signed before each retry to handle token expiry.

To run sequentially (useful when debugging a single scene): `--workers 1`.

## Outputs

Current ingestion writes outputs to:

* `data/<aoi_id>/cube.zarr/` (**canonical source dataset**; root 10m grid plus native `20m` group)
* `data/<aoi_id>/indices_timeseries.csv`
* `data/<aoi_id>/scenes_index.jsonl`
* `data/<aoi_id>/run_metadata.json`

### Current cube layout

The cube stores source pixels and provenance:

* root group: `B02`, `B03`, `B04`, `B08`, `time`, `y`, `x`, provenance variables
* `20m` group: native 20m bands such as `B05`, `B06`, `B07`, `B8A`, `B11`, `B12`, `SCL` when requested

### `scenes_index.jsonl` (operational ledger)

This append-only JSONL ledger stores:

* one record per attempted solar day
* `cache_key` and day `status`
* optional per-band `band_status` for repair/backfill

### Local reuse behavior

On reruns with the same AOI/grid configuration, ingestion will:

* skip already-present source bands
* download only missing requested bands
* recompute `indices_timeseries.csv` from local source pixels

Use `--force-rerun` to wipe and rebuild everything.

This is not a STAC query-result cache. The removed STAC TTL/env-var cache helper is no longer part of the codebase.

## How roles use the outputs

* **ML/time-series preprocessing**: reads `indices_timeseries.csv`.
* **ML/seasonal analysis**: reads smoothed outputs produced downstream (not created by this script).
* **ML/scoring**: consumes seasonal windows + quality metrics produced downstream.
* **Any downstream pixel-level logic**: reads source pixels from `cube.zarr`.

## Implementation

The CLI entry point is `scripts/ingest_aoi.py` (~100 lines, argument parsing only). Legacy pipeline logic lived in `farmtrust_core/ingest/`:

| Module | Responsibility |
|---|---|
| `pipeline.py` | `write_outputs()` orchestrator |
| `processor.py` | `process_one_scene()` thread-safe worker |
| `dedup.py` | Pre-download deduplication |
| `scene_index.py` | Legacy JSON index CRUD + cache-skip logic |
| `window_read.py` | COG window reads, reprojection, chip writing |
| `indices.py` | NDVI, EVI, NDMI, NDWI, MNDWI computation |
| `stac_client.py` | STAC search with endpoint fallback |
| `config.py` | Config parsing, bbox normalization |
| `utils.py` | Fingerprint, atomic file write, UTC timestamp |

Current ingestion modules are `runner.py`, `cube_pipeline.py`, `cube_loader.py`, `cube_stats.py`, `indices.py`, `config.py`, and `utils.py`.
