# FARMTRUST_AGRICULTURAL_ACTIVITY_ML_PLAN_p2.md
> **FarmTrust · NeuralAlloy**
> Module: SITS-BERT Transfer Learning + Manual Annotation
> Maintained by: Fares (ML lead)
> Parent plan: `docs/FARMTRUST_AGRICULTURAL_ACTIVITY_ML_PLAN.md`
> Branch: `feature/agri-activity-ml-pipeline`
> Goal: `precision_active >= 0.80` on manually annotated test set

---

## READ THIS FIRST — Claude Code Instructions

Phases 0–7 of the parent plan are **complete**. Do not re-read or re-execute them.
This file picks up where the parent plan ended.
Read this file fully before touching any file.
Work the lowest incomplete phase. Commit after each phase. Never skip ahead.

### Operating rules (inherited + additions)

1. Never overwrite existing files in `farmtrust_core/`, `api/`, `contracts/`, `portal/` unless a phase explicitly names the exact change.
2. All new code in this plan lives in `scripts/` or `kaggle/notebooks/` only.
3. All new dependencies go into `pyproject.toml` under `[project.optional-dependencies] ml` only.
4. `data/ml/labels/test_set.csv` is sacred — never loaded during training.
5. All random seeds = 42.
6. Commit format: `feat(sits-t-p2): phase-XN — <what was built>`
7. **STOP and wait for human input** wherever a phase says `⏸ HUMAN STEP`.
8. Current phase = lowest phase with `STATUS: [ ]`.

---

## Label Mapping — EuroCropsML HCAT → Our 4 Classes

| EuroCropsML HCAT class | Our label | Integer |
|---|---|---|
| Winter wheat, spring wheat, durum wheat, triticale | active | 0 |
| Grassland, meadow, clover, alfalfa, berseem | active | 0 |
| Fallow land, bare soil, set-aside | bare | 1 |
| Catch crop, cover crop, green manure | sparse | 2 |
| Everything else (maize, sunflower, potato, etc.) | uncertain | 3 |

> Rationale: wheat and grass phenology in Latvia is the closest
> European analogue to Egypt winter crops (wheat, berseem).
> We only transfer active/bare/sparse signal — not crop type.

---

## Feature Mapping — EuroCrops Bands → Our 10 Features

| Our feature | Source if raw bands available | Source if indices only |
|---|---|---|
| `ndvi` | `(B08-B04)/(B08+B04)` | use `NDVI` column directly |
| `evi` | `2.5*(B08-B04)/(B08+6*B04-7.5*B02+1)` | use `EVI` column directly |
| `ndmi` | `(B08-B11)/(B08+B11)` | use `NDMI` column if available, else `0.0` |
| `ndwi` | `(B03-B08)/(B03+B08)` | use `NDWI` column if available, else `0.0` |
| `bare_soil_proxy` | `(ndmi-ndvi)/(ndmi+ndvi+1e-6)` | compute from ndvi/ndmi |
| `valid_fraction` | `1.0` (EuroCrops has no cloud mask) | `1.0` |
| `doy_sin` | `sin(2*pi*doy/365)` | same |
| `doy_cos` | `cos(2*pi*doy/365)` | same |
| `observation_gap_days` | diff between consecutive timestamps | same |
| `is_usable_float` | `1.0` (all EuroCrops obs are valid) | `1.0` |

> If a column is missing set it to `0.0` and log a warning.
> Never raise on missing features — degrade gracefully.

---

## Kaggle Workflow for This Plan

