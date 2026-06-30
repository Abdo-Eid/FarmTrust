# YieldSAT Yield Modeling Scientific Log

Date started: 2026-06-30

## Purpose

This document tracks the research framing, dataset boundary, modeling choices, AOI compatibility constraints, validation logic, AOI inference path, limitations, and later interpretation for the YieldSAT yield-modeling work.

It is written as a scientific/research log rather than a repo activity log so it can later support the graduation book. Temporary implementation mechanics belong in active tasks while durable research framing and evidence belong here.

## Scope

Current scope:

- Yield modeling remains research-only.
- Yield prediction is not part of the current FarmTrust lender-facing land-assessment contract.
- The current notebook path uses the prebuilt YieldSAT field-level model tables rather than rebuilding features from the raw raster archive.
- The current baseline is intentionally narrowed to `corn` and `wheat` only.
- The current AOI check is a research inference exercise on the last known Corn season under `data/aoi_demo_01/`.
- Local model artifacts, notebook outputs, and generated research files should stay out of git unless they are lightweight notebook/source files.

## Dataset Boundary

Primary dataset reference:

- `docs/documentations/03-yieldsat-dataset.md`

Current modeling inputs:

- `notebooks/data/yieldsat_final_3_model_tables/model_mid_season.parquet`
- `notebooks/data/yieldsat_final_3_model_tables/model_near_harvest.parquet`
- `notebooks/data/yieldsat_final_3_model_tables/model_full_season.parquet`

Confirmed model-table facts from the current workspace:

- Each table has `1583` rows.
- Crops in the ready tables: `soybean`, `wheat`, `corn`, `rapeseed`.
- Current narrowed training subset: `wheat` `454` rows and `corn` `303` rows, total `757` rows.
- Ready-table countries are `Argentina`, `Brazil`, and `Germany`.
- `Uruguay` is absent from the ready model tables because those rows were filtered out during the original extraction path.
- Target column: `target_yield_t_ha`.

Prediction-moment table shapes:

- `model_mid_season.parquet`: `(1583, 1204)`
- `model_near_harvest.parquet`: `(1583, 1204)`
- `model_full_season.parquet`: `(1583, 1188)`

## Current Research Question

Can a yield-regression baseline trained from AOI-compatible YieldSAT features predict yield for `corn` and `wheat` under grouped internal validation, and can that same feature contract be applied to the last Corn season in `data/aoi_demo_01/`?

## Current Working Constraints

The AOI archive is not a full copy of the YieldSAT raw field schema. The current AOI directory contains:

- `cube.zarr`
- `indices_timeseries.csv`
- `weather_daily.parquet`
- `run_metadata.json`
- `scenes_index.jsonl`

Important AOI boundary:

- Available Sentinel-2 bands from the AOI archive are `B02`, `B03`, `B04`, `B05`, `B06`, `B07`, `B08`, `B8A`, and `B11`.
- Bands required by some YieldSAT features but missing from the AOI archive include `B01`, `B09`, and `B12`.
- The AOI directory contains weather time series, but it does not contain the YieldSAT soil raster summaries or DEM summary table in the same ready-to-join form as the model tables.

Current modeling consequence:

- The baseline notebook must use an AOI-compatible feature contract instead of the full ready-table schema.
- The first baseline should avoid soil, DEM, provider/farm identity, and geographic shortcut features unless they are explicitly recreated for the AOI and justified later.

## Intended Notebook Path

Planned notebook:

- `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb`

Planned notebook responsibilities:

1. Audit the three YieldSAT yield tables.
2. Filter training data to `corn` and `wheat` only.
3. Define an AOI-compatible feature subset shared by training and AOI inference.
4. Compare `CatBoost`, `XGBoost`, and `LightGBM` regressors under grouped validation.
5. Fit the selected baseline on the chosen training table.
6. Build one AOI season feature row for the last Corn season under `data/aoi_demo_01/`.
7. Produce an AOI yield prediction as research evidence only.

## Leakage Boundary

Columns that must not be used as numeric regression targets or shortcut identifiers:

- `target_yield_t_ha` as an input feature.
- Field identity columns such as `field_id`, `field_shared_name`, `farm`, and `field_num`.
- Direct location shortcut fields such as raw admin-unit strings, centroids, and CRS in the first AOI-compatible baseline.
- Ready-table-only feature groups that the AOI cannot currently reproduce, including the default SoilGrids and DEM summary groups.

Allowed first-baseline inputs should be limited to features that can be recreated for the AOI from:

