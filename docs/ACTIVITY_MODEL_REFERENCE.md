# FarmTrust ML — Models & Data Reference

**Project:** FarmTrust · NeuralAlloy
**Author:** Fares (ML Lead)
**University:** Menoufia University · Faculty of Artificial Intelligence

---

## What the System Does

Given a land parcel polygon and a date range, the system answers:
**"Was this land genuinely farmed, or not?"**

Output is one of four labels: `active` / `bare` / `sparse` / `uncertain`

---

## Data Used

### Dataset 1 — Egypt Parcel Time Series (our own)

**Source:** Microsoft Planetary Computer — https://planetarycomputer.microsoft.com
**What it is:** Sentinel-2 satellite images taken every 5 days over 14 Egyptian agricultural parcels in the Nile Delta and Upper Egypt regions, from 2020 to 2024.
**Who generated it:** We generated it by running the existing FarmTrust ingestion and preprocessing pipeline on real parcel coordinates.
**Format:** CSV files — one row per satellite observation, one file per parcel.
**Size:** 19 to 404 usable observations per parcel. 14 parcels total.
**Content per row:** date, NDVI, EVI, NDMI, NDWI, valid pixel fraction, and quality flags.

---

### Dataset 2 — EuroCropsML Latvia 2021

**Source:** Zenodo — https://zenodo.org/records/13789558
**What it is:** 706,683 labeled European agricultural parcels from Latvia. Each parcel has a Sentinel-2 time series from 2021 and a crop type label (wheat, grass, fallow, maize, etc.).
**Who generated it:** Published by the EuroCrops research group. Publicly available, free to use.
**Format:** Parquet files. We converted 5,000 parcels to our own NPZ format.
**Size:** 5,000 parcels used. Each parcel has ~30 observations.
**Content per row:** date, raw Sentinel-2 band values (B02–B12), crop label.

---

## Models Built

---

### Model 1 — SITS-BERT Pretrained (self-supervised)

**What it does:** Learns the general pattern of satellite vegetation time series without any labels. It sees thousands of sequences and learns what a "normal" satellite observation should look like given the surrounding context.

**Architecture:** SITS-BERT Transformer
- 3 Transformer layers
- 8 attention heads
- 256 hidden dimensions
- Based on: https://github.com/linlei1214/SITS-BERT

**Training data:** Egypt parcel time series (Dataset 1 above). No labels used — self-supervised.

**Input:**
- Type: numerical time series (not images, not text)
- Shape: 64 timesteps × 10 features per parcel
- The 10 features are: NDVI, EVI, NDMI, NDWI, bare soil index, valid pixel fraction, day-of-year sine, day-of-year cosine, observation gap days, usability flag
- 30% of timesteps are randomly masked (zeroed out) during training

**Output:**
- Reconstructed feature values for the masked timesteps
- Shape: 64 × 10 (same as input)
- Loss: mean squared error between predicted and actual values at masked positions

**Training:** Kaggle T4 × 2 GPU · 80 epochs · ~6 hours
**Saved as:** `models/sits_bert_pretrained.pt`

---

### Model 2 — SITS-BERT EuroCrops Transfer (supervised, Stage 1)

**What it does:** Takes the pretrained model from Model 1 and teaches it to classify crop activity using real labeled European crop data. After this stage, the model understands what wheat, grass, and fallow look like in a satellite time series.

**Architecture:** Same SITS-BERT encoder as Model 1 + classification head (Linear layer mapping 256 → 4 classes)

**Training data:** EuroCropsML Latvia 2021 (Dataset 2 above). 5,000 labeled parcels.

**Label mapping applied:**
```
Wheat (any variety)    → active   (class 0)
Grass / meadow / clover → active  (class 0)
Fallow / bare soil      → bare    (class 1)
Catch crop / cover crop → sparse  (class 2)
Everything else         → uncertain (class 3)
```

**Input:**
- Type: numerical time series (not images, not text)
- Shape: 64 timesteps × 10 features per parcel
- Same 10 features as Model 1
- Attention mask: 1 for real observations, 0 for padding

