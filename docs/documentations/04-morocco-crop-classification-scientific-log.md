# Morocco Crop Classification Scientific Log

Date started: 2026-06-28

## Version Note

This document is the old/current-work scientific snapshot for the Morocco crop-classification work. It merges the PR #11 AOI/XGBoost inference evidence with the later Morocco dataset exploration and cleaning decisions.

It is intended to support the graduation book by keeping the research question, experiments, progress, struggles, dataset decisions, and interpretation in one coherent place. Later work may supersede these results.

This is research-only. Crop classification is not part of the current FarmTrust production land assessment output.

Latest branch outcome, after the sequential experiments below: the current AOI-passing candidate is the Morocco-only binary `Alfalfa`/`Corn` LightGBM configuration in `notebooks/08-morocco_crop_lightgbm_baseline.ipynb`. It uses only AOI-compatible features: 9 brightness-normalized default Sentinel-2 band ratios plus 9 vegetation indices. It predicts C1 Corn and C3 Corn as `Corn`, and C4 Alfalfa as `Alfalfa`; C4 passes with moderate confidence and remains the weaker case.

The log has two connected parts:

- Old AOI inference work: notebook-trained XGBoost models tested against a known Corn AOI.
- Dataset preparation work: Figshare Morocco crop/irrigation data prepared into a selected crop/background Sentinel-2 time-series dataset for later modeling.

## Research Objective

The objective was to test whether a notebook-trained XGBoost crop classifier could be used for an AOI-style inference input.

The specific AOI used in this stage was known to be `Corn`. The work tested which available model path could produce a defensible current demo result while keeping failed and blocked paths visible.

## Scientific Question

Can a tabular XGBoost crop classifier trained from Sentinel-2 field features correctly classify a real AOI cube when the inference input is reduced to the bands and features available in the AOI archive?

Secondary questions:

- Does the model's expected feature schema match the AOI's available bands?
- Can a merged multi-source crop model generalize to this AOI?
- Are execution success and scientific validation success the same thing?

The answer at this stage is partial. One Morocco-only model predicted the known Corn AOI correctly, but with low confidence. The broader merged five-label model path was either blocked or failed validation.

Latest answer: after additional experiments, the Morocco-only binary LightGBM model passed the current three-season AOI label check. The combined multi-source models still failed the AOI check, which supports a source/domain/class-boundary-conflict interpretation rather than a code-only or AOI-data-impossibility explanation.

## Working Hypotheses

Hypothesis 1: A Morocco-only XGBoost model trained from Morocco field features may work better on the current AOI than a merged model because its feature set is closer to the available AOI bands.

Status: supported only as a one-AOI smoke result. The Morocco-only model predicted `corn`, but confidence was low.

Hypothesis 2: A merged AgrifieldNet + Morocco five-label model may provide broader crop coverage.

Status: not validated in the current AOI test. The full model was blocked by missing artifact and missing AOI bands. The AOI-compatible reduced variant predicted `Wheat` for known `Corn`.

Hypothesis 3: Missing spectral bands should not be imputed just to force a model to run.

Status: accepted as a research guardrail. Missing `B01`, `B09`, and `B12` blocked the full merged model instead of being invented.

## Data And AOI Context

The tested AOI archive was:

- `D:\My_Downloads\aoi_demo_01 (1).rar`

The extracted AOI input contained:

- `cube.zarr`
- known actual label: `Corn`
- archive member count: `8763`

Available Zarr variables included:

- `B02`
- `B03`
- `B04`
- `B05`
- `B06`
- `B07`
- `B08`
- `B8A`
- `B11`
- `SCL`
- `mgrs_tiles`
- `min_cloud_cover`
- `source_item_ids`

Important missing bands:

- `B01`
- `B09`
- `B12`

No missing bands were imputed or synthesized.

## Model Paths Investigated

### Morocco-Only XGBoost

Notebook source:

- `notebooks/Morocco_Only_XGBoost_professional.ipynb`

Local artifact folder:

- `models/Moroco_only_Model/`

Target classes:

- `corn`
- `other_crop`
- `soil`
- `wheat`

The notebook trained a tabular XGBoost classifier from Morocco field-level Sentinel-2 features. It did not use the `Photos/` folder as image input. It used consolidated tabular CSV features.