- AOI Sentinel-2 cube bands.
- AOI-derived vegetation-index summaries.
- AOI observation-quality and revisit-gap summaries.
- Explicitly known season window metadata.
- The known crop label for the tested AOI season if the experiment is treated as a crop-conditioned yield baseline.

Weather handling decision for the current baseline:

- Raw weather aggregates are intentionally excluded from the default AOI baseline.
- Reason: the current YieldSAT training geography covers `Argentina`, `Brazil`, and `Germany`, while the tested AOI is in Egypt-like geography, so raw weather is too likely to act as a non-transferable climate shortcut.
- Weather can return later only as a separate experiment after it is normalized into more geography-robust signals.

## Validation Logic

Current validation plan:

- Use grouped validation rather than a random row split.
- Group by `country_year` so the same country-year slice cannot appear in both train and validation folds.
- Report regression metrics such as RMSE, MAE, and R2.
- Keep AOI inference separate from internal grouped validation because one AOI prediction is not a substitute for held-out validation.

Known structural risk:

- Crop and geography are partly entangled in YieldSAT. Germany contributes only `wheat`, while `corn` is present in Argentina and Brazil only.
- Strong internal metrics could still reflect domain shortcuts or crop-country coupling rather than robust new-region generalization.

## AOI Test Target

Current AOI test target:

- Directory: `data/aoi_demo_01/`
- Current requested test season: the last known Corn season in this AOI archive.
- Selected season ID in the new notebook: `C3`.
- Selected season window: `2025-06-15` to `2025-09-11`.

Notebook implementation boundary:

- Notebook path: `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb`.
- Active training table: `model_full_season.parquet`.
- Training crops: `corn` and `wheat` only.
- First AOI-compatible feature groups: `crop`, `season_length_days`, AOI-available Sentinel-2 band summaries, AOI-compatible vegetation-index summaries, and S2 quality/gap features.
- Excluded from the first AOI-compatible baseline: SoilGrids, DEM summaries, admin-unit metadata, centroids, CRS, area, provider/farm identity, missing AOI bands `B01`, `B09`, `B12`, and raw weather aggregates.

## Testing Log

