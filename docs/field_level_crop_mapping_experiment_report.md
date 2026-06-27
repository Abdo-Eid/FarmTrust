# Field-Level Crop Mapping Experiment Report

Date: 2026-06-26

Project scope:
- Task: field-level crop classification
- Target classes: `wheat`, `corn`, `other`
- Data source: YieldSAT Sentinel-2 seasonal field data
- Main model families explored: LSTM sequence models, XGBoost baselines, weighted ensembles

## 1. Executive Summary

This project evolved from a simple three-class LSTM baseline into a stronger field-level seasonal modeling pipeline using:
- reflectance bands,
- agronomic indices,
- observation-quality features,
- calendar features,
- group-aware validation splits,
- and later a blended ensemble.

The strongest recorded results in the notebooks came from the full 22-feature seasonal pipeline:
- LSTM validation macro F1: `0.9443`
- LSTM test accuracy: `0.9476`
- XGBoost test accuracy: `0.9170`
- tuned ensemble test accuracy: `0.9782`
- tuned ensemble macro F1: `0.9796`

Later feature reduction experiments showed:
- aggressive reduction to 12 features hurt LSTM performance materially,
- a lighter 15-feature reduction preserved LSTM performance almost exactly,
- but the best recorded ensemble remained the full-feature run.

## 2. Problem Definition

This work should be described explicitly as:

`Field-level target-crop screening: wheat / corn / other`

It is not a four-class crop mapping task in the final modeling setup. The original YieldSAT archive contained four crop labels, but the implemented objective deliberately remapped them into three operational classes:
- `wheat`
- `corn`
- `other`

This reframing was important because the practical objective was to detect two target crops reliably at field level while preserving a fallback class for non-target fields.

Why field level was chosen instead of pixel level:
- the label available in this workflow is a field label, not a reliable per-pixel crop label
- field-level aggregation reduces within-field noise from mixed pixels, cloud contamination, and boundary effects
- the real decision target in this project is the crop assigned to a whole field parcel
- field-level time series are more consistent with farm-management use cases than pixelwise thematic maps

Why pixel level was not the primary target:
- a pixel-level model would require stronger pixelwise ground truth than the notebooks used here
- individual pixels inside the same field can vary because of shadows, edges, soil exposure, and georegistration offsets
- training pixelwise from field labels would introduce label noise because not every pixel is equally representative of the field crop

## 3. Dataset Framing

The notebooks consistently used the following field counts from YieldSAT:

| Original crop | Field count |
|---|---:|
| soybean | 1305 |
| wheat | 454 |
| corn | 303 |
| rapeseed | 111 |

Total discovered field folders:
- `2173`

The classification problem was reformulated from four source crops into three deployment-oriented classes:

| Final class | Source crop mapping |
|---|---|
| wheat | wheat |
| corn | corn |
| other | soybean + rapeseed |

Selected class-balanced training subset used throughout the later notebooks:
- wheat: `454`
- corn: `303`
- soybean sampled into other: `400`
- rapeseed sampled into other: `100`
- total: `1257`

This was a sensible practical decision for a first deployable field-level classifier because it focused the model on two important known crops while preserving a reject-like `other` category.

## 4. Core Preprocessing Design

Across the mature notebooks, the pipeline converged on the following representation:
- `20` timesteps per field
- Sentinel-2 reflectance bands aggregated at field level
- cloud/invalid masking using the SCL layer
- agronomic indices derived from reflectance means
- calendar features from day-of-year
- quality feature from valid pixel fraction

The mature feature tensor shape before reduction was:
- `X shape: (1257, 20, 22)`

The 22 per-timestep features were:
- `B01, B02, B03, B04, B05, B06, B07, B08, B8A, B09, B11, B12`
- `ndvi, evi, ndmi, ndwi, ndre, savi, msi`
- `valid_fraction, doy_sin, doy_cos`

Important implementation notes from the notebooks:
- reflectance was scaled as `DN / 10000`
- missing temporal values were filled by interpolation plus fallback statistics
- context features were retained explicitly rather than dropping low-quality timesteps
- grouping by `country_year` was introduced to reduce optimistic leakage