```
LOCAL                                    KAGGLE
─────────────────────────────────────    ──────────────────────────────
Phase C1-C3: Install + convert EuroCrops → data/eurocrops/eurocrops_transfer.npz
Phase C4:    Write notebook 05           → kaggle/notebooks/05_transfer_finetune.ipynb
Phase C5:    Upload eurocrops dataset    → faresmamdou/farmtrust-eurocrops
Phase C6:    Push + run notebook 05      → sits_bert_transfer_finetuned.pt
             ⏸ HUMAN: download model
Phase A1-A2: Annotation tool + merge script (runs locally, no Kaggle)
Phase A3:    ⏸ HUMAN: label 14 AOIs interactively
Phase F1:    ⏸ HUMAN: confirm model downloaded
Phase F2-F3: Merge labels + rebuild dataset v2
Phase F4:    Upload v2 + retrain          → sits_bert_final.pt
             ⏸ HUMAN: download final model
Phase F5:    Run evaluation — target precision_active >= 0.80
Phase F6:    Commit + PR summary
```

---

## Phases

---

### Phase C1 — Install EuroCropsML + Download Latvia 2021

**STATUS:** `[x]`
**Runs on:** Local

**What it does:**
Installs the `eurocropsml` Python package and downloads the Latvia 2021
crop dataset — the smallest country file with wheat, grass, and fallow classes.

**Commands:**
```bash
uv run pip install eurocropsml

uv run python -c "
from eurocropsml.dataset import EuroCropsDataset
ds = EuroCropsDataset(
    root='data/eurocrops/',
    country='Latvia',
    year=2021,
    download=True
)
print('Downloaded. Classes:', ds.classes[:10])
print('Total samples:', len(ds))
"
```

If the Python API fails, use CLI fallback:
```bash
uv run eurocropsml download --country Latvia --year 2021 \
  --output-dir data/eurocrops/
```

After download, run:
```bash
find data/eurocrops/ -type f | sort
du -sh data/eurocrops/
```
Print full output.

**Commit:** `feat(sits-t-p2): phase-C1 — eurocrops Latvia 2021 downloaded`

**Success criteria:** `data/eurocrops/` contains at least one `.parquet` or `.npz` file. Total size > 10 MB.

---

### Phase C2 — Inspect EuroCropsML Schema

**STATUS:** `[x]`
**Runs on:** Local

**What it does:**
Reads the downloaded EuroCrops data and prints its full schema so we
know exactly which columns to use in the converter.

**Script to run inline (not a file):**
```python
import pandas as pd, glob, json

files = glob.glob('data/eurocrops/**/*.parquet', recursive=True) + \
        glob.glob('data/eurocrops/**/*.csv', recursive=True)

print(f"Files found: {len(files)}")
for f in files[:3]:
    df = pd.read_parquet(f) if f.endswith('.parquet') else pd.read_csv(f)
    print(f"\n=== {f} ===")
    print("Columns:", df.columns.tolist())
    print("Shape:", df.shape)
    print("Date range:", df.filter(like='date').iloc[:,0].min(),
          "→", df.filter(like='date').iloc[:,0].max()
          if len(df.filter(like='date').columns) > 0 else "no date col")
    print("Crop classes:", df['crop_label'].value_counts().head(15)
          if 'crop_label' in df.columns else "no crop_label col")
    print("Sample row:", df.iloc[0].to_dict())
```

Save output to `data/eurocrops/schema_inspection.txt`:
```bash
uv run python <above script> > data/eurocrops/schema_inspection.txt
cat data/eurocrops/schema_inspection.txt
```

**Commit:** `feat(sits-t-p2): phase-C2 — eurocrops schema inspection`

**Success criteria:** `schema_inspection.txt` exists and contains column names, shape, and at least 5 crop class names.

---

### Phase C3 — Create `scripts/convert_eurocrops.py`

**STATUS:** `[x]`
**Runs on:** Local

**What it does:**
Converts EuroCrops Latvia data into our SITS-BERT `.npz` format
using the label and feature mappings defined at the top of this file.

**Implement this script:**