| Date | Action | Result | Evidence | Follow-up |
|---|---|---|---|---|
| 2026-06-30 | Inspected the ready YieldSAT model tables in the workspace | Confirmed three flat regression tables with shared row count and `target_yield_t_ha` target | Local parquet inspection in `notebooks/data/yieldsat_final_3_model_tables/` | Build notebook against AOI-compatible subset |
| 2026-06-30 | Inspected the AOI directory for inference compatibility | Confirmed AOI has `cube.zarr`, `indices_timeseries.csv`, and `weather_daily.parquet`, but not the full YieldSAT-ready soil/DEM summary schema | Local inspection of `data/aoi_demo_01/` | Restrict first baseline to AOI-compatible features |
| 2026-06-30 | Created the first AOI-compatible yield notebook | Added a new notebook with grouped `corn`/`wheat` regression, AOI feature reconstruction, and last-Corn-season inference cells | `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb` | Keep unexecuted until the user chooses to run it |
| 2026-06-30 | Removed raw weather from the default AOI baseline design | Reframed the first AOI test as imagery-only plus season/crop metadata because Egypt AOI transfer is less defensible with raw weather learned from non-Egypt geographies | Current notebook and this log | Revisit weather only after normalization or anomaly-style redesign |
| 2026-06-30 | Executed the notebook through grouped validation and AOI feature reconstruction | Confirmed the notebook now runs through cell `16`, produces grouped CV results, and rebuilds one AOI season feature row for `C3` | User-run notebook outputs in `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb` | Re-run cell `18` after the final prediction-cell simplification |
| 2026-06-30 | Fixed notebook compatibility and workflow issues found during user execution | Repaired the AOI index-summary AUC calculation, restored the feature-importance cell, removed stale raw-weather dependencies, and simplified the final prediction cell to reuse `best_pipeline` | Current notebook source and executed outputs | Validate final AOI prediction output from cell `18` |
| 2026-06-30 | Read the final AOI prediction output from cell `18` | The final cell completed quickly and predicted a much higher AOI yield than the user's observed field context | Executed output of cell `18` in `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb` | Diagnose why predicted AOI yield is implausibly high for the local benchmark |
| 2026-06-30 | Tested a corn-only variant to reduce crop-mix transfer effects | The AOI prediction stayed effectively the same while grouped CV got worse, so wheat presence was not the main reason for the remaining mismatch | Executed outputs in temporary notebook `notebooks/12-yieldsat_yield_corn_aoi_baseline.ipynb` | Prefer a stronger feature-contract ablation next, especially removing raw band summaries |
| 2026-06-30 | Compared the combined AOI corn sample (`C1` + `C3`) against the YieldSAT corn feature distribution | The dominant mismatch is seasonal timing support, not general spectral brightness. Brightness normalization on the 9 band means did not improve the AOI sample shift overall | Read the current notebook feature contract, rebuilt `C1` and `C3` from `cube.zarr` plus `indices_timeseries.csv`, filtered `model_full_season.parquet` to corn rows only, and computed per-feature percentiles, z-scores, support checks, and standardized-space distances | Prioritize calendar-sensitive feature ablations before a raw-band-only ablation |
| 2026-06-30 | Applied the first timing-robust feature ablation to the main yield notebook | Removed the absolute calendar-sensitive features identified by the AOI-vs-YieldSAT comparison and kept the rest of the AOI-safe imagery contract for the next user-run baseline | Updated the feature-contract cells in `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb`, then verified the remaining contract shape against `model_full_season.parquet` | Re-run the notebook and compare grouped CV plus AOI prediction against the earlier baseline |
| 2026-06-30 | Inspected the executed outputs from the timing-robust first pass | Removing the timing-sensitive features preserved grouped validation almost unchanged and moved the AOI prediction down only modestly, so timing support was part of the mismatch but not the whole explanation | User-run outputs from the updated `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb` through cell `18` | Test a second pass that keeps the timing-robust contract but removes raw band summaries |
| 2026-06-30 | Tested a compact-soil variant on top of the timing-robust contract | Adding coarse SoilGrids topsoil features moved the AOI prediction down more than timing removal alone, but grouped validation did not improve and the soil source is coarse enough to behave partly like a location prior | Temporary executed notebook state plus `scripts/fetch_aoi_soil.py` and `data/aoi_demo_01/soil_features.parquet` inspection | Keep the soil result as evidence, but continue the next controlled ablation from the reverted no-soil notebook by removing raw band summaries |
| 2026-06-30 | Prepared the next no-raw-band transfer test in the main notebook | Reverted to the no-soil notebook state and changed the feature contract to vegetation-index plus non-calendar quality only, while still deriving indices from the AOI cube bands | Updated the feature-contract cells in `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb` and verified the new schema against `model_full_season.parquet` | Re-run the notebook and compare the result against the timing-robust no-soil and temporary compact-soil variants |
| 2026-06-30 | Inspected the executed outputs from the no-raw-band timing-robust pass | Removing raw Sentinel-2 band summaries moved the AOI prediction down more meaningfully than the timing-only pass, with only a small grouped-validation penalty, making it the cleaner current default despite the slightly weaker CV score | User-run outputs from the updated `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb` through cell `18` | Use this reduced feature contract as the current preferred no-soil baseline unless a later targeted test clearly improves the trade-off |
| 2026-06-30 | Removed direct `valid_pixel_fraction` summaries from the current no-raw-band notebook source | `valid_pixel_fraction` now stays only in the reconstruction path as an internal support signal; it is no longer part of model input, which keeps the reduced contract cleaner | Updated the feature-contract cells in `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb` and verified the new schema against `model_full_season.parquet` | Re-run the notebook to compare the `96`-feature contract against the earlier `98`-feature no-raw-band run |
| 2026-06-30 | Inspected the executed outputs from the direct-valid-pixel-free no-raw-band pass | Removing direct `valid_pixel_fraction` features made the reduced model slightly worse and moved the AOI prediction slightly back up, but it preserved the desired contract boundary where S2 cleanliness acts only as support, not as target-discriminating signal | User-run outputs from the updated `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb` through cell `18` | Treat this `96`-feature run as the current principled stopping point |
| 2026-06-30 | Appended and executed a `PLSRegression` appendix against the current `96`-feature contract | The best PLS setting (`8` components) underperformed the current `catboost` baseline in grouped CV and predicted an even higher AOI yield, so it does not improve the transfer trade-off | User-run appendix output from cell `20` in `notebooks/11-yieldsat_yield_corn_wheat_aoi_baseline.ipynb` | Keep PLS as a comparison appendix only; do not promote it to the main baseline |

## Current Interpretation

The technically correct first step is not a full-schema yield model. The AOI archive supports only a subset of the YieldSAT ready-table contract, so the first defensible notebook should train and infer on the intersection that both sides can truly provide.

This means the current baseline is best framed as:

- a `corn`/`wheat` yield-regression research baseline,
- using AOI-compatible Sentinel-2, derived vegetation-index, and quality features,
- with grouped internal validation,
- followed by one research AOI yield estimate on the last Corn season.

Current execution note:

- The notebook has now been user-executed through grouped validation, feature-importance inspection, AOI feature-row reconstruction, and final AOI prediction for both the original imagery-only baseline and the timing-robust first pass.
- The final AOI prediction cell reuses the already-fitted best model rather than retraining all three models again.
- The current comparison of interest is now the gap between the original imagery-only baseline and the timing-robust first pass, because that shows how much of the Egypt transfer error was tied to absolute calendar-sensitive features.

Current partial results:

- Grouped CV best model so far: `lightgbm`.
- Grouped CV summary for the imagery-only baseline:
  - `lightgbm`: `RMSE 1.783`, `MAE 1.381`, `R2 0.630`
  - `xgboost`: `RMSE 1.823`, `MAE 1.430`, `R2 0.614`
  - `catboost`: `RMSE 1.825`, `MAE 1.457`, `R2 0.612`
- Error asymmetry is visible by crop in the out-of-fold review:
  - `corn` mean absolute error about `1.926 t/ha`
  - `wheat` mean absolute error about `1.013 t/ha`
- AOI season reconstruction for `C3` completed successfully before final prediction:
  - season window: `2025-06-15` to `2025-09-11`
  - AOI season rows: `41`
  - valid AOI rows: `39`
  - AOI feature row columns: `182`
- Final AOI prediction from cell `18`:
  - selected model: `lightgbm`
  - predicted yield: `8.712 t/ha`
  - predicted yield: `3659.0 kg/feddan`
  - predicted whole-plot yield after plot-area conversion: about `1113.2 kg`
  - corn training percentile: `0.488`
  - final prediction-cell runtime was not the issue; the observed prediction step completed in a few hundredths of a second during inspection.
- Timing-robust first-pass grouped CV summary after removing `11` absolute calendar-sensitive features:
  - best grouped-CV model remained `lightgbm`
  - `lightgbm`: `RMSE 1.798`, `MAE 1.393`, `R2 0.625`
  - `catboost`: `RMSE 1.810`, `MAE 1.440`, `R2 0.620`
  - `xgboost`: `RMSE 1.810`, `MAE 1.414`, `R2 0.621`
- Timing-robust out-of-fold crop error remained asymmetric:
  - `corn` mean absolute error stayed about `1.926 t/ha`
  - `wheat` mean absolute error was about `1.036 t/ha`
- Timing-robust AOI inference from cell `18`:
  - selected model: `lightgbm`
  - predicted yield: `8.490 t/ha`
  - predicted yield: `3565.6 kg/feddan`
  - predicted whole-plot yield: `1084.8 kg`
  - plot area from notebook calculation: about `1277.8 m^2`, `0.1278 ha`, `0.304 feddan`
  - corn training percentile: `0.459`
- Compared with the original imagery-only baseline, the timing-robust pass changed the AOI result only modestly:
  - AOI prediction moved down by about `0.222 t/ha`
  - AOI prediction moved down by about `93.4 kg/feddan`
  - AOI whole-plot estimate moved down by about `28.4 kg`
  - corn-training percentile moved from `0.488` to `0.459`
  - grouped validation changed only slightly, with `lightgbm` RMSE moving from `1.783` to `1.798`
- Timing-robust feature-importance summary:
  - source-level importance remained dominated by `s2_index`, then `s2_band`, then `s2_quality`
  - importance by source: `s2_index 7638`, `s2_band 5917`, `s2_quality 767`, `crop 112`
  - top transformed feature was still `s2_valid_pixel_fraction_mean`, followed by index spread/slope features and band variability features such as `s2_GNDVI_std`, `s2_EVI_std`, `s2_B4_std_mean_of_dates`, and `s2_B8_max_mean_of_dates`