Training data recorded by the notebook:

- labels table shape: `(7124, 9)`
- features table shape: `(7124, 17)`
- filtered rows after label cleaning: `6762`

Class counts after filtering:

- `wheat`: `2614`
- `other_crop`: `1954`
- `corn`: `1252`
- `soil`: `942`

Notebook holdout evidence:

- best CV macro F1: `0.7305293112128431`
- tuned holdout accuracy: `0.7531411677753141`
- tuned holdout macro F1: `0.73`

Final feature count: `17`.

Raw and engineered features included:

- `B2`, `B3`, `B4`, `B5`, `B6`, `B7`, `B8`, `B8A`, `B11`, `NDVI`
- `NDWI`, `NDBI`, `SAVI`, `BSI`, `B11_B8_ratio`, `B4_B8_ratio`, `B8_B4_diff`

Inference preprocessing reproduced the notebook contract:

- mean-aggregate AOI Zarr bands
- compute `NDVI`
- apply saved clipping bounds
- compute engineered indices
- reorder by `feature_cols_v2.pkl`
- predict probabilities with XGBoost

### Full Merged Five-Label XGBoost

Notebook source:

- `notebooks/Merged_xgboost_training.ipynb`

Research purpose:

- combine AgrifieldNet and Morocco field-level samples
- test a broader five-label crop classifier

Five retained labels:

- `Corn`
- `Potatoes`
- `Rice`
- `Sugarcane`
- `Wheat`

The merged dataset contained `11284` rows and `16` columns before five-label filtering. After removing unsupported labels, `7200` rows remained.

Source counts in the merged CSV:

- `morocco`: `6762`
- `agrifieldnet`: `4522`

The full model expected these static mean features:

- `B01_mean`
- `B02_mean`
- `B03_mean`
- `B04_mean`
- `B05_mean`
- `B06_mean`
- `B07_mean`
- `B08_mean`
- `B8A_mean`
- `B09_mean`
- `B11_mean`
- `B12_mean`
- `NDVI_mean`

Notebook holdout evidence for the full five-label model:

- accuracy: `0.845139`
- macro F1: `0.753623`
- weighted F1: `0.849403`
- 5-fold mean macro F1: `0.7696`

Current status in AOI testing:

- blocked because the expected local full model artifact was missing
- also incompatible with the current AOI unless a full-band AOI provides `B01`, `B09`, and `B12`

### AOI-Compatible Reduced Five-Label XGBoost

This variant was created to match the current AOI's available shared bands.

Feature schema:

- `B02_mean`
- `B03_mean`
- `B04_mean`
- `B05_mean`
- `B06_mean`
- `B07_mean`
- `B08_mean`
- `B8A_mean`
- `B11_mean`

It intentionally excluded:

- `B01_mean`
- `B09_mean`
- `B12_mean`

Notebook holdout evidence:

- accuracy: `0.8354166666666667`
- macro F1: `0.7305025296798493`
- weighted F1: `0.8409700758719112`

This model ran technically on the AOI, but failed validation by predicting `Wheat` for known `Corn`.

## Experiment Timeline

| Stage | Action | Result | Scientific Meaning |
|---|---|---|---|
| Clean restart | Focused on notebook-trained XGBoost artifacts instead of old experiment entry points | Dedicated research inference path created | Reduced implementation noise and isolated the experiment |
| Deterministic AOI aggregation | Used mean aggregation over available AOI cube values | One simple reproducible AOI row | Avoided unvalidated timestamp-selection behavior |
| Morocco-only inference | Ran notebook-compatible preprocessing and prediction | Predicted `corn` for known `Corn` | Useful one-AOI smoke evidence, but not broad validation |
| Full merged model check | Tried to evaluate the broader five-label model path | Blocked by missing artifact and missing AOI bands | Execution could not produce a valid prediction |
| AOI-compatible five-label test | Used shared available bands only | Predicted `Wheat` for known `Corn` | Model ran, but failed validation |
| Diagnostics | Checked class order, feature order, clipping, and holdout confusion | No label-order or feature-order bug found | Failure is likely model/data/schema related |

## Implementation History Preserved From Old Task