```python
"""
scripts/convert_eurocrops.py

Converts EuroCropsML Latvia 2021 → farmtrust SITS-BERT .npz format.

Usage:
  python scripts/convert_eurocrops.py \
    --input-dir data/eurocrops/ \
    --output data/eurocrops/eurocrops_transfer.npz \
    --max-parcels 5000

Output .npz keys:
  features:       (N, 64, 10)  float32
  attention_mask: (N, 64)      bool
  doy:            (N, 64)      int16
  labels:         (N, 64)      int8   (same label for every timestep)
  parcel_ids:     (N,)         object

Label mapping: use LABEL MAPPING table from top of this plan.
Feature mapping: use FEATURE MAPPING table from top of this plan.
Max sequence length: 64 (left-pad with zeros, attention_mask=0 for padding).
Seed: 42 for any shuffling.

Print manifest at end:
  Total parcels converted: N
  Label distribution: {active: X, bare: Y, sparse: Z, uncertain: W}
  Skipped (too short < 5 obs): K
  Mean sequence length before padding: M
  Output file size: X MB
"""
```

After implementing, run:
```bash
uv run python scripts/convert_eurocrops.py \
  --input-dir data/eurocrops/ \
  --output data/eurocrops/eurocrops_transfer.npz \
  --max-parcels 5000
```

Print full manifest output.

**Commit:** `feat(sits-t-p2): phase-C3 — eurocrops converter script`

**Success criteria:** `eurocrops_transfer.npz` exists. `active` label count > 500. File size > 1 MB. Loads correctly with `np.load(..., allow_pickle=True)`.

---

### Phase C4 — Create `kaggle/notebooks/05_transfer_finetune.ipynb`

**STATUS:** `[x]`
**Runs on:** Local (write) → Kaggle (execute in C6)

**What it does:**
Two-stage training notebook: (1) fine-tune on EuroCrops for transfer,
(2) domain-adapt on Egypt AOI data with lower LR.

**Notebook cells in exact order:**

```
Cell 1 — Install:
  !pip install torch numpy scikit-learn hmmlearn -q

Cell 2 — Verify inputs:
  import numpy as np, os
  euro = np.load('/kaggle/input/farmtrust-eurocrops/eurocrops_transfer.npz', allow_pickle=True)
  egypt = np.load('/kaggle/input/farmtrust-sits/sits_dataset.npz', allow_pickle=True)
  print("EuroCrops:", euro['features'].shape)
  print("Egypt:", egypt['features'].shape)

Cell 3 — Load sits_bert code:
  import sys
  def find_farmtrust_core():
      for root, dirs, files in os.walk('/kaggle/input'):
          for d in dirs:
              if d == 'sits_bert':
                  path = os.path.join(root, d)
                  sys.path.insert(0, os.path.dirname(path))
                  return os.path.dirname(path)
      raise RuntimeError(f"sits_bert not found. Input: {os.listdir('/kaggle/input')}")
  find_farmtrust_core()
  from sits_bert.model import SITSBertFinetune
  from sits_bert.config import SITSBertConfig
  print("Model imported OK")

Cell 4 — STAGE 1: Fine-tune on EuroCrops (transfer learning):
  config = SITSBertConfig(num_classes=4)
  model = SITSBertFinetune(config)
  # Load pretrained weights
  ckpt = torch.load('/kaggle/input/farmtrust-sits-pretrained/sits_bert_pretrained.pt',
                    map_location='cpu')
  model.encoder.load_state_dict(ckpt['model_state_dict'], strict=False)
  # Train 30 epochs, LR=0.0001, batch=128
  # class_weights=[2.0, 1.0, 1.2, 0.8], seed=42
  # Save: /kaggle/working/sits_bert_euro_transfer.pt
  # Print loss per epoch

Cell 5 — Plot Stage 1 loss curve (save PNG to /kaggle/working/)

Cell 6 — STAGE 2: Domain adapt on Egypt data:
  # Load sits_bert_euro_transfer.pt
  # Train 50 epochs, LR=0.00005, batch=32
  # class_weights=[2.5, 1.0, 1.2, 0.8], label_smoothing=0.1
  # early_stopping patience=10 on precision_active
  # Save best: /kaggle/working/sits_bert_transfer_finetuned.pt
  # with optimal_threshold embedded in checkpoint

Cell 7 — Threshold sweep:
  # Sweep 0.40→0.90 in steps of 0.05
  # Find highest recall where precision_active >= 0.80
  # Print table: threshold | precision | recall | f1 | false_active_rate

Cell 8 — Print classification report + confusion matrix

Cell 9 — List output files:
  for f in os.listdir('/kaggle/working/'):
      print(f, round(os.path.getsize(f'/kaggle/working/{f}')/1e6, 2), 'MB')

Cell 10 — Final message:
  print("=== TRANSFER COMPLETE. Download: sits_bert_transfer_finetuned.pt ===")
```