- Interpretation after the first timing-robust run: removing absolute calendar-sensitive features helped directionally but not materially. The overprediction shrank slightly, while grouped CV remained almost unchanged, so the remaining mismatch is likely still carried by non-calendar spectral distribution differences and/or a broader YieldSAT-to-Egypt target/domain gap.
- Compact-soil variant result before the notebook was reverted:
  - added `6` compact soil numeric features:
    - `soil_sand_pct_0_30cm`
    - `soil_clay_pct_0_30cm`
    - `soil_soc_gkg_0_30cm`
    - `soil_phh2o_0_30cm`
    - `soil_cec_cmolkg_0_30cm`
    - `soil_nitrogen_gkg_0_30cm`
  - added `1` categorical soil feature: `soil_texture_class_0_30cm`
  - numeric feature count increased from `170` to `176`
  - grouped CV did not improve:
    - best grouped-CV model changed to `xgboost`
    - `xgboost`: `RMSE 1.807`, `MAE 1.410`, `R2 0.621`
    - `lightgbm`: `RMSE 1.817`, `MAE 1.392`, `R2 0.616`
    - `catboost`: `RMSE 1.834`, `MAE 1.454`, `R2 0.609`
  - AOI prediction did move down more than the timing-robust no-soil pass:
    - predicted yield: `7.997 t/ha`
    - predicted yield: `3358.8 kg/feddan`
    - predicted whole-plot yield: `1021.9 kg`
    - corn training percentile: `0.419`
  - compared with the timing-robust no-soil pass, the compact-soil variant moved the AOI estimate down by about:
    - `0.493 t/ha`
    - `206.8 kg/feddan`
    - `62.9 kg` for the whole plot
  - fitted-model importance shows soil helped only modestly rather than dominating the model:
    - source-level importance: `s2_index 0.586`, `crop 0.213`, `s2_band 0.142`, `soil_compact 0.036`, `s2_quality 0.023`
    - the most visible soil feature in the top transformed features was `soil_nitrogen_gkg_0_30cm`, but it remained well below the dominant crop and vegetation-index terms
  - interpretation: the soil block likely contributed some useful prior signal, but it did not improve grouped validation and therefore does not yet justify itself as a stronger default than the no-soil timing-robust notebook.
- No-raw-band timing-robust result:
  - raw Sentinel-2 band-summary features removed from model input: `72`
  - remaining numeric feature count: `98`
  - grouped CV best model changed to `catboost`
  - grouped CV summary:
    - `catboost`: `RMSE 1.837`, `MAE 1.441`, `R2 0.609`
    - `lightgbm`: `RMSE 1.848`, `MAE 1.405`, `R2 0.601`
    - `xgboost`: `RMSE 1.874`, `MAE 1.450`, `R2 0.593`
  - out-of-fold crop error remained asymmetric:
    - `corn` mean absolute error about `1.938 t/ha`
    - `wheat` mean absolute error about `1.106 t/ha`
  - AOI inference from cell `18`:
    - selected model: `catboost`
    - predicted yield: `7.942 t/ha`
    - predicted yield: `3335.5 kg/feddan`
    - predicted whole-plot yield: `1014.8 kg`
    - corn training percentile: `0.406`
  - compared with the timing-robust no-soil pass, the no-raw-band pass moved the AOI estimate down by about:
    - `0.548 t/ha`
    - `230.1 kg/feddan`
    - `70.0 kg` for the whole plot
  - compared with the temporary compact-soil variant, the no-raw-band pass ended up slightly lower on AOI prediction even without the coarse SoilGrids prior:
    - about `0.055 t/ha` lower
    - about `23.3 kg/feddan` lower
    - about `7.1 kg` lower for the whole plot
  - feature-importance summary under the reduced contract:
    - source-level importance collapsed to `s2_index 60.535`, `crop 33.964`, `s2_quality 5.501`
    - top transformed features were `crop` one-hot columns plus vegetation-index AUC and shape features such as `s2_EVI_auc`, `s2_NDWI_auc`, `s2_SAVI_auc`, and `s2_NDVI_auc`
    - `s2_valid_pixel_fraction_mean` remained the strongest quality term
  - interpretation: the no-raw-band pass did not improve grouped CV, but the validation hit was small relative to the size of the feature reduction and the AOI prediction moved down more than in the timing-only pass. Because it removes `72` raw band summary features and still lands slightly below the temporary compact-soil result, this is the cleaner current default no-soil baseline.