This section distills the old T-07 task notes. The task file was removed because it belonged to the old implementation cycle, while the durable knowledge belongs here.

The work started with a clean restart from notebook-trained XGBoost artifacts only. Training was treated as external and was not reproduced inside the FarmTrust product pipeline.

The implemented research path was intentionally narrow:

- one dedicated research script path, later removed after its durable findings were preserved here
- one model family: XGBoost
- one deterministic AOI aggregation method: mean over available AOI values
- one notebook-compatible preprocessing contract
- one research/demo output table with class probabilities and confidence

The early implementation included timestamp-selection options, but those were removed because they made the demo path look more precise than the evidence supported. The final old-work version used mean aggregation only.

Research outputs were kept local/ignored. The archive test wrote JSON and CSV outputs under `data/research/merged_crop_classification/`, but those outputs were evidence artifacts, not production data.

Important implementation decisions preserved from T-07:

- The work remained research-only and did not modify canonical FarmTrust assessment output.
- No retraining was done during archive inference validation.
- Missing full-model bands were not imputed.
- The full merged five-label model was allowed to be blocked rather than forced to run.
- The AOI-compatible five-label model used only shared AOI features.
- The demo did not claim timestamp-selected predictions were validated.

The old task also recorded the exact notebook preprocessing order used by the Morocco-only inference path:

- compute `NDVI`
- clip common features with saved bounds
- compute engineered indices
- reorder by `feature_cols_v2.pkl`
- predict with the XGBoost artifact

Supported AOI band aliases included:

- `B02` -> `B2`
- `B03` -> `B3`
- `B04` -> `B4`
- `B05` -> `B5`
- `B06` -> `B6`
- `B07` -> `B7`
- `B08` -> `B8`

This implementation history matters for the graduation book because it shows the method became simpler over time: from exploratory scripts and timestamp ideas toward a narrow, reproducible, inference-only experiment.

## Results Summary

### Latest AOI-Passing Result

Notebook:

- `notebooks/08-morocco_crop_lightgbm_baseline.ipynb`

Configuration:

- Active labels: `Alfalfa`, `Corn`.
- Rows: `2109` (`Corn` 1252, `Alfalfa` 857).
- Features: `18` AOI-compatible columns.
- Feature schema: 9 brightness-normalized default S2 band ratios plus 9 vegetation indices.
- Excluded as direct model inputs: raw S2 bands, `area_ha`, `observation_count`, `time_span_days`, weather, geometry, non-default S2 bands, and multi-stat aggregates.
- LightGBM objective: `binary`.

Random split validation:

| Metric | Value |
|---|---:|
| Accuracy | `0.9502` |
| Macro F1 | `0.9486` |

Per-class validation:

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| `Alfalfa` | `0.9261` | `0.9532` | `0.9395` |
| `Corn` | `0.9675` | `0.9482` | `0.9577` |

Confusion matrix:

| Actual | Pred Alfalfa | Pred Corn |
|---|---:|---:|
| `Alfalfa` | `163` | `8` |
| `Corn` | `13` | `238` |

Direct AOI prediction:

| Season | Known | Predicted | Alfalfa probability | Corn probability |
|---|---|---|---:|---:|
| `C1` | `Corn` | `Corn` | `0.000153` | `0.999847` |
| `C3` | `Corn` | `Corn` | `0.008052` | `0.991948` |
| `C4` | `Alfalfa` | `Alfalfa` | `0.568402` | `0.431598` |

Scientific interpretation:

- The current Morocco-only binary model solves the current AOI label check.
- Corn is highly confident for both tested Corn seasons.
- Alfalfa passes but with moderate confidence, so C4 remains the weaker case.
- The result supports the later diagnosis that combined-model failures came from source/domain/class-boundary conflict, not from AOI Corn being unclassifiable.

### Earlier Results Preserved For Sequence

| Model | Status | Predicted | Actual | Correct | Interpretation |
|---|---|---|---|---:|---|
| `morocco_only_xgboost` | `ok` | `corn` | `Corn` | `true` | Passed this one AOI smoke validation with low confidence |
| `merged_crop_5labels_xgboost` | `blocked` |  | `Corn` |  | Missing full artifact; AOI also lacks required full-band inputs |
| `merged_crop_5labels_aoi_shared_bands_xgboost` | `ok` | `Wheat` | `Corn` | `false` | Ran technically but failed known-label validation |

