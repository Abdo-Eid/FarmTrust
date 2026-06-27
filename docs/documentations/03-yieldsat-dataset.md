# YieldSAT Dataset

Date started: 2026-06-27

## Identity

- **Kaggle dataset:** `abdulhamedeid/yieldsat-private` (private)
- **Owner:** Abdulhamed Eid
- **Total size:** ~190.4 GB
- **Purpose:** Multi-source agricultural data for crop yield prediction and crop mapping research.
- **Full external docs:** `D:\work\yieldSAT\reports\` — includes `dataset_inventory.md`, `schema_summary.md`, `model_tables_guide.md`, `YIELDSAT_BEGINNER_GUIDE.md`, `EXPLORATION_LOG.md`.

## Coverage

| Country | Fields | Crops | Years | Provider |
|---------|--------|-------|-------|----------|
| Argentina | 751 | soybean, corn, wheat | 2017–2024 | DUP1 |
| Brazil | 551 | soybean, corn, wheat | 2017–2024 | DUP2 |
| Germany | 299 | wheat, rapeseed | 2016–2022 | DUP3 |
| Uruguay | 572 | soybean | 2018–2022 | DUP4 |
| **Total** | **2,173** | **4 crops** | **2016–2024** | — |

## Structure

Two tiers:

```
yieldsat-private/
├── Preprocessed/   (~147 GB) — one NetCDF per country, merged multi-source, ready for xarray
└── Raw/            (~43 GB) — one folder per field with original parts
    └── {Country}/
        └── {farmX_fieldYYY_crop_year}/
            ├── dem/           5 GeoTIFFs: elevation, slope, aspect, curvature, TWI
            ├── s2_images/     ~50–80 GeoTIFFs (Sentinel-2 L2A, 12-band, uint16 ×10000)
            ├── scl_masks/     ~50–80 GeoTIFFs (Scene Classification Layer, uint8)
            ├── soil/          8 GeoTIFFs: clay, sand, silt, SOC, N, pH, CEC, cfvo
            ├── weather/       1 CSV (daily Temp_mean/max/min in Kelvin, Total_prec in meters)
            ├── yield_masks/   3 GeoTIFFs: mean, std, count of scaled yield
            └── metadata-*.json  crop, year, dates, yield_ground_truth, area, centroid
```

## Unit & Scaling Gotchas

- Weather temperatures are in **Kelvin** (convert to °C).
- Precipitation is in **meters** (convert to mm).
- Sentinel-2 L2A reflectance is `uint16` scaled by **10000** (convert to 0–1 before indices like EVI/SAVI).
- Soil GeoTIFFs can be **multi-band** (e.g., clay has 12 depth bands) — do not assume single band.
- Slope appears scaled by **10000** in some rasters.
- `yield_ground_truth` is a **number** in some JSONs, a **string** in others — parse both.
- `adm_units` key names differ by country.
- CRS varies: EPSG:32720 (Argentina), EPSG:32633 (Germany), etc.

## Existing Yield Model Tables

Prior extraction (`scripts/extract_features.py`) produced three CatBoost-ready tables:

| Table | Rows | Columns | Description |
|-------|------|---------|-------------|
| `model_mid_season.parquet` | 1,583 | 1,204 | Features up to 50% of growing period |
| `model_near_harvest.parquet` | 1,583 | 1,204 | Features up to 30 days before harvest |
| `model_full_season.parquet` | 1,583 | 1,188 | Full season |

- 590 fields excluded due to unusable Sentinel-2 imagery.
- Columns: metadata, DEM (45), SoilGrids (864), weather (37), Sentinel-2 (218–234).
- Target: `target_yield_t_ha`.
- 4 crops: soybean (715), wheat (454), corn (303), rapeseed (111).

## Yield-Prediction Use Case

This is the original dataset purpose. The target is `yield_ground_truth` (t/ha) from metadata JSONs or the yield masks.

- `crop` is a natural feature for multi-crop yield models.
- The three model tables are ready for CatBoost/XGBoost/lightGBM yield regression.
- The Preprocessed NetCDFs support spatiotemporal deep learning with `xarray`.

## Crop-Mapping Use Case

The dataset is also useful for crop classification (mapping) because it provides:

- **Ground-truth `crop` label** per field (soybean, corn, wheat, rapeseed).
- **Sentinel-2 time series** with SCL cloud masks — spectral-temporal signal for crop discrimination.
- **Weather, DEM, and soil** as auxiliary features or environmental context.
- **Multi-country, multi-year** coverage for testing cross-domain generalization.

### FarmTrust Crop-Mapping Extraction Notebook

`notebooks/yieldsat_crop_mapping_feature_store.ipynb` extracts YieldSAT into two reusable Parquet tables designed for crop-mapping research:

- `crop_mapping_fields.parquet` — one row per field: crop label, country, provider, farm, year, dates, area, centroid, CRS, DEM, soil, non-yield metadata.
- `crop_mapping_observations.parquet` — one row per field per Sentinel-2 observation date: all 12 bands, vegetation indices, SCL fractions, valid-pixel metrics, daily/rolling/cumulative weather.

### Leakage Rules for Crop Mapping

- `crop` is the label — must not be used as an input feature.
- No yield features: no `target_yield_t_ha`, yield masks, or `yield_ground_truth`.
- Country, provider, year, farm are metadata — can encode dataset bias. Report their use and prefer grouped validation.

## Status

The YieldSAT dataset exists externally at `D:\work\yieldSAT\` and on Kaggle. The FarmTrust crop-mapping extraction notebook is created and ready for sample testing. Full extraction requires the raw dataset on Kaggle or equivalent.