- Direct-valid-pixel-free no-raw-band result:
  - direct `valid_pixel_fraction` summaries removed from model input: `2`
    - `s2_valid_pixel_fraction_mean`
    - `s2_valid_pixel_fraction_min`
  - remaining numeric feature count: `96`
  - grouped CV best model remained `catboost`
  - grouped CV summary:
    - `catboost`: `RMSE 1.857`, `MAE 1.451`, `R2 0.600`
    - `lightgbm`: `RMSE 1.889`, `MAE 1.449`, `R2 0.584`
    - `xgboost`: `RMSE 1.908`, `MAE 1.477`, `R2 0.579`
  - out-of-fold crop error remained asymmetric:
    - `corn` mean absolute error about `1.982 t/ha`
    - `wheat` mean absolute error about `1.094 t/ha`
  - AOI inference from cell `18`:
    - selected model: `catboost`
    - predicted yield: `8.079 t/ha`
    - predicted yield: `3393.3 kg/feddan`
    - predicted whole-plot yield: `1032.3 kg`
    - corn training percentile: `0.429`
  - compared with the earlier `98`-feature no-raw-band pass, removing the direct valid-pixel terms changed the result by about:
    - `+0.137 t/ha`
    - `+57.8 kg/feddan`
    - `+17.5 kg` for the whole plot
    - grouped-CV RMSE moved from `1.837` to `1.857`
  - feature-importance summary under the `96`-feature contract:
    - source-level importance: `s2_index 63.962`, `crop 32.547`, `s2_quality 3.491`
    - top transformed features were `crop` one-hot columns plus vegetation-index AUC/shape terms such as `s2_EVI_auc`, `s2_NDRE_auc`, `s2_NDWI_auc`, and `s2_GNDVI_auc`
    - the strongest remaining quality term was `s2_mean_gap_days`
  - interpretation: removing the direct valid-pixel features costs a little validation quality and AOI plausibility compared with the `98`-feature no-raw-band pass, but it better matches the intended modeling principle that Sentinel-2 cleanliness should support reconstruction rather than act as a yield-discriminating signal.
- PLS appendix result on the same `96`-feature contract:
  - appendix model family: `PLSRegression` with preprocessing plus `StandardScaler`
  - tested component sweep: `2`, `4`, `8`, `12`, `16`, `24`, `32`
  - best PLS setting: `8` components
  - grouped CV summary for the best PLS run:
    - `RMSE 2.070`
    - `MAE 1.545`
    - `R2 0.488`
  - AOI inference from appendix cell `20`:
    - selected appendix model: `pls_8c`
    - predicted yield: `8.340 t/ha`
    - predicted yield: `3502.8 kg/feddan`
    - predicted whole-plot yield: `1065.7 kg`
    - corn training percentile: `0.446`
  - compared with the current `96`-feature `catboost` baseline:
    - grouped-CV RMSE worsened from `1.857` to `2.070`
    - AOI prediction moved up by about `0.261 t/ha`
    - AOI prediction moved up by about `109.5 kg/feddan`
    - AOI whole-plot estimate moved up by about `33.4 kg`
    - corn-training percentile moved from `0.429` to `0.446`
  - coefficient-magnitude summary by source:
    - `s2_index 8.3808`
    - `crop 2.3969`
    - `s2_quality 0.4137`
  - interpretation: the latent-factor linear family is a useful contrast check, but on the current cross-region YieldSAT-to-AOI setup it underperforms the best tree baseline and moves the AOI estimate farther from the user's remembered whole-plot range.

Why the compact-soil result needs caution:

- `scripts/fetch_aoi_soil.py` does not derive parcel-resolved soil summaries from AOI pixels.
- It performs a `SoilGrids` centroid point query at about `250 m` resolution and writes one compact soil row per AOI.
- The AOI artifact itself records:
  - `soil_query_method = centroid_point_query`
  - `soil_source_resolution_m = 250`
  - `soil_estimated_source_cells = 1`
  - `soil_low_resolution_warning = True`
- Because the AOI is much smaller than one SoilGrids cell, this compact soil block should be treated as a coarse regional prior rather than as a high-confidence field soil measurement.

Corn-only ablation result:

- A temporary corn-only notebook was created by copying the mixed baseline and retraining on `corn` only.
- Corn-only grouped CV got worse than the mixed `corn`/`wheat` baseline:
  - best grouped-CV model: `catboost`
  - `catboost`: `RMSE 2.403`, `MAE 2.000`, `R2 0.131`
  - `xgboost`: `RMSE 2.476`, `MAE 2.090`, `R2 0.064`
  - `lightgbm`: `RMSE 2.478`, `MAE 2.034`, `R2 0.046`
- Corn-only AOI inference also stayed near the center of the training corn distribution rather than moving toward the observed local yield:
  - selected model: `catboost`
  - predicted yield: `8.847 t/ha`
  - predicted yield: `3715.7 kg/feddan`
  - predicted whole-plot yield: `1130.4 kg`
  - plot area from notebook calculation: about `1277.8 m^2`, `0.1278 ha`, `0.304 feddan`
  - corn training percentile: `0.502`
- Interpretation: removing wheat did not materially reduce the AOI prediction. The remaining mismatch is therefore more likely tied to feature-transfer behavior and cross-region yield level shift than to mixed-crop conditioning.