Morocco-only probabilities:

- `proba_corn`: `0.42813432216644287`
- `proba_other_crop`: `0.07592978328466415`
- `proba_soil`: `0.20565509796142578`
- `proba_wheat`: `0.290280818939209`
- confidence status: `low`

AOI-compatible five-label probabilities:

- `proba_corn`: `0.014917795546352863`
- `proba_potatoes`: `0.0002640655147843063`
- `proba_rice`: `0.00008443059050478041`
- `proba_sugarcane`: `0.00020094447245355695`
- `proba_wheat`: `0.9845327734947205`

## Progress Achieved

- A clean research-only inference path was created for a notebook-trained XGBoost model.
- The AOI archive could be opened and reduced into a model input row.
- The Morocco-only artifact chain was traceable from notebook to local artifacts to inference output.
- The known Corn AOI was predicted correctly by the Morocco-only model.
- The result was not overstated because confidence was low.
- Missing-band imputation was avoided.
- Blocked inference and failed validation were separated clearly.
- Diagnostics confirmed that the AOI-compatible five-label failure was not caused by label mapping or feature order.

## Struggles And Blockers

The central struggle was feature-schema mismatch between training and inference.

The full merged five-label model expected a richer static feature schema than the current AOI could provide. The AOI lacked `B01`, `B09`, and `B12`, and the local full model artifact was missing. This made the full merged path blocked, not scientifically failed.

The reduced AOI-compatible five-label model solved the execution schema problem by using only shared bands, but it lost potentially useful information such as `NDVI_mean` and other computable indices. It then predicted `Wheat` with high confidence for a known Corn AOI.

Diagnostics showed:

- label encoder order was correct
- probability order was correct
- feature order matched the artifact contract
- six of nine AOI features clipped high
- computed AOI NDVI was available but not used by the reduced five-label model
- notebook holdout behavior already showed Corn-to-Wheat confusion: `35 / 311`, about `11.25%`

This means the failure is probably not a simple code bug. It is more likely a model generalization and feature-design problem.

## Scientific Interpretation

Latest interpretation:

The Morocco-only binary LightGBM model is the current selected AOI-passing research candidate for the C1/C3 Corn and C4 Alfalfa check. This is still research evidence, not a production FarmTrust crop-category output. The moderate C4 Alfalfa probability should stay visible in reporting.

Sequential interpretation of earlier work:

The Morocco-only model is the current selected demo model only because it is the only path that both ran and predicted the known AOI label correctly.

The result is weak evidence because it is based on one AOI and low confidence. It is still useful because it verifies that the notebook-trained tabular model can be connected to an AOI cube inference path without changing FarmTrust production output.

The merged five-label direction remains scientifically interesting, but it is not validated at this stage. Its current challenge is not just model quality; it is the mismatch between training features, artifact availability, and real AOI data availability.

The AOI-compatible reduced model teaches an important negative lesson: making a model executable by reducing features is not enough. The reduced schema must still preserve discriminative crop information and must be validated on known AOIs.

## Validity Threats

- Only one known AOI was tested.
- The Morocco-only model confidence was low.
- The AOI may not represent the training distribution.
- The full merged model was not fully tested because the artifact was missing.
- The current AOI lacks bands required by the full merged model.
- The AOI-compatible reduced model omitted `NDVI_mean`, even though it was computable from available `B08` and `B04`.
- Internal notebook metrics do not prove AOI deployment robustness.
- There is no broad external validation set of AOIs with known crop labels yet.

## Lessons Learned

- Scientific validation must distinguish technical execution from correct prediction.
- A blocked model is different from a failed model.
- Missing Sentinel-2 bands should block incompatible model paths instead of being invented.
- A single correct AOI prediction is only smoke evidence.
- Low confidence must remain visible in reporting.
- Feature-schema design is a first-order scientific issue, not just an implementation detail.
- A production-style AOI model should be trained on the same features that can be reliably computed from future AOI inputs.
- Reduced shared-band models need additional validation and may need computed indices such as `NDVI_mean`.