Comment at top of notebook:
```
# Kaggle settings: GPU T4 x1 | Internet ON | RAM 30GB
# Input datasets:
#   faresmamdou/farmtrust-sits          (sits_dataset.npz)
#   faresmamdou/farmtrust-sits-pretrained (sits_bert_pretrained.pt)
#   faresmamdou/farmtrust-eurocrops     (eurocrops_transfer.npz)
#   faresmamdou/farmtrust-sits-code     (sits_bert/ code)
```

**Commit:** `feat(sits-t-p2): phase-C4 — transfer finetune notebook 05`

**Success criteria:** Notebook file exists. All cells have valid Python syntax. `find_farmtrust_core()` function present in Cell 3.

---

### Phase C5 — Upload EuroCrops Dataset to Kaggle

**STATUS:** `[x]`
**Runs on:** Local

**What it does:**
Packages `eurocrops_transfer.npz` as a new Kaggle dataset and uploads it.

**Commands:**
```bash
mkdir -p kaggle_upload/farmtrust-eurocrops

cp data/eurocrops/eurocrops_transfer.npz \
   kaggle_upload/farmtrust-eurocrops/

cat > kaggle_upload/farmtrust-eurocrops/dataset-metadata.json << 'EOF'
{
  "title": "FarmTrust EuroCrops Transfer",
  "id": "faresmamdou/farmtrust-eurocrops",
  "licenses": [{"name": "CC0-1.0"}]
}
EOF

kaggle datasets create \
  -p kaggle_upload/farmtrust-eurocrops/ \
  --dir-mode zip

echo "Upload complete."
kaggle datasets list --user faresmamdou
```

Also update `farmtrust-sits-code` with notebook 05:
```bash
cp kaggle/notebooks/05_transfer_finetune.ipynb \
   kaggle_upload/farmtrust-sits-code/notebooks/

kaggle datasets version \
  -p kaggle_upload/farmtrust-sits-code/ \
  -m "add notebook 05 transfer finetune"
```

**Commit:** `feat(sits-t-p2): phase-C5 — eurocrops dataset uploaded to Kaggle`

**Success criteria:** `kaggle datasets list --user faresmamdou` shows `farmtrust-eurocrops`. No upload errors.

---

### Phase C6 — Run Notebook 05 on Kaggle

**STATUS:** `[x]`
**Runs on:** Kaggle (via CLI)

**What it does:**
Pushes and runs the two-stage transfer fine-tuning notebook on Kaggle GPU.
Polls until complete, then stops for manual model download.

**Commands:**
```bash
# Create kernel metadata
cat > kaggle/notebooks/kernel-metadata.json << 'EOF'
{
  "id": "faresmamdou/farmtrust-sits-bert-transfer-finetune",
  "title": "FarmTrust SITS-BERT Transfer Finetune",
  "code_file": "05_transfer_finetune.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "dataset_sources": [
    "faresmamdou/farmtrust-sits",
    "faresmamdou/farmtrust-sits-pretrained",
    "faresmamdou/farmtrust-eurocrops",
    "faresmamdou/farmtrust-sits-code"
  ],
  "competition_sources": [],
  "kernel_sources": []
}
EOF

cd kaggle/notebooks
kaggle kernels push -p .
cd ../..

# Poll every 60 seconds
while true; do
  STATUS=$(kaggle kernels status faresmamdou/farmtrust-sits-bert-transfer-finetune \
           2>&1 | grep -i "status")
  echo "[$(date +%H:%M:%S)] $STATUS"
  echo "$STATUS" | grep -qi "complete\|error" && break
  sleep 60
done
```