When and how reflectance scaling was applied:
- scaling was applied immediately after reading each Sentinel-2 image tile from disk
- the notebook logic read the raster as numeric bands, cast it to floating point, and then converted raw digital numbers using `reflectance = DN / 10000`
- invalid or non-positive values were then set to missing before aggregation
- field-level band means were calculated after scaling and after SCL masking
- agronomic indices such as `ndvi`, `evi`, `ndmi`, `ndwi`, `ndre`, `savi`, and `msi` were computed from these scaled reflectance means, not from unscaled raw digital numbers

Why this matters:
- index formulas assume physically meaningful reflectance ratios
- scaling before aggregation keeps the reflectance statistics and derived indices numerically consistent across fields and dates

Field-level aggregation design:
- each field/date sample was reduced to one feature vector by averaging valid pixels within the field footprint
- this means the model does not consume raw image patches; it consumes a seasonal sequence of field summaries
- one field therefore becomes one multistep sample rather than thousands of pixel samples

## 5. Final Experiment Comparison

The final experiments can be summarized in one benchmark table:

| Experiment | Features | Model | Accuracy | Macro F1 |
|---|---|---|---:|---:|
| Reflectance baseline | 12 bands | LSTM | 0.9245 | ~0.92 |
| Full features | 22 | LSTM | 0.9476 | 0.9443 |
| Full features | 22 | XGBoost | 0.9170 | 0.8846 |
| Full features | 22 | Ensemble | 0.9782 | 0.9796 |
| Aggressive reduced | 12 | LSTM | 0.8996 | 0.9337 val |
| Light reduced | 15 | LSTM | 0.9476 | 0.9446 |

Interpretation:
- the full 22-feature pipeline delivered the strongest overall benchmark
- the 15-feature LSTM matched the full LSTM almost exactly
- aggressive pruning removed information that was still useful, especially for wheat
- the ensemble gave the best overall score, while the reduced 15-feature LSTM gave the best simplicity-to-performance tradeoff among the pure LSTM runs

How the test set was chosen:
- the split was done at field level, not at pixel level
- later notebooks moved away from simple random splitting and grouped fields by `country_year`
- this grouping was used so that fields from the same country and year stayed together in the same partition
- the goal was to reduce overly optimistic leakage from very similar seasonal conditions appearing in both training and testing
- in practical terms, the held-out test partition was selected from grouped field samples after the class remapping and field subsampling steps were complete

Why this split strategy was preferred:
- it is harder and more realistic than a naive random split
- it better tests whether the model generalizes across seasonal and regional structure
- it is still not as strict as a full leave-one-country-out study, which is why that remains a recommended next step

## 6. Notebook Review

### 6.1 `crop_mapping_v1_reflectance_baseline.ipynb`

Role:
- early working LSTM baseline with a simpler split

What it tried:
- 3-class LSTM with `20 x 12` reflectance input
- temporal interpolation for NaNs
- standard train/test split
- it carried forward the core lesson from the earliest discarded exploration: the `wheat / corn / other` reformulation was workable and field-level seasonal sequences contained useful crop signal

Recorded result:
- LSTM accuracy: `0.9245`
- confusion matrix:
  - wheat: `12 0 2`
  - corn: `0 19 0`
  - other: `2 0 18`
- macro average F1 about `0.92`

Why it mattered:
- it proved the field-level reformulation was viable,
- but it was still optimistic because the split strategy was not yet strong enough for cross-country, cross-season generalization claims.

Why the grouped strategy was preferred later:
- random splitting can place fields from the same seasonal and regional context in both train and test
- grouped splitting by `country_year` makes leakage much less likely
- grouped evaluation is therefore more realistic for deployment than a naive random split

Main advantage of this baseline:
- it established a clear reflectance-only benchmark that all later grouped and full-feature models had to beat

Assessment:
- good proof of concept
- not yet a final trustworthy model

### 6.2 Grouped full-feature development