## Morocco Dataset Exploration And Cleaning

### Purpose

This section records the scientific and technical decisions behind `notebooks/07-morocco_dataset.ipynb`.

The notebook is now the source of truth for the dataset-preparation workflow. It downloads the two useful Figshare files, extracts them, creates one raw merged Parquet checkpoint, reloads that checkpoint, and then creates one selected crop/background Sentinel-2 time-series dataset for later modeling work.

Generated archives, extracted folders, and processed data are local notebook artifacts and should not be committed.

### Dataset Sources

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

### Notebook Workflow

Notebook:

- `notebooks/07-morocco_dataset.ipynb`

Current workflow:

1. Install `dbfread`, `pyshp`, `shapely`, `pyproj`, `requests`, and `pyarrow` in Colab.
2. Download only the two selected Figshare files.
3. Extract both archives under `data/morocco_crop_irrigation/`.
4. Read the shapefile DBF attributes and all Sentinel-2 parcel CSV files.
5. Merge them by `parcel_id`.
6. Save one raw checkpoint: `raw_merged.parquet`.
7. Reload only `raw_merged.parquet` and continue from that file.
8. Keep selected seasonal crops plus background labels.
9. Save one selected crop/background time-series file: `morocco_selected_crop_background_timeseries.parquet`.
10. Extract parcel geometry metadata from the shapefile: WKT, centroid, bounding box, and area.
11. Convert the existing Morocco Sentinel-2 CSV bands into YieldSAT-style `s2_*_mean` columns and derived vegetation indices.
12. Fetch Open-Meteo historical weather by representative survey-zone centroid and join daily/rolling/cumulative weather features to each observation.
13. Save one final enriched feature file: `features.parquet`.

Important cleanup decision:

- The temporary script-based build path was removed.
- Old generated folders were removed.
- The notebook is the reproducible path for this dataset stage.

### Weather Enrichment Struggle And Resolution

Morocco's Figshare Sentinel-2 CSVs already contain per-parcel spectral time series, but they do not contain weather. To align Morocco with the YieldSAT feature style, notebook 07 added weather through the Open-Meteo archive API.

The first design question was whether to fetch weather per parcel or use a lighter approximation. Per-parcel weather would require thousands of API requests and make Colab runs slow and fragile. The chosen compromise was one representative weather point per `survey_zone`, using the median parcel centroid in that zone. Every parcel in the same zone gets the same weather values for the same date.

Weather implementation details:

- Source: Open-Meteo archive API.
- Location mode: `survey_zone_median_centroid`.
- Locations fetched: `Doukkala`, `Gharb`, `Souss`, `Statte`, `Tadla`, `el haouz`.
- Date range: `2023-12-03` to `2024-12-26`, starting 29 days before the first satellite date so 30-day rolling windows are available.
- Joined rows: `390766`.
- Missing weather rows after join: `0`.
- Weather feature columns in `features.parquet`: `28`.

This is a regional-weather approximation, not per-field microclimate. It is acceptable for this research baseline because it is fast, reproducible, and comparable to YieldSAT-style weather features. It should not be interpreted as exact parcel-level weather.

### SCL Quality Struggle And Resolution

The initial enrichment direction tried to add Sentinel-2 SCL/cloud-quality features. This became expensive and fragile in Colab because the full pass required many parcel-date targets. A Google Earth Engine diagnostic later showed the correct way to filter images with SCL is `ee.Filter.listContains("system:band_names", "SCL")`; the earlier `ee.Filter.notNull(["SCL"])` approach checks metadata rather than band availability and can wrongly produce no useful items.

After comparing against YieldSAT exploration, SCL was removed from the main Morocco feature-generation notebook because SCL/cloud fractions were low-importance relative to Sentinel-2 bands, vegetation indices, and weather. The notebook now preserves only a future note for SCL extraction rather than running it by default.

### Raw Data Facts Preserved

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

### Label Interpretation

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

### Reviewed Crop Set

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
- Do not group these crops into `Other` in the dataset-preparation notebook; defer that to a later modeling notebook.

Similarity notes:

| Future group direction | Reviewed crops kept for later |
|---|---|
| Close to `Wheat` | `Beets`, `Potatoes`, `Peas`, `Onions`, `Fava Beans` |
| Close to `Corn` | `Peanut`, `Tomatoes`, `Sugarcane`, `Rice` |
| Close to `Alfalfa` | `Peas`, `Peanut`, `Fava Beans`, `Parsley` |

Some crops can support more than one future group, such as `Peas`, `Peanut`, and `Fava Beans`.

### Final Dataset Outputs

The dataset notebook now writes exactly three Parquet files:

- `data/morocco_crop_irrigation/raw_merged.parquet`
- `data/morocco_crop_irrigation/morocco_selected_crop_background_timeseries.parquet`
- `data/morocco_crop_irrigation/features.parquet`

The selected crop/background time-series file keeps the simple source columns for compatibility with earlier modeling checks:

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

The enriched `features.parquet` output contains:

- Rows: `390766`
- Columns: `70`
- Sentinel-2 band mean columns: `13`
- Vegetation-index columns: `11`
- Weather columns: `28`
- Geometry metadata columns: `7`
- SCL/cloud-quality columns: `0`

SCL/cloud-quality extraction was removed from the main notebook because the full pass is expensive and the YieldSAT exploration showed SCL was a low-importance feature group relative to Sentinel-2 bands, vegetation indices, and weather. If SCL features are needed later, use Google Earth Engine with `ee.Filter.listContains("system:band_names", "SCL")`, not `ee.Filter.notNull(["SCL"])`, because `SCL` is a band name rather than an image metadata key. Earth Engine `frequencyHistogram()` can return fractional edge-pixel counts, so later SCL fractions should be computed from weighted counts rather than assuming integer pixels.

### Dataset Stage Status

This stage produced both the selected crop/background time-series file and the enriched `features.parquet` used by the updated LightGBM baseline.

The next modeling step grouped reviewed non-main crops into `Other crop`, grouped `Bare soil`, `Water`, and `Weed` into `Background`, cleaned duplicate parcel-date rows, clipped unstable EVI outliers, and trained a LightGBM baseline on parcel-level aggregate features.

## Morocco LightGBM Baseline

### Notebook

Notebook:

- `notebooks/08-morocco_crop_lightgbm_baseline.ipynb`

Input:

- `data/morocco_crop_irrigation/features.parquet`

Loaded data:

- Time-series rows: `390766`
- Columns: `70`
- Unique parcels: `7734`

### Target Grouping

The baseline uses five model labels:

- `Wheat`
- `Corn`
- `Alfalfa`
- `Other crop`
- `Background`

Grouping rule:

- `Wheat`, `Corn`, and `Alfalfa` stay as main crop classes.
- Reviewed non-main seasonal crops become `Other crop`.
- `Bare soil`, `Water`, and `Weed` become `Background`.

Parcel counts after grouping:

| model label | parcels |
|---|---:|
| `Wheat` | `2614` |
| `Other crop` | `1707` |
| `Background` | `1304` |
| `Corn` | `1252` |
| `Alfalfa` | `857` |

### Feature Construction

Before parcel-level modeling, notebook 08 applies two quality fixes:

- duplicate `parcel_id + satellite_date` rows are averaged from `390766` source rows down to `309914` unique parcel-date rows
- `s2_EVI_mean` is clipped to `[-1, 1]` because the original EVI formula produced denominator-instability outliers from `-27.458071` to `38.113894`

The cleaned time series is then aggregated to one row per parcel.

Aggregates used for each numeric Sentinel-2, vegetation-index, weather, and area feature:

- mean
- median
- standard deviation
- minimum
- maximum

Additional coverage features:

- `observation_count`
- `time_span_days`

Model table:

- Rows: `7734`
- Columns: `268`
- Model features: `263`

Excluded from model features:

- `parcel_id`
- original `label`
- `model_label`
- `irrigation_type`
- `survey_zone`
- centroid and bounding-box coordinate fields

Reason:

- `irrigation_type`, `survey_zone`, centroids, and bounding boxes are useful for diagnostics, but excluding them from the first baseline reduces shortcut learning from metadata/geography.

### Random Stratified Split Result

The first baseline used a parcel-level random stratified train/test split:

- Train parcels: `6187`
- Test parcels: `1547`

This split trains on all zones normally, because parcels from each zone can appear in both train and test sets. It measures same-distribution held-out performance, not new-zone generalization.

LightGBM result:

- Accuracy: `0.7989657401422108`
- Macro F1: `0.7929820237919876`

Per-class F1:

| class | F1 |
|---|---:|
| `Alfalfa` | `0.8466` |
| `Wheat` | `0.8365` |
| `Corn` | `0.8196` |
| `Other crop` | `0.7983` |
| `Background` | `0.6640` |

Main weakness:

- `Background` remains the weakest class, with recall `0.6245` and F1 `0.6640`.

Largest confusions:

| actual | predicted | count |
|---|---|---:|
| `Background` | `Wheat` | `47` |
| `Background` | `Corn` | `23` |
| `Wheat` | `Background` | `31` |
| `Wheat` | `Other crop` | `24` |
| `Other crop` | `Wheat` | `23` |
| `Other crop` | `Background` | `23` |

### Diagnostic Findings

Accuracy by survey zone varied strongly even though `survey_zone` was not used as a feature:

| survey zone | accuracy |
|---|---:|
| `Souss` | `0.511628` |
| `Statte` | `0.589286` |
| `Doukkala` | `0.777209` |
| `el haouz` | `0.791667` |
| `Gharb` | `0.885375` |
| `Tadla` | `0.891892` |

This suggests possible geographic/domain shift. The random split is valid as a first baseline, but it is not enough to claim the model generalizes to unseen regions.

Top feature importances included:

- `area_ha`
- `s2_B11_mean_min`
- `s2_B12_mean_std`
- `s2_GNDVI_mean_std`
- `s2_B02_mean_min`
- `s2_CAI_B01_B08_mean_max`
- `s2_B09_mean_min`
- `s2_NBR_mean_min`
- `s2_B01_mean_min`
- `s2_B01_mean_median`

Potential caution:

- `area_ha` is the top LightGBM importance in the random split, so field-size differences may encode label or zone structure in addition to agronomic signal. This does not make the model invalid, but it should be tested in ablations before making strong generalization claims.

### Leave-One-Zone-Out Cross-Validation Result

Notebook `08-morocco_crop_lightgbm_baseline.ipynb` now uses scikit-learn `LeaveOneGroupOut` with `survey_zone` as the group variable. Each fold trains on all zones except one and evaluates on the held-out zone.

Strict all-label macro F1 by held-out zone:

| held-out zone | train parcels | test parcels | accuracy | macro F1 |
|---|---:|---:|---:|---:|
| `Gharb` | `6442` | `1292` | `0.250000` | `0.188885` |
| `Doukkala` | `3786` | `3948` | `0.353850` | `0.327867` |
| `Souss` | `7567` | `167` | `0.413174` | `0.327961` |
| `Statte` | `7486` | `248` | `0.588710` | `0.462004` |
| `Tadla` | `6573` | `1161` | `0.730405` | `0.534433` |
| `el haouz` | `6816` | `918` | `0.700436` | `0.580155` |

Held-out class support by zone:

| held-out zone | Alfalfa | Background | Corn | Other crop | Wheat | total |
|---|---:|---:|---:|---:|---:|---:|
| `Doukkala` | `571` | `693` | `525` | `712` | `1447` | `3948` |
| `Gharb` | `63` | `58` | `664` | `505` | `2` | `1292` |
| `Souss` | `4` | `70` | `48` | `33` | `12` | `167` |
| `Statte` | `17` | `128` | `0` | `46` | `57` | `248` |
| `Tadla` | `116` | `108` | `2` | `170` | `765` | `1161` |
| `el haouz` | `86` | `247` | `13` | `241` | `331` | `918` |

Per-zone class F1:

| held-out zone | Alfalfa | Background | Corn | Other crop | Wheat |
|---|---:|---:|---:|---:|---:|
| `Gharb` | `0.269608` | `0.207650` | `0.000000` | `0.467167` | `0.000000` |
| `Doukkala` | `0.695985` | `0.370642` | `0.000000` | `0.475997` | `0.096712` |
| `Souss` | `0.500000` | `0.718750` | `0.000000` | `0.421053` | `0.000000` |
| `Statte` | `0.736842` | `0.734694` | `0.000000` | `0.495050` | `0.343434` |
| `Tadla` | `0.685446` | `0.507123` | `0.000000` | `0.663212` | `0.816386` |
| `el haouz` | `0.853659` | `0.756757` | `0.000000` | `0.579310` | `0.711048` |