AOI-vs-YieldSAT corn feature comparison result:

- The current YieldSAT corn reference for this baseline is only `303` rows across `14` `country_year` groups, and those rows come only from `Argentina` and `Brazil`.
- Under the exact AOI-compatible numeric contract used by the notebook, the comparison space contains `181` numeric features:
  - `1` season-length feature
  - `72` Sentinel-2 band-summary features
  - `98` vegetation-index features
  - `10` S2 quality/gap features
- Across the combined AOI sample (`C1` and `C3`) versus the YieldSAT corn reference:
  - median absolute z-score was about `0.84`
  - about `40.3%` of AOI feature values fell into the YieldSAT corn `<5th` or `>95th` percentile tails
  - about `19.6%` of AOI feature values were outside the observed YieldSAT corn min-max range
- The dominant shift is in timing-sensitive features, not in general observation quality:
  - `season_length_days` is out of range for both AOI corn seasons: `C1=105` and `C3=89` versus YieldSAT corn range `117-324`
  - `s2_*_peak_doy` features for `NDVI`, `EVI`, `GNDVI`, `NDRE`, `NDWI`, `SAVI`, and `MSI` all landed below the YieldSAT corn support for both AOI seasons
  - `s2_first_valid_doy` and `s2_last_valid_doy` also landed below the YieldSAT corn support for both AOI seasons
  - this pattern is consistent with a strong southern-hemisphere versus Egypt season-timing mismatch inside the current corn reference set
- AOI observation quality itself is strong rather than weak:
  - both `C1` and `C3` had `39` valid Sentinel-2 dates
  - `s2_valid_pixel_fraction_mean` was about `0.986` for `C1` and `0.978` for `C3`
- Raw band shift exists, but it does not appear to be the primary driver:
  - the strongest mean-band mismatch was `s2_B11_mean_mean_of_dates`, at about `-2.40 sigma` for `C1` and `-2.19 sigma` for `C3`
  - the other raw band means were much milder, mostly within about `|z| < 0.8`
- Standardized representation-space checks were dominated by the same timing issue:
  - both AOI seasons and the AOI-sample centroid landed beyond every YieldSAT corn row in the standardized `181`-feature space
  - the nearest corn neighbors were still far away and all came from `Argentina_2017`, with yields about `9.91-12.33 t/ha` and season lengths `173-210` days
- Supplemental brightness-normalization check on the `9` band mean features did not improve the AOI sample mismatch overall:
  - raw 9-band mean block AOI-centroid distance: about `2.49` in standardized space
  - brightness-normalized 9-band mean block AOI-centroid distance: about `2.52`
  - mean absolute z-score across those AOI band values moved from about `0.61` raw to about `0.67` after normalization
  - normalization helped `C1` alone but hurt `C3`, so it does not currently support a brightness-normalization-first fix for the yield baseline
- Updated interpretation: the current overprediction risk is more strongly explained by cross-region season-timing support and calendar-sensitive feature design than by raw spectral brightness alone.

Timing-robust first-pass notebook change:

- The main notebook now uses a timing-robust AOI-compatible contract for the next pass instead of the earlier imagery-only-plus-calendar version.
- Removed timing-sensitive features from the model input:
  - `season_length_days`
  - `s2_first_valid_doy`
  - `s2_last_valid_doy`
  - `s2_days_since_last_valid`
  - `s2_NDVI_peak_doy`
  - `s2_EVI_peak_doy`
  - `s2_GNDVI_peak_doy`
  - `s2_NDRE_peak_doy`
  - `s2_NDWI_peak_doy`
  - `s2_SAVI_peak_doy`
  - `s2_MSI_peak_doy`
- The remaining numeric contract for the next user run is now:
  - `72` AOI-available Sentinel-2 band-summary features
  - `91` vegetation-index features with `*_peak_doy` removed
  - `7` quality/gap features with absolute day-of-year timing removed
  - total numeric features: `170`
- The notebook still reconstructs the full AOI-safe season summary row, but the model input now keeps only the timing-robust subset above.
- How this pass was chosen: the earlier AOI-vs-YieldSAT corn comparison showed calendar-sensitive fields were the strongest out-of-support features for Egypt relative to the current `Argentina`/`Brazil` corn reference, while raw band brightness alone was not the main mismatch.
- Result after execution: this first pass produced only a modest AOI prediction reduction, so timing-sensitive feature removal alone is not enough to close the local plausibility gap.

Next no-raw-band notebook change:

- After the compact-soil experiment was inspected, the notebook source was returned to the no-soil path for the next cleaner comparison.
- The current notebook source now removes raw Sentinel-2 band summary features from model input while keeping timing-robust vegetation-index and non-calendar quality features.
- `valid_pixel_fraction` is retained only as an internal support/filter signal during AOI reconstruction and is no longer exposed as a direct model feature.
- The active no-raw-band contract is now:
  - `0` raw Sentinel-2 band-summary features kept in model input
  - `72` raw Sentinel-2 band-summary features excluded
  - `91` vegetation-index features with `*_peak_doy` removed
  - `5` non-calendar quality/gap features kept in model input
  - `2` direct valid-pixel support summaries excluded from model input: `s2_valid_pixel_fraction_mean`, `s2_valid_pixel_fraction_min`
  - total numeric features: `96`
- The AOI reconstruction still computes band summaries internally because the vegetation indices depend on the AOI cube bands, and it still uses `valid_fraction` to decide which dates are usable, but neither raw band summaries nor direct `valid_pixel_fraction` summaries are now passed to the model.

Observed local context from the user:

- The user's land reportedly produced about `600-800 kg` for the whole field/plot, not per feddan.
- The active notebook geometry conversion currently yields about `1277.8 m^2`, or about `0.1278 ha`, or about `0.304 feddan`.
- Under that conversion, the original imagery-only baseline predicted about `1113.2 kg` for the whole AOI plot and the timing-robust first pass predicted about `1084.8 kg`.
- The temporary compact-soil variant predicted about `1021.9 kg` for the whole AOI plot.
- The current no-raw-band timing-robust pass predicts about `1014.8 kg` for the whole AOI plot.
- The current direct-valid-pixel-free no-raw-band pass predicts about `1032.3 kg` for the whole AOI plot.
- The appended `PLSRegression` check predicts about `1065.7 kg` for the whole AOI plot.
- That is still above the user's observed `600-800 kg`, but it remains closer than the no-soil timing-robust pass while still remaining outside the user's remembered range.

Current notebook fixes already applied:

- Raw weather removed from the default baseline and from AOI reconstruction requirements.
- AOI reconstruction no longer depends on `weather_daily.parquet`.
- AUC calculation in AOI index summaries now uses a NumPy-compatible trapezoid integration path.
- The feature-importance cell again fits `best_pipeline` before reading importances.
- The final prediction cell now predicts with the already-fitted best model instead of retraining all three models.
- Temporary timing/debug prints were used to inspect the last cell and then removed after confirming prediction runtime was negligible.
- The last cell now reports yield in `t/ha`, `kg/feddan`, and whole-plot `kg` based on AOI geometry loaded directly from `run_metadata.json`.
- No repo artifacts were kept from the AOI-vs-YieldSAT feature comparison; the analysis was run as a read-and-compare step only and only the resulting findings were retained here.
- After the timing-robust source edit, stale notebook outputs and execution counts were cleared so the next run reflects only the new feature contract.

## Open Questions

- Which prediction-moment table is most defensible for the first AOI test: `mid_season`, `near_harvest`, or `full_season`?
- Should the first AOI-compatible baseline include the known crop label as an explicit input feature, or should it train separate crop-specific regressors later?
- How stable are grouped metrics once location and non-AOI feature shortcuts are removed?
- How should AOI yield plausibility be judged if no ground-truth AOI yield value is currently attached to the archive?
- After the timing-robust pass, do the remaining raw Sentinel-2 band summaries still contribute enough regional shift to justify a vegetation-index-plus-quality-only baseline?
- Is the compact-soil block helping because it adds real agronomic signal, or mainly because a single coarse SoilGrids centroid query acts as a geography prior for this AOI?
- Given that the no-raw-band pass performed nearly as well on the AOI prediction without soil, is there still enough evidence to justify bringing coarse SoilGrids priors back into the default baseline?
- If the next ablation still overpredicts, is the remaining gap primarily a target-definition issue, a management/intensity mismatch, or a broader cross-region label-distribution problem inside YieldSAT corn?

## Next Actions

1. Treat the current `96`-feature no-raw-band, direct-valid-pixel-free `catboost` notebook path as the principled stopping point for this exploration; the appended `PLSRegression` check did not improve the trade-off.
2. If work resumes later, compare whether the remaining gap is tied more to mixed-crop conditioning or to YieldSAT target/domain mismatch rather than to raw spectral level.
3. If later experiments revisit soil, keep it clearly separated from the default baseline and account explicitly for the coarse `250 m` centroid-query limitation.