This stage is best treated as one connected progression across:
- `crop_mapping_full_features_final.ipynb`

Role:
- transition from a simple baseline to a harder grouped evaluation with the full seasonal feature set

How the grouped strategy was done:
- each field was assigned to a `country_year` group
- fields from the same `country_year` were kept together in the same partition
- the grouped split happened after class remapping and field selection, so the train and evaluation partitions operated on final field-level samples
- this reduced leakage from nearly identical seasonal conditions appearing in both train and test

What the early grouped notebook contributed:
- harder grouping logic using `country_year`
- explicit train/final-validation group separation
- a transition away from optimistic random-split evaluation

Recorded grouped-transition output:
- train final: `(582, 20, 13)`
- validation: `(445, 20, 13)`
- validation groups: `7`

How the full-feature model was built in this grouped stage:
- a full `20 x 22` seasonal tensor per field
- grouped split by `country_year`
- one LSTM sequence model as the main temporal learner
- one XGBoost baseline on flattened or aggregated representations
- one tuned weighted ensemble
- permutation feature importance and grouped importance analysis
- all of that was consolidated into one cleaned production-style notebook that preserved the same full-feature design and packaged the strongest results more cleanly

Recorded dataset state:
- `X shape: (1257, 20, 22)`
- `28` unique `country_year` groups

Recorded LSTM result:
- validation macro F1: `0.9443`
- test accuracy: `0.9476`

LSTM confusion matrix:
- wheat: `81 1 2`
- corn: `1 55 0`
- other: `1 7 81`

Recorded XGBoost result:
- validation macro F1: `0.8846`
- test accuracy: `0.9170`

Recorded tuned ensemble result:
- best validation config:
  - `alpha = 0.70`
  - `wheat_threshold = 0.60`
  - `corn_threshold = 0.75`
- final tuned ensemble accuracy: `0.9782`
- final tuned ensemble macro F1: `0.9796`

Recorded aggressive aggregated-feature XGBoost result:
- validation macro F1: `0.8832`
- test accuracy: `0.8122`

Top recorded LSTM permutation features:
- `doy_cos`
- `doy_sin`
- `B06`
- `ndre`
- `B11`
- `ndmi`
- `msi`

Recorded group importance:
- context: `0.3866`
- reflectance: `0.2839`
- agri_indices: `0.1526`

Low-importance candidates recorded:
- `ndwi`
- `valid_fraction`
- `B04`
- `B03`
- `B05`
- `ndvi`
- `B02`
- `B08`
- `B12`
- `B8A`
- `savi`

What the final merged notebook added:
- a clean full-feature production-style presentation
- the same `20 x 22` grouped full-feature workflow as the benchmark stage
- the same strongest benchmark metrics:
  - LSTM validation macro F1: `0.9443`
  - LSTM test accuracy: `0.9476`
  - XGBoost test accuracy: `0.9170`
  - tuned ensemble accuracy: `0.9782`
  - tuned ensemble macro F1: `0.9796`
- a cleaner summary of the strongest and weakest LSTM features
- the best single notebook to cite when presenting the full-feature result formally

Why this merged stage mattered:
- it introduced the more defensible grouped validation strategy
- it established the strongest full-feature benchmark in the repo history
- it showed the performance order clearly: ensemble best, LSTM second, flattened tree baseline lower
- it produced the feature-importance evidence that later justified feature reduction experiments

Assessment:
- this is the methodological core of the project
- it is the right place in the report to explain grouped evaluation, the full-feature model design, and the final polished full-feature notebook

### 6.3 `crop_mapping_aggressive_feature_reduction.ipynb`

Role:
- aggressive feature reduction test

Selected features:
- `B01, B06, B07, B09, B11, evi, ndmi, ndre, msi, valid_fraction, doy_sin, doy_cos`

Selected feature count:
- `12`

Recorded result:
- validation macro F1: `0.9337`
- test accuracy: `0.8996`

LSTM confusion matrix:
- wheat: `68 16 0`
- corn: `1 55 0`
- other: `5 1 83`

