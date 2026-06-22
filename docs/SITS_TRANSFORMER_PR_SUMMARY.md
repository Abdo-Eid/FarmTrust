# SITS Transformer PR Summary

## What Was Built

- Phase 0: Added optional ML dependencies for Torch, classical ML, evaluation, and plotting.
- Phase 1: Built `farmtrust_core/ml/` with Egypt agricultural-cycle sequence building, weak labels, normalization, reliability features, and advisory inference.
- Phase 2: Added the SITS dataset export pipeline for Kaggle training artifacts.
- Phase 2.5: Added the LightGBM/CatBoost classical activity model benchmark path as the priority production candidate.
- Phase 3: Added SITS-BERT training code for pretraining, finetuning, datasets, config, and model definitions.
- Phase 4: Added and executed Kaggle notebook workflow for SITS-BERT training.
- Phase 5: Added local model download and inference flow that writes `data/ml/<aoi_id>/sits_prediction.json`.
- Phase 6: Added evaluation and threshold tooling, including proxy test set handling and warning controls.
- Phase 7: Integrated optional API advisory output without changing existing rule-based assessment fields.

## Current Model Status

The pipeline is validated end to end, but current evaluation metrics are `0.0`. This is expected because the model was trained on a very small weakly labeled dataset and evaluated against rule-based proxy labels, not manually annotated ground truth. The result should be treated as a successful system integration signal, not as evidence of model quality.

SITS-BERT remains advisory/research only. LightGBM/CatBoost remains the priority production ML candidate until evaluation on a real labeled validation/test set proves otherwise.

## What Is Needed To Improve Metrics

- Manually annotate `data/ml/labels/test_set.csv` and replace proxy labels with ground-truth labels.
- Ingest 50+ AOIs to build a real training set with broader land, crop, and coverage variation.
- Rebuild and re-upload `sits_dataset.npz` to Kaggle, then retrain the models.

## Safe Merge Notes

- All 21 existing tests pass.
- ML is advisory only; no existing API field names or rule-based outputs were changed.
- `models/` is gitignored, so trained weights and other large model files are not included in the PR.
- The API returns `ml_advisory` as an optional field and returns `null` when no ML artifact exists.

## Open Items For The Team

- Replace proxy test labels with manual annotations before reporting metrics to lenders or stakeholders.
- Decide the minimum AOI count and label quality gate for promoting any ML model beyond advisory mode.
- Compare retrained SITS-BERT against the classical LightGBM/CatBoost baseline on active precision, false-active rate, macro F1, calibration, and timeline quality.
- Recalibrate Egypt-specific coverage gates after collecting 100+ manually labeled AOIs.
- Keep false-active gates mandatory for any future production ML decision path.
