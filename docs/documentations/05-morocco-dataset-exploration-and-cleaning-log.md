# Morocco Dataset Exploration And Cleaning Log

Date started: 2026-06-28

## Purpose

This document records the scientific and technical decisions behind `notebooks/07-morocco_dataset.ipynb`.

The notebook is now the source of truth for the workflow. It downloads the two useful Figshare files, extracts them, creates one raw merged Parquet checkpoint, reloads that checkpoint, and then creates one selected crop/background Sentinel-2 time-series dataset for later modeling work.

Generated archives, extracted folders, and processed data are local notebook artifacts and should not be committed.

## Dataset Sources

Primary article:

- https://www.nature.com/articles/s41597-026-06993-y#data-availability

Figshare dataset page:

- https://figshare.com/articles/dataset/_b_Crop_and_irrigation_type_dataset_for_Moroccan_agricultural_regions_b_b_A_ground-truth_resource_for_earth_observation_validation_b_/28486022/2

Files used:

| File ID | File | Role |
|---:|---|---|
| `56267117` | `Shapefile_Crop and irrigation dataset.rar` | Ground-truth parcel attributes and labels |
| `56267120` | `Sentinel2 bands and Ndvi for surveyed parcels.rar` | Per-parcel Sentinel-2/NDVI time-series CSVs |

The large georeferenced-photo archive was skipped because it contains normal field photos and is not needed for this tabular remote-sensing dataset.

## Notebook Workflow

Notebook:

- `notebooks/07-morocco_dataset.ipynb`

Current workflow:

1. Install `dbfread` in Colab.
2. Download only the two selected Figshare files.
3. Extract both archives under `data/morocco_crop_irrigation/`.
4. Read the shapefile DBF attributes and all Sentinel-2 parcel CSV files.
5. Merge them by `parcel_id`.
6. Save one raw checkpoint: `raw_merged.parquet`.
7. Reload only `raw_merged.parquet` and continue from that file.
8. Keep selected seasonal crops plus background labels.
9. Save one cleaned time-series file: `morocco_selected_crop_background_timeseries.parquet`.

Important cleanup decision:

- The temporary script-based build path was removed.
- Old generated folders were removed.
- The notebook is the reproducible path for this dataset stage.

## Raw Data Facts Preserved

Raw shapefile attribute table:

- Shape: `(10383, 13)`.
- Columns: `parcel_id`, `date`, `crop`, `season`, `tree`, `irrigation`, `btw_lines`, `btw_trees`, `height`, `diameter`, `cp_height`, `zone`, `photo`.

Raw `crop` category counts:

| crop category | count |
|---|---:|
| `Seasonal Crop` | `6975` |
| `Trees` | `1427` |
| `Bare soil` | `942` |
| `Weed` | `638` |
| `Trees + Seasonal` | `385` |
| `Water` | `16` |

Sentinel-2/NDVI data:

- The archive contains per-parcel CSV time series, not full raster imagery.
- Usable Sentinel-2 parcels found in notebook output: `9993`.
- Raw merged table shape from notebook output: `(518907, 29)`.
- Sentinel-2 date range from notebook output: `2024-01-01` to `2024-12-26`.

Coverage finding:

- The data has broad 2024 coverage, but parcels do not have identical observation counts.
- Earlier coverage checks showed observation counts ranging from `18` to `301`, with median around `37` observations per parcel.
- Later modeling should handle variable-length time series through aggregation, time-window features, interpolation, or a sequence model that supports uneven sequence lengths.

## Label Interpretation

The raw columns have different meanings:

- `crop`: broad parcel/land-cover category.
- `season`: seasonal crop name for pure seasonal crop parcels.
- `tree`: tree crop name for tree parcels.

The final label rule used in the notebook:

- If `crop == "Seasonal Crop"`, label comes from `season`.
- If `crop` is a background class, label comes from `crop`.

Background labels kept:

- `Bare soil`
- `Water`
- `Weed`

Excluded categories:

- `Trees`
- `Trees + Seasonal`

Reason:

- Tree-only and mixed tree-seasonal parcels are not clean seasonal field-crop signals for the first crop-classification dataset.

## Reviewed Crop Set

Main target crops kept:

- `Wheat`
- `Corn`
- `Alfalfa`

Reviewed seasonal crops kept for later possible `Other` grouping:

- `Beets`
- `Potatoes`
- `Peas`
- `Peanut`
- `Onions`
- `Tomatoes`
- `Sugarcane`
- `Fava Beans`
- `Parsley`
- `Rice`

Selection rationale:

- Keep crops with count `>= 25`.
- Remove crops with count `< 25`.
- Keep reviewed crops that are agriculturally close to one of the three main target crops.
- Do not group these crops into `Other` yet; defer that to a later modeling notebook.

Similarity notes:

| Future group direction | Reviewed crops kept for later |
|---|---|
| Close to `Wheat` | `Beets`, `Potatoes`, `Peas`, `Onions`, `Fava Beans` |
| Close to `Corn` | `Peanut`, `Tomatoes`, `Sugarcane`, `Rice` |
| Close to `Alfalfa` | `Peas`, `Peanut`, `Fava Beans`, `Parsley` |

Some crops can support more than one future group, such as `Peas`, `Peanut`, and `Fava Beans`.

## Final Notebook Output

The notebook writes one selected crop/background time-series file:

- `data/morocco_crop_irrigation/morocco_selected_crop_background_timeseries.parquet`

Final columns:

- `parcel_id`
- `satellite_date`
- `B1`
- `B2`
- `B3`
- `B4`
- `B5`
- `B6`
- `B7`
- `B8`
- `B8A`
- `B9`
- `B11`
- `B12`
- `ndvi`
- `survey_date`
- `label`
- `irrigation_type`
- `survey_zone`

Excluded from final output:

- `source_folder`
- `source_file`
- raw `irrigation`
- `photo`
- tree labels
- mixed tree-seasonal labels
- tree-only labels
- unreviewed rare crops
- tree-structure measurement columns: `btw_lines`, `btw_trees`, `height`, `diameter`, `cp_height`

## Current Status

This stage is complete enough for the next notebook to decide label grouping and modeling strategy.

Next expected work:

- Reload `morocco_selected_crop_background_timeseries.parquet`.
- Decide how to group reviewed non-main crops into `Other`.
- Decide whether to aggregate time series into field-level features or train temporal models directly.