When complete print:
```
=== Kaggle kernel finished ===
File to download: sits_bert_transfer_finetuned.pt
Save to: models/sits_bert_transfer_finetuned.pt
```

**⏸ HUMAN STEP — STOP HERE.**
Do not download anything. Do not continue to Phase A1.
Wait for human to confirm the file is saved at `models/sits_bert_transfer_finetuned.pt`.

**Commit:** `feat(sits-t-p2): phase-C6 — transfer finetune kernel pushed and complete`

**Success criteria:** Kernel status = COMPLETE. No errors. Human confirms model file downloaded.

---

### Phase A1 — Create `scripts/annotate_aois.py`

**STATUS:** `[x]`
**Runs on:** Local

**What it does:**
Terminal tool that shows each AOI's NDVI timeline + season windows
and lets Fares assign a ground-truth label interactively.

**Implement this script:**

```python
"""
scripts/annotate_aois.py

Interactive terminal annotation tool for Egypt AOIs.
Shows NDVI timeline + detected season windows per AOI.
Saves labels to data/ml/labels/manual_annotations.csv.

Usage: python scripts/annotate_aois.py

For each AOI in data/ml/labels/test_set.csv, displays:
  - AOI ID, usable obs count, season count, quality labels
  - NDVI timeline table (all usable observations)
    columns: date | ndvi | evi | ndmi | season_window
    mark observations inside a detected window with [SEASON]
  - Detected activity windows list with dates + quality
  
Then prompts:
  [1] active       — 2+ confirmed crop seasons visible
  [2] intermittent — 1 season or irregular activity
  [3] sparse       — weak vegetation only, no clear cycle
  [4] bare         — no vegetation activity at all
  [5] skip         — not sure, come back later
  [q] quit         — save and exit

Saves to data/ml/labels/manual_annotations.csv:
  columns: aoi_id, manual_label, annotated_at

At exit prints:
  Annotated: X/N AOIs
  Skipped:   Y AOIs
  Run: python scripts/merge_annotations.py to apply labels
"""
```

After implementing, do NOT run it yet — that happens in Phase A3.

**Commit:** `feat(sits-t-p2): phase-A1 — annotation tool`

**Success criteria:** `python scripts/annotate_aois.py --help` or dry run shows the tool loads without error. Displays correct header for first AOI without crashing.

---

### Phase A2 — Create `scripts/merge_annotations.py`

**STATUS:** `[x]`
**Runs on:** Local

**What it does:**
Merges manual annotations into `test_set.csv` and overrides
matching weak labels in `weak_labels.csv` with high-confidence labels.

**Implement this script:**

```python
"""
scripts/merge_annotations.py

Merges data/ml/labels/manual_annotations.csv into:
  1. data/ml/labels/test_set.csv
     - Replace 'label' with manual_label where annotation exists
     - Set label_source = "manual_annotation"
     - Keep rule_based_proxy where no annotation

  2. data/ml/labels/weak_labels.csv
     - For each manually annotated aoi_id:
       override ALL rows for that aoi_id with:
         label = manual_label (converted to integer 0/1/2/3)
         weak_confidence = 0.95
     - This is how manual labels enter training

Prints:
  Manual annotations loaded: X
  test_set.csv updated: Y rows changed to manual_annotation
  test_set.csv unchanged: Z rows still rule_based_proxy
  weak_labels.csv overridden: W observations across X AOIs
"""
```

After implementing, do NOT run it yet — that happens in Phase F2.

**Commit:** `feat(sits-t-p2): phase-A2 — annotation merge script`

**Success criteria:** Script is importable. Dry run with `--dry-run` flag prints what would change without writing files.

---

### Phase A3 — Run Annotation Tool