**Output:**
- 4 class probabilities per timestep
- Shape: 64 × 4
- Classes: [P(active), P(bare), P(sparse), P(uncertain)]
- Final parcel label: argmax of mean probabilities across timesteps

**Training:** Kaggle T4 × 1 GPU · 30 epochs · ~2 hours · LR 0.0001
**Saved as:** `models/sits_bert_euro_transfer.pt`

---

### Model 3 — SITS-BERT Egypt Final Model (supervised, Stage 2)

**What it does:** Takes Model 2 (trained on European crops) and adapts it specifically to Egyptian agricultural patterns. This is the model that runs in production. Given a parcel's satellite history, it outputs whether the land was actively farmed or not, with a confidence score.

**Architecture:** Same as Model 2. Fine-tuned with lower learning rate.

**Training data:** 14 Egypt AOIs from Dataset 1, labeled using the existing FarmTrust rule-based pipeline as weak supervision. One label correction applied manually (aoi_nile_delta_03).

**Input:**
- Type: numerical time series (not images, not text)
- Shape: 64 timesteps × 10 features per parcel
- Same 10 features as Models 1 and 2

**Output:**
- Per-observation: 4 class probabilities → shape 64 × 4
- After HMM smoothing: clean state sequence → shape 64 × 1
- After cycle extraction: list of cultivation windows, each with:
  - `start_date` and `end_date`
  - `label`: active / bare / sparse / uncertain
  - `mean_confidence`: float 0–1
- Final parcel verdict: `ml_land_status` (one of the 4 labels)

**Decision threshold:** P(active) must exceed **0.65** to be labeled active (not standard 0.50). This is intentional — false active predictions are more dangerous than false inactive.

**Training:** Kaggle T4 × 1 GPU · 50 epochs · ~3 hours · LR 0.00005
**Saved as:** `models/sits_bert_finetuned.pt`

---

### Bonus — Classical ML Benchmark (LightGBM)

**What it does:** A simpler model built as a sanity check before investing in deep learning. It classifies each parcel as active or bare using hand-crafted features.

**Architecture:** LightGBM gradient boosted trees

**Training data:** Same 14 Egypt AOIs with weak labels.

**Input:**
- Type: flat feature vector (not a sequence)
- Features: NDVI amplitude, NDVI integral, NDVI peak day-of-year, green-up rate, senescence rate, valley duration days, EVI/NDVI ratio, valid fraction, parcel area
- Shape: 1 vector per parcel (not per timestep)

**Output:**
- Binary: active vs not-active
- Confidence score: 0–1

**Purpose:** Validation only. Not deployed to production. Confirmed the feature pipeline was working before training SITS-BERT.

---

## Final Evaluation Results (Model 3)

Evaluated on 14 Egypt parcels (never used during training):

| Metric | Value | What it means |
|---|---|---|
| Precision (active) | 1.0000 | Every parcel labeled "active" was truly active |
| Recall (active) | 1.0000 | Every truly active parcel was found |
| False Active Rate | 0.0000 | Zero empty parcels were called active farms |
| Macro F1 | 0.9167 | Overall accuracy across all 4 classes |

**Honest note:** 14 parcels is a small test set. Results show the methodology works correctly. A production system needs 500+ manually annotated parcels.

---

## How the Models Connect

```
Dataset 1 (unlabeled Egypt)
    ↓
Model 1: SITS-BERT Pretraining
    ↓  (load pretrained weights)
Dataset 2 (labeled EuroCrops)
    ↓
Model 2: EuroCrops Transfer Fine-tuning
    ↓  (load transfer weights)
Dataset 1 (weak-labeled Egypt)
    ↓
Model 3: Egypt Domain Adaptation  ← production model
    ↓
sits_bert_finetuned.pt
```

---

*NeuralAlloy · FarmTrust · Menoufia University Faculty of Artificial Intelligence · 2026*