Interpretation:
- corn remained strong
- wheat degraded sharply due to over-pruning

Assessment:
- important negative result
- demonstrated that not all apparently weak features are expendable

### 6.4 `crop_mapping_light_reduced_final.ipynb`

Role:
- lighter feature reduction refinement

Selected features:
- `B01`
- `B04`
- `B06`
- `B07`
- `B08`
- `B09`
- `B11`
- `evi`
- `ndvi`
- `ndmi`
- `ndre`
- `msi`
- `valid_fraction`
- `doy_sin`
- `doy_cos`

Selected feature count:
- `15`

Recorded tensor shape:
- light-reduced tensor: `(1257, 20, 15)`

Recorded LSTM result:
- validation macro F1: `0.9446`
- test accuracy: `0.9476`

LSTM confusion matrix:
- wheat: `80 3 1`
- corn: `1 55 0`
- other: `1 6 82`

Recorded feature importance for the 15-feature LSTM:
- strongest:
  - `B06`
  - `doy_sin`
  - `doy_cos`
  - `ndre`
  - `ndmi`
  - `B11`
- weakest:
  - `B01`
  - `B04`
  - `evi`
  - `valid_fraction`

Recorded group importance:
- context: `0.3624`
- reflectance: `0.2411`
- agri_indices: `0.1548`

Recorded XGBoost result:
- validation macro F1: `0.8945`
- test accuracy: `0.9214`

Recorded tuned ensemble result:
- accuracy: `0.9607`
- macro F1: `0.9603`

Assessment:
- best reduced-feature LSTM notebook
- very strong evidence that a 15-feature model can match the full LSTM
- but its recorded ensemble result was lower than the full-feature ensemble benchmark

## 7. Evidence and Figures to Include

For a submission, defense, or academic-style appendix, the following visual evidence should be included explicitly:

1. Dataset folder structure
- show the country-level and field-level organization of the YieldSAT folders

2. LSTM training and validation loss
- include the full-feature run
- include the light-reduced 15-feature run

3. LSTM training and validation accuracy
- include the full-feature run
- include the light-reduced 15-feature run

4. Confusion matrix for the full-feature LSTM
- source: `crop_mapping_full_features_final.ipynb`

5. Confusion matrix for the reduced 15-feature LSTM
- source: `crop_mapping_light_reduced_final.ipynb`

6. Feature importance plot
- source: permutation importance from the full-feature importance notebook

7. Group importance plot
- compare `reflectance`, `agri_indices`, and `context`

8. Inference or deployment pipeline diagram
- show that deployment must reuse the same preprocessing, feature order, scaling, and label mapping used during training

These figures are not just cosmetic. They are evidence for data organization, optimization behavior, class-level errors, and interpretability.

## 8. Final Feature Schema

The final reduced LSTM used the following `15` per-timestep features in this exact order:

1. `B01`
2. `B04`
3. `B06`
4. `B07`
5. `B08`
6. `B09`
7. `B11`
8. `evi`
9. `ndvi`
10. `ndmi`
11. `ndre`
12. `msi`
13. `valid_fraction`
14. `doy_sin`
15. `doy_cos`

This order matters. Any saved model or later inference path must consume features in exactly the same sequence used during training.

## 8.1 Model Input and Output Format

Input format for the full-feature LSTM:
- shape per sample: `(20, 22)`
- meaning: `20` ordered timesteps, each with `22` features
- batch input shape at training or inference time: `(N, 20, 22)`

Input format for the reduced LSTM:
- shape per sample: `(20, 15)`
- batch input shape at training or inference time: `(N, 20, 15)`

What one sample represents:
- one agricultural field
- one seasonal sequence
- one feature vector per selected observation date

Output format:
- one probability vector per field
- class order follows the saved label mapping
- in this project that mapping is:
  - `0 -> wheat`
  - `1 -> corn`
  - `2 -> other`
- output shape per sample: `(3,)`
- batch output shape: `(N, 3)`

Final prediction rule:
- the predicted class is the index with the highest probability
- the reported crop label is obtained by decoding that class index back to `wheat`, `corn`, or `other`