Worst held-out zone: `Gharb`, with macro F1 `0.188885`.

`Gharb` confusion matrix:

| actual / predicted | Alfalfa | Background | Corn | Other crop | Wheat |
|---|---:|---:|---:|---:|---:|
| `Alfalfa` | `55` | `1` | `0` | `4` | `3` |
| `Background` | `0` | `19` | `0` | `13` | `26` |
| `Corn` | `94` | `79` | `0` | `294` | `197` |
| `Other crop` | `195` | `26` | `0` | `249` | `35` |
| `Wheat` | `1` | `0` | `0` | `1` | `0` |

Interpretation:

- Random stratified split answers same-distribution performance and reached macro F1 `0.7929820237919876` after duplicate parcel-date cleanup, EVI clipping, and enriched feature use.
- Leave-one-zone-out validation answers whether the model survives stronger geographic/domain shift; performance drops sharply, especially for held-out `Gharb`.
- `Gharb` is the strongest warning because it has substantial `Corn` support (`664` parcels), yet held-out `Corn` F1 is `0.000000`; all actual `Corn` parcels were predicted as other classes.
- Some per-zone class zeros are affected by zero or tiny support in that zone, so class support must be reported with any per-zone macro score.
- Current evidence supports a same-distribution Morocco baseline, not a robust unseen-zone crop classifier.

## Graduation Book Material To Preserve

Potential narrative:

- The final branch result was not a single straight success. It came after preserving failed and blocked paths, tightening AOI-compatible feature contracts, and narrowing the class boundary to the labels supported by the current AOI check.
- The project tested a practical bridge from notebook-trained crop classification models to AOI-level inference.
- The first Morocco-only model produced a correct Corn prediction, but low confidence showed that correctness alone is insufficient.
- The broader merged model idea exposed a real research challenge: the training schema must match the data that production-like AOIs can actually provide.
- A reduced AOI-compatible model ran successfully but failed scientifically, demonstrating why execution success is not validation success.
- The latest Morocco-only binary LightGBM run passed the current AOI label check with very high Corn confidence and moderate Alfalfa confidence.

Potential table:

| Experiment | Outcome | Lesson |
|---|---|---|
| Morocco-only binary LightGBM | Passed C1/C3 Corn and C4 Alfalfa AOI check | Narrow, AOI-compatible class boundaries can solve the current demo label check |
| Morocco-only XGBoost | Correct Corn prediction, low confidence | Useful proof of inference path, not production validation |
| Full merged five-label model | Blocked | Required artifacts and bands must exist before testing |
| AOI-compatible five-label model | Wrong Wheat prediction | Schema compatibility alone does not guarantee crop separability |

Potential figure ideas:

- AOI inference pipeline diagram: `cube.zarr -> band aggregation -> indices -> XGBoost -> probabilities`.
- Model comparison table showing `ok`, `blocked`, and `failed validation` as separate outcomes.
- Feature-schema mismatch diagram comparing full merged model features with available AOI bands.

## Next Experiments

For the current Morocco-only path:

- Keep the low confidence visible.
- Test more known-label AOIs.
- Record confusion patterns across AOIs, not only a single prediction.

For the full merged five-label path:

- Restore or regenerate the full model artifact if this path remains important.
- Test only with AOIs that include the full required band set.
- Do not force prediction by imputing absent bands.

For the AOI-compatible five-label path:

- Treat the current model as failed validation.
- Add computed `NDVI_mean` and other indices available from shared bands.
- Validate against more known Corn and Wheat AOIs to investigate Corn/Wheat confusion.
- Recheck whether feature clipping indicates out-of-distribution AOI values.

For the graduation-book storyline:

- Present this stage as an honest research iteration.
- Highlight the methodological discipline: trace artifacts, validate with known labels, preserve failures, and do not promote weak evidence into production claims.
