# scripts/

Entry point scripts for running the FarmTrust pipeline locally.

## Files

- `ingest_aoi.py` — end-to-end ingestion: STAC search, chip download, index computation, output writing.
- `preprocess_timeseries.py` — build smoothed NDVI/EVI/NDMI/NDWI preprocessing outputs from ingestion results.
- `seasonal_analysis.py` — detect season windows from preprocessing outputs.
- `land_assessment.py` — build the interval-based land assessment from ingest + preprocess + seasonal outputs.
- `ingest_demo.json` — demo config for a sample Egyptian AOI.

## Usage

```bash
uv sync --extra data
uv run ingest-aoi --config scripts/ingest_demo.json
```

```bash
python scripts/preprocess_timeseries.py --aoi-id aoi_demo_01
python scripts/seasonal_analysis.py --aoi-id aoi_demo_01
python scripts/land_assessment.py --aoi-id aoi_demo_01
```

See `docs/documentations/01-ingest_aoi_stub.md` for full options and output layout.