## 9. What Worked Well

The strongest decisions in this project were:

### 9.1 Reformulating to `wheat / corn / other`

Why it was good:
- reduced class complexity
- aligned better with practical deployment
- improved interpretability of false positives and false negatives

### 9.2 Moving to group-aware validation

Why it was good:
- reduced leakage across similar country-year conditions
- gave more realistic estimates than a naive random split

### 9.3 Adding calendar and quality features

Why it was good:
- `doy_sin` and `doy_cos` repeatedly emerged as among the most important features
- this confirmed that crop phenology timing is critical

### 9.4 Using permutation importance before pruning

Why it was good:
- feature selection was not done blindly
- the aggressive 12-feature reduction showed that careless pruning can hurt performance
- the later 15-feature selection was much better justified

### 9.5 Preserving a strong LSTM baseline while testing simpler alternatives

Why it was good:
- XGBoost provided a useful baseline
- ensemble modeling showed whether complementary errors existed
- this created a stronger evidence chain than reporting only one model family

## 10. Deployment and Inference Considerations

Any deployment package for this model family should preserve, at minimum:
- `.keras` model weights
- `scaler.pkl`
- `feature_names.pkl`
- `label_names.pkl`
- `config.json`

Required deployment rule:
- inference must reuse the same preprocessing logic
- inference must reuse the same reflectance scaling
- inference must reuse the same SCL masking assumptions
- inference must reuse the same feature order
- inference must reuse the same label mapping

This is especially important for the reduced LSTM because the feature count alone is not enough. The serving pipeline must also preserve the exact order:
- `B01, B04, B06, B07, B08, B09, B11, evi, ndvi, ndmi, ndre, msi, valid_fraction, doy_sin, doy_cos`

What inference data should look like:
- one field at a time, or a batch of fields
- each field must be converted into a seasonal sequence with exactly `20` ordered timesteps
- each timestep must contain the same features used in training, in the same order
- reflectance bands must already be converted using `DN / 10000`
- SCL masking must be applied before computing field-level means
- agronomic indices must be computed from the scaled reflectance values
- calendar features `doy_sin` and `doy_cos` must be derived from the observation date
- `valid_fraction` must represent the fraction of valid pixels after masking

Expected inference tensor:
- full-feature model: `(N, 20, 22)`
- reduced model: `(N, 20, 15)`

What should not be passed directly to the model:
- raw unscaled digital numbers
- unordered dates
- per-pixel rasters without field aggregation
- feature columns in a different order
- sequences with a different timestep count unless they are resampled to the trained format

Recommended inference record structure before tensor conversion:
- `field_id`
- `country`
- `year` or season identifier
- ordered list of observation dates
- per-date field-level feature vector
- optional metadata about masking quality and source imagery

Known limitation from the broader experimentation history:
- an AOI-level serving example was previously observed to predict `wheat` even though the expected crop was `corn`

The most likely explanations are:
- domain shift between YieldSAT training fields and a new AOI
- mismatch in season timing
- different SCL masking behavior
- different preprocessing assumptions between training and serving

That observation should not be hidden. It should be documented as a deployment risk and as evidence that strong notebook metrics do not automatically guarantee robust external behavior.

## 11. What Was Risky or Needs Correction

### 11.1 Split confidence should still be treated carefully

Even with `country_year` grouping, the dataset remains relatively small and geographically structured. Results are strong, but they are not yet equivalent to a fully external validation study.

Recommended next step:
- leave-one-country-out evaluation

### 11.2 SCL masking assumptions were not perfectly consistent across all stages

The notebooks often used:
- `VALID_SCL_CLASSES = [4, 5, 6, 7]`

The FarmTrust ingest metadata later recorded invalid classes:
- `0, 1, 3, 7, 8, 9, 10, 11`

That means:
- the valid/invalid SCL interpretation was not identical across all workflows,
- especially for class `7`

This needs to be standardized before making strong deployment claims.

### 11.3 Some late cells in `crop_mapping_light_reduced_final.ipynb` failed

