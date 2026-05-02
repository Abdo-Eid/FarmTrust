# scripts/

Entry point scripts for running the FarmTrust pipeline locally.

## Files

- `ingest_aoi.py` — end-to-end ingestion: STAC search, chip download, index computation, output writing.
- `ingest_demo.json` — demo config for a sample Egyptian AOI.

## Usage

```bash
uv sync --extra data
uv run ingest-aoi --config scripts/ingest_demo.json
```

See `docs/documentations/01-ingest_aoi_stub.md` for full options and output layout.
