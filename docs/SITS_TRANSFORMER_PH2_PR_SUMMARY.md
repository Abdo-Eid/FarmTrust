# SITS-Transformer Phase 2 - PR Summary

## What was built
- EuroCropsML Latvia 2021 download and conversion to FarmTrust SITS-BERT format.
- Two-stage transfer fine-tuning: EuroCrops pre-adaptation followed by Egypt domain adaptation.
- Terminal AOI annotation workflow plus annotation merge into the held-out test set and weak-label training data.
- Final evaluation with corrected manual labels and threshold-gated inference artifacts.
- Final evaluation: precision_active = 1.00, false_active_rate = 0.00.

## Model chain
sits_bert_pretrained.pt (Phase 0-5)
  -> sits_bert_euro_transfer.pt (Stage 1: EuroCrops, 30 epochs)
    -> sits_bert_final.pt (Stage 2: Egypt manual labels, 50 epochs)

## Test set status
manual_annotation/manual_annotation_corrected: 12 parcels
rule_based_proxy: 0 parcels

No proxy labels remain in the current F5 test set. `aoi_nile_delta_03` was manually corrected to active after review confirmed real vegetation activity despite cloud-gap season boundary issues.

## Safe to merge
- 21 existing tests pass.
- Final evaluation passes: precision_active = 1.0000, recall_active = 1.0000, false_active_rate = 0.0000.
- `ml_advisory` field is optional; no existing API contract field was changed.
- `models/` remains gitignored; no large model binaries are included in the PR.
- `farmtrust_core/scoring/` was untouched.

## What comes next
- Expand manually reviewed AOI coverage beyond the current 12-parcel F5 test set.
- Ingest 50+ AOIs for a larger Egypt training and validation set.
- Phase 3: Sentinel-1 SAR multimodal model.