**STATUS:** `[x]`
**Runs on:** Local

**What it does:**
Fares labels all 14 AOIs interactively using the terminal tool.

**Commands:**
```bash
python scripts/annotate_aois.py
```

**⏸ HUMAN STEP — STOP HERE.**
Claude Code must NOT continue past this point.
Do not proceed to Phase F1 until human types "done annotating".

When human says "done", print:
```bash
cat data/ml/labels/manual_annotations.csv
```
Show the full annotation file so Fares can confirm.

**Commit:** `feat(sits-t-p2): phase-A3 — manual annotations complete`

**Success criteria:** `manual_annotations.csv` has >= 10 rows (at least 10 of 14 AOIs labeled). At least 2 different label values present (not all the same label).

---

### Phase F1 — Confirm Transfer Model Downloaded

**STATUS:** `[x]`
**Runs on:** Local

**What it does:**
Verifies the transfer model downloaded from Phase C6 is valid
and readable before rebuilding the dataset.

**Commands:**
```bash
python -c "
import torch, json
path = 'models/sits_bert_transfer_finetuned.pt'
ckpt = torch.load(path, map_location='cpu')
print('Epoch:', ckpt.get('epoch', 'unknown'))
print('Optimal threshold:', ckpt.get('optimal_threshold', 'not set'))
print('Val precision active:', ckpt.get('val_precision_active', 'not set'))
print('Keys in checkpoint:', list(ckpt.keys()))
print('MODEL VALID')
"
```

If the file does not exist or fails to load, print:
```
MODEL NOT FOUND at models/sits_bert_transfer_finetuned.pt
Download from Kaggle: faresmamdou/farmtrust-sits-bert-transfer-finetune
Output tab → sits_bert_transfer_finetuned.pt
Save to: models/sits_bert_transfer_finetuned.pt
```
Then stop. Do not continue until the file is valid.

**Commit:** `feat(sits-t-p2): phase-F1 — transfer model verified`

**Success criteria:** `torch.load('models/sits_bert_transfer_finetuned.pt')` succeeds and prints MODEL VALID.

---

### Phase F2 — Merge Annotations

**STATUS:** `[ ]`
**Runs on:** Local

**What it does:**
Applies manual labels to `test_set.csv` and overrides weak labels
in `weak_labels.csv` so training uses human-verified labels.

**Commands:**
```bash
python scripts/merge_annotations.py

# Verify result
echo "=== test_set.csv after merge ==="
python -c "
import pandas as pd
df = pd.read_csv('data/ml/labels/test_set.csv')
print(df[['aoi_id','label','label_source']].to_string())
print('Label distribution:')
print(df['label'].value_counts())
print('Source distribution:')
print(df['label_source'].value_counts())
"
```

**Commit:** `feat(sits-t-p2): phase-F2 — annotations merged into test set + weak labels`

**Success criteria:** `test_set.csv` has at least 10 rows with `label_source = "manual_annotation"`. `weak_labels.csv` has overridden rows with `weak_confidence = 0.95`.

---

### Phase F3 — Rebuild Dataset v2 with Manual Labels

**STATUS:** `[ ]`
**Runs on:** Local

**What it does:**
Rebuilds the SITS dataset `.npz` using the updated `weak_labels.csv`
that now contains high-confidence manual labels for 14 AOIs.

**Commands:**
```bash
python scripts/build_sits_dataset.py \
  --data-root data \
  --output data/ml/export/sits_dataset_v2.npz

# Print manifest
python -c "
import numpy as np
d = np.load('data/ml/export/sits_dataset_v2.npz', allow_pickle=True)
print('Parcels:', d['features'].shape[0])
print('Features shape:', d['features'].shape)
import collections
labels_flat = d['weak_labels'].flatten()
labels_flat = labels_flat[labels_flat != -1]
dist = collections.Counter(labels_flat.tolist())
print('Label distribution:', {str(k): v for k,v in sorted(dist.items())})
import os
size = os.path.getsize('data/ml/export/sits_dataset_v2.npz') / 1e6
print(f'File size: {size:.2f} MB')
"

# Upload v2 to Kaggle
cp data/ml/export/sits_dataset_v2.npz \
   kaggle_upload/farmtrust-sits/

kaggle datasets version \
  -p kaggle_upload/farmtrust-sits/ \
  -m "v2: manual annotation labels override weak labels for 14 AOIs"
```