Observed errors:
- `importance_df` / `agg_feature_cols` were missing in later export cells

Impact:
- LSTM training and evaluation results are still valid
- but some later XGBoost/agri export cells were not fully reproducible from the preserved notebook execution

### 11.4 The results are not yet full external validation

The current evidence is strong for internal grouped evaluation, but it is still not equivalent to a geographically independent validation campaign.

What is still needed:
- leave-one-country-out evaluation
- repeated grouped resampling
- explicit external holdout or future-season holdout

### 11.5 Deployment behavior may be more fragile than notebook metrics suggest

The report should acknowledge that an AOI-level serving result can fail even when notebook metrics are strong. This is typical in remote sensing when:
- preprocessing differs slightly
- seasonal timing differs
- cloud masking differs
- field geometry context differs from the training archive

## 12. Final Model Recommendations

There are two reasonable final choices depending on your goal.

### Option A: Best benchmark model

Use the full-feature pipeline from `crop_mapping_full_features_final.ipynb` if your priority is:
- strongest recorded ensemble performance
- strongest overall benchmark

Best recorded results:
- LSTM test accuracy: `0.9476`
- ensemble accuracy: `0.9782`
- ensemble macro F1: `0.9796`

### Option B: Best simplified LSTM

Use the 15-feature reduced LSTM from `crop_mapping_light_reduced_final.ipynb` if your priority is:
- lower feature count
- nearly unchanged LSTM accuracy
- simpler sequence input

Best recorded reduced LSTM result:
- validation macro F1: `0.9446`
- test accuracy: `0.9476`

This is a strong simplification result and is probably the best pure-LSTM candidate if you want a leaner model.

## 13. Reproducibility and Final Notebook Set

The final notebook set that should be referenced in a submission is:

1. `crop_mapping_full_features_final.ipynb`
- role: best benchmark notebook
- contains: strongest full-feature LSTM, XGBoost, ensemble, and final interpretation-oriented outputs

2. `crop_mapping_light_reduced_final.ipynb`
- role: best simplified LSTM notebook
- contains: the reduced 15-feature LSTM that preserved the full LSTM accuracy

Supporting notebooks that remain useful as evidence:
- `crop_mapping_v1_reflectance_baseline.ipynb`
- `crop_mapping_aggressive_feature_reduction.ipynb`

Minimum reproducibility requirements:
- preserve random seed settings
- preserve `country_year` grouping logic
- preserve `20` timestep sampling
- preserve reflectance scaling as `DN / 10000`
- preserve SCL masking logic
- preserve feature order exactly

Additional details that should be preserved in any rerun:
- the same class remapping from four source crops to `wheat / corn / other`
- the same field-level aggregation logic
- the same sampled composition of the `other` class when reproducing the reported experiments
- the same missing-value interpolation strategy
- the same label encoding order

## 14. Final Assessment

Overall assessment:
- the experimentation process was strong and rational,
- the project made good progress from baseline to mature benchmark,
- the best notebook evidence supports a high-quality field-level seasonal classifier,
- and the feature-reduction work was especially valuable because it showed both what can be removed and what should not be removed.

Most defensible headline results from the notebook record:
- full-feature LSTM: `94.76%` test accuracy
- best recorded ensemble: `97.82%` test accuracy, `97.96%` macro F1
- reduced 15-feature LSTM: matched the full LSTM at `94.76%` test accuracy

The strongest scientific conclusion is not that all crop mapping is solved. The strongest supported conclusion is that field-level target-crop screening for `wheat / corn / other` is feasible and strong under grouped internal evaluation.

The remaining gap is no longer basic modeling quality. The remaining gap is experiment governance:
- stronger external validation
- strict preprocessing consistency
- and cleaner deployment reproducibility

The clearest follow-up priorities are:
- run leave-one-country-out or leave-one-country-year-out validation
- standardize SCL masking across all notebooks and deployment paths
- embed the final figure set directly in the report
- keep one clean deployment export path with model, scaler, feature names, label names, and config