**Commit:** `feat(sits-t-p2): phase-F3 — sits_dataset_v2 with manual labels uploaded`

**Success criteria:** `sits_dataset_v2.npz` exists. Label distribution shows at least 3 different classes with count > 0. Kaggle dataset version incremented.

---

### Phase F4 — Final Retrain on Kaggle

**STATUS:** `[ ]`
**Runs on:** Kaggle (via CLI)

**What it does:**
Re-runs notebook 05 with v2 dataset (manual labels).
This is the final training run — expect real accuracy.

**Commands:**
```bash
# Update notebook 05 to use sits_dataset_v2.npz
# Change in Cell 2:
#   egypt = np.load('.../sits_dataset.npz') →
#   egypt = np.load('.../sits_dataset_v2.npz')
# Save notebook, then push kernel

cd kaggle/notebooks
kaggle kernels push -p .
cd ../..

# Poll
while true; do
  STATUS=$(kaggle kernels status \
    faresmamdou/farmtrust-sits-bert-transfer-finetune 2>&1)
  echo "[$(date +%H:%M:%S)] $STATUS"
  echo "$STATUS" | grep -qi "complete\|error" && break
  sleep 60
done
```

When complete print:
```
=== FINAL TRAINING COMPLETE ===
File to download: sits_bert_transfer_finetuned.pt
Save to: models/sits_bert_final.pt
```

**⏸ HUMAN STEP — STOP HERE.**
Wait for human to save the file at `models/sits_bert_final.pt`.

**Commit:** `feat(sits-t-p2): phase-F4 — final retrain on v2 dataset complete`

**Success criteria:** Kernel status = COMPLETE. Human confirms `models/sits_bert_final.pt` saved.

---

### Phase F5 — Final Evaluation

**STATUS:** `[ ]`
**Runs on:** Local

**What it does:**
Copies final model into place, runs full evaluation against the
manually annotated test set, and prints the real accuracy report.

**Commands:**
```bash
# Put final model in place
cp models/sits_bert_final.pt models/sits_bert_finetuned.pt

# Update model card
python -c "
import torch, json, datetime
ckpt = torch.load('models/sits_bert_finetuned.pt', map_location='cpu')
card = {
  'model_version': 'sits-bert-transfer-v1',
  'training_date': datetime.date.today().isoformat(),
  'training_data': 'EuroCrops Latvia 2021 + 14 Egypt AOIs (manual labels)',
  'optimal_threshold': ckpt.get('optimal_threshold', 0.65),
  'val_precision_active': ckpt.get('val_precision_active', None),
  'stage1_epochs': 30,
  'stage2_epochs': 50,
}
json.dump(card, open('models/model_card.json', 'w'), indent=2)
print(json.dumps(card, indent=2))
"

# Run full evaluation
python evaluation/metrics.py

# Run threshold tuner
python evaluation/threshold_tuner.py
```

Evaluation must print:
```
╔══════════════════════════════════════════════╗
║  ⚠  TEST SET IS RULE-BASED PROXY            ║  ← or MANUAL ANNOTATION if F2 ran
╚══════════════════════════════════════════════╝

precision_active:    X.XX
recall_active:       X.XX
macro_f1:            X.XX
false_active_rate:   X.XX
brier_score:         X.XX

PASS / FAIL
```

Target: `precision_active >= 0.80` and `false_active_rate <= 0.06`.

If PASS: continue to F6.
If FAIL: print exact gap (e.g. "precision is 0.71, need 0.80")
and stop. Do not mark F5 complete. Report failure.

**Commit:** `feat(sits-t-p2): phase-F5 — final evaluation PASS/FAIL`

**Success criteria:** `precision_active >= 0.80` AND `false_active_rate <= 0.06`. Evaluation script exits cleanly.

---

### Phase F6 — PR Summary + Final Commit

**STATUS:** `[ ]`
**Runs on:** Local

**What it does:**
Writes a PR summary document and makes the final clean commit
ready for team review and merge.

**Create `docs/SITS_TRANSFORMER_PH2_PR_SUMMARY.md`:**

```markdown
# SITS-Transformer Phase 2 — PR Summary

## What was built
- EuroCropsML Latvia 2021 download + conversion to FarmTrust format
- Two-stage transfer fine-tuning: EuroCrops → Egypt domain adaptation
- Interactive terminal annotation tool for Egypt AOIs
- Manual annotation of 14 Egypt AOIs
- Final evaluation: precision_active = X.XX, false_active_rate = X.XX

## Model chain
sits_bert_pretrained.pt (Phase 0-5)
  → sits_bert_euro_transfer.pt (Stage 1: EuroCrops, 30 epochs)
    → sits_bert_final.pt (Stage 2: Egypt manual labels, 50 epochs)

## Test set status
  [manual_annotation / rule_based_proxy]: X / Y parcels
  Replace all proxy labels before lender demo.

## Safe to merge
  - 21 existing tests pass
  - ml_advisory field is optional — no existing API field changed
  - models/ is gitignored — no large files in PR
  - farmtrust_core/scoring/ untouched

## What comes next
  - Annotate remaining proxy-labeled parcels
  - Ingest 50+ AOIs for larger training set
  - Phase 3: Sentinel-1 SAR multimodal model
```

**Commands:**
```bash
git add -A
git commit -m "feat(sits-t-p2): all phases complete — transfer learning + manual annotation"

git log --oneline feature/agri-activity-ml-pipeline ^main | head -20
```

Print total commit count on branch and final phase summary.

**Success criteria:** All phases show `STATUS: [x]`. Working tree is clean. PR summary exists in `docs/`.

---

## Quick Reference — Files Created in This Plan

| File | Phase | Purpose |
|---|---|---|
| `data/eurocrops/eurocrops_transfer.npz` | C3 | EuroCrops converted to SITS-BERT format |
| `data/eurocrops/schema_inspection.txt` | C2 | Schema docs for EuroCrops data |
| `kaggle/notebooks/05_transfer_finetune.ipynb` | C4 | Two-stage Kaggle training notebook |
| `kaggle_upload/farmtrust-eurocrops/` | C5 | Kaggle dataset upload folder |
| `scripts/annotate_aois.py` | A1 | Interactive terminal annotation tool |
| `scripts/merge_annotations.py` | A2 | Merges manual labels into training data |
| `data/ml/labels/manual_annotations.csv` | A3 | Ground-truth labels from Fares |
| `data/ml/export/sits_dataset_v2.npz` | F3 | Training dataset with manual labels |
| `models/sits_bert_final.pt` | F4 | Final trained model |
| `models/model_card.json` | F5 | Model version + metrics |
| `docs/SITS_TRANSFORMER_PH2_PR_SUMMARY.md` | F6 | PR review document |

---

## Human Steps Summary (⏸ points)

| Phase | What you do |
|---|---|
| C6 | Download `sits_bert_transfer_finetuned.pt` → `models/sits_bert_transfer_finetuned.pt` |
| A3 | Run annotation tool and label all 14 AOIs. Type "done annotating" when finished. |
| F1 | Confirm transfer model is at `models/sits_bert_transfer_finetuned.pt` |
| F4 | Download `sits_bert_transfer_finetuned.pt` → `models/sits_bert_final.pt` |

---

*Last updated: June 2026 · NeuralAlloy / FarmTrust · SITS-Transformer Phase 2*
*Claude Code: read this file first · work lowest incomplete phase · commit after each phase*
