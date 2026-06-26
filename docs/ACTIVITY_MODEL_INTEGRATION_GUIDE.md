# FarmTrust ML — Teammate Integration Guide
> **Read this file before touching anything.**
> This is the complete handoff document for integrating the ML advisory layer into FarmTrust.
> Written by Fares (ML Lead) · NeuralAlloy · June 2026

---

## Who Should Read This

| Role | What you need from this file |
|---|---|
| **Backend teammate** | How ML inference runs, what files it reads and writes, how to add it to the worker, what the new API field looks like |
| **Frontend teammate** | What `ml_advisory` contains, how to render it, what states to handle, copy-paste component logic |
| **AI agent / Codex** | Full file paths, schemas, function names, integration points, rules to never break |

---

## One-Sentence Summary

I built a SITS-BERT Transformer that reads a land parcel's satellite history and outputs whether it was actively farmed or not. The output is attached as an optional `ml_advisory` field to every existing API response. **The existing rule-based system is untouched and remains authoritative.**

---

## Table of Contents

1. What was built
2. What files exist and where
3. How the ML pipeline runs (step by step)
4. The output artifact — `sits_prediction.json`
5. How it connects to the API
6. Backend integration instructions
7. Frontend integration instructions
8. How to run ML inference locally
9. How to get the model file
10. What the model takes as input (exact dimensions)
11. What the model outputs (exact schema)
12. Rules that must never be broken
13. What to do when things go wrong
14. What comes next

---

## 1. What Was Built

Three things were built and committed to the branch `feature/agri-activity-ml-pipeline`:

**A. A new Python subpackage** at `farmtrust_core/ml/` that reads from the existing preprocessing artifacts and runs ML inference. It does not modify any existing code.

**B. A trained SITS-BERT Transformer model** saved at `models/sits_bert_finetuned.pt` (gitignored — see Section 9 for how to download). This model takes a parcel's satellite time series and classifies each observation as active / bare / sparse / uncertain.

**C. A new optional field `ml_advisory`** added to the existing API response. It is `null` when the model file is not present. When the model is present, it contains the ML verdict alongside the existing rule-based verdict.

---

## 2. What Files Exist and Where

### New files (created by ML work)

```
farmtrust_core/
└── ml/
    ├── __init__.py
    ├── sequence_builder.py     ← reads ndvi_smoothed.csv → builds model input tensor
    ├── weak_labeler.py         ← generates training labels from season_windows.json
    ├── normalization.py        ← Z-score normalization for model features
    └── inference.py            ← loads model, runs prediction, writes sits_prediction.json

scripts/
    ├── build_sits_dataset.py   ← packages AOI data into .npz for Kaggle training
    ├── run_sits_inference.py   ← CLI: run ML inference on one AOI
    ├── download_from_kaggle.sh ← downloads trained model from Kaggle
    ├── create_proxy_test_set.py
    ├── auto_annotate_aois.py
    └── merge_annotations.py

kaggle/
    ├── sits_bert/              ← SITS-BERT model architecture code
    │   ├── config.py
    │   ├── dataset.py
    │   ├── model.py
    │   ├── pretrain.py
    │   └── finetune.py
    └── notebooks/
        ├── 00_ingest_egypt_aois.ipynb
        ├── 02_pretrain.ipynb
        ├── 03_finetune.ipynb
        └── 05_transfer_finetune.ipynb

evaluation/
    ├── metrics.py              ← evaluation against test set
    └── threshold_tuner.py      ← finds optimal decision threshold

data/
└── ml/
    ├── labels/
    │   ├── test_set.csv        ← ⛔ SACRED — never load during training
    │   ├── manual_annotations.csv
    │   └── weak_labels.csv
    ├── export/
    │   ├── sits_dataset.npz    ← Kaggle training data (gitignored)
    │   └── sits_dataset_v2.npz ← v2 with manual labels (gitignored)
    └── <aoi_id>/
        └── sits_prediction.json ← ML output per AOI (gitignored)

models/                         ← entire folder gitignored
    ├── sits_bert_pretrained.pt
    ├── sits_bert_finetuned.pt  ← THE production model
    ├── normalization_stats.json
    └── model_card.json

docs/
    ├── ACTIVITY_MODEL_DECISION_LOG.md
    ├── ACTIVITY_MODEL_IMPLEMENTATION_LOG.md
    ├── ACTIVITY_MODEL_REFERENCE.md
    ├── ACTIVITY_MODEL_INTEGRATION_GUIDE.md  ← this file
    └── visuals/
        ├── visuals_manifest.csv
        └── *.png               ← all generated visuals
```

### Existing files modified (minimal changes only)

```
pyproject.toml          ← added [ml] optional dependencies group
api/worker.py           ← added one optional ML inference call after scoring step
api/schemas.py          ← added optional MLAdvisoryOutput field to response
api/assessment_mapper.py ← added map_ml_advisory() function
```

---

## 3. How the ML Pipeline Runs (Step by Step)

This runs **after** the existing pipeline finishes for an AOI. It does not replace any existing step.

```
Step 1 — Existing pipeline runs as normal:
    ingest → ndvi_smoothed.csv
           → quality_metrics.json
           → season_windows.json
           → land_assessment.json

Step 2 — ML inference triggers (in api/worker.py, after scoring):
    run_inference_if_model_available(aoi_id, data_root)

Step 3 — SequenceBuilder reads existing artifacts:
    Reads: data/preprocess/<aoi_id>/ndvi_smoothed.csv
    Keeps only is_usable=True rows
    Computes 10 features per observation
    Pads to 64 timesteps
    Output: tensor shape [64, 10] + attention_mask [64]

Step 4 — SITS-BERT model runs:
    Input:  [64, 10] float32 tensor
    Output: [64, 4]  float32 probability matrix
    Classes: [active, bare, sparse, uncertain]

Step 5 — False-active gate applied:
    If P(active) < 0.65 for a timestep → zero out active, add to uncertain
    This prevents false active predictions

Step 6 — HMM smoother runs:
    Converts noisy per-timestep probabilities → clean state sequence
    Enforces temporal consistency (can't flip active→bare→active in 3 days)

Step 7 — Cycle extractor runs:
    Groups consecutive same-label timesteps into cultivation windows
    Adds start_date, end_date, duration_days, mean_confidence per window

Step 8 — Output written:
    Writes: data/ml/<aoi_id>/sits_prediction.json

Step 9 — API assembles response:
    Reads sits_prediction.json via map_ml_advisory()
    Attaches as ml_advisory field in response
    If model not available or inference failed → ml_advisory = null
```

---

## 4. The Output Artifact — `sits_prediction.json`

**Location:** `data/ml/<aoi_id>/sits_prediction.json`

**Full schema:**

```json
{
  "schema_version": "ml-1.0",
  "pipeline_version": "sits-bert-v0.1",
  "aoi_id": "aoi_demo_01",
  "model_version": "sits-bert-transfer-v1",
  "inference_timestamp": "2026-06-10T14:32:10Z",
  "model_confidence_threshold": 0.65,

  "ml_land_status": "active",
  "ml_lender_decision": "loan_eligible",
  "ml_assessment_confidence": "high",
  "ml_false_active_risk": "low",
  "ml_review_recommendation": "no_review_required",

  "thresholds": {
    "confirmed_active": 0.80,
    "possible_active": 0.65
  },

  "observations": [
    {
      "timestamp": "2023-03-15",
      "ml_label": "active",
      "ml_probabilities": {
        "active": 0.87,
        "bare": 0.06,
        "sparse": 0.05,
        "uncertain": 0.02
      },
      "ml_confidence": 0.87,
      "is_usable": true
    }
  ],

  "ml_activity_windows": [
    {
      "window_id": "ml_w01",
      "label": "active",
      "start_date": "2023-11-10",
      "end_date": "2024-04-25",
      "duration_days": 166,
      "mean_confidence": 0.84,
      "min_confidence": 0.71,
      "observation_count": 22,
      "false_active_gates_triggered": []
    }
  ],

  "ml_summary": {
    "pct_observations_active": 0.61,
    "pct_observations_bare": 0.31,
    "pct_observations_sparse": 0.05,
    "pct_observations_uncertain": 0.03,
    "ml_activity_window_count": 4,
    "false_active_gates_triggered": []
  },

  "advisory_note": "ML output is advisory. Rule-based assessment in land_assessment.json remains authoritative."
}
```

**Field reference:**

| Field | Type | Meaning |
|---|---|---|
| `ml_land_status` | string | Overall ML verdict: `active` / `bare` / `sparse` / `uncertain` |
| `ml_assessment_confidence` | string | `high` / `medium` / `low` based on mean confidence score |
| `ml_false_active_risk` | string | `low` / `medium` / `high` — risk that active prediction is wrong |
| `ml_lender_decision` | string | `loan_eligible` / `not_eligible` / `insufficient_evidence` |
| `ml_activity_windows` | array | List of detected cultivation periods with dates and confidence |
| `ml_summary.pct_observations_active` | float | Fraction of observations classified as active (0–1) |
| `observations` | array | Per-observation ML labels and probabilities |

---

## 5. How It Connects to the API

### What was added to `api/schemas.py`

```python
from typing import Optional
from pydantic import BaseModel

class MLAdvisoryOutput(BaseModel):
    ml_land_status: Optional[str] = None
    ml_assessment_confidence: Optional[str] = None
    ml_false_active_risk: Optional[str] = None
    ml_lender_decision: Optional[str] = None
    ml_activity_window_count: Optional[int] = None
    ml_model_version: Optional[str] = None
    advisory_note: str = "ML output is advisory. Rule-based assessment remains authoritative."

# This field was added to the existing assessment response model:
ml_advisory: Optional[MLAdvisoryOutput] = None
```

### What was added to `api/worker.py`

```python
# Added after the existing scoring step — do not move this
from farmtrust_core.ml.inference import run_inference_if_model_available

try:
    run_inference_if_model_available(aoi_id=aoi_id, data_root=DATA_ROOT)
except Exception as e:
    logger.warning(f"ML inference skipped for {aoi_id}: {e}")
    # Job continues normally even if ML fails
```

### What was added to `api/assessment_mapper.py`

```python
from pathlib import Path
from api.schemas import MLAdvisoryOutput
import json

def map_ml_advisory(aoi_id: str, data_root: str) -> Optional[MLAdvisoryOutput]:
    path = Path(data_root) / "ml" / aoi_id / "sits_prediction.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return MLAdvisoryOutput(
            ml_land_status=data.get("ml_land_status"),
            ml_assessment_confidence=data.get("ml_assessment_confidence"),
            ml_false_active_risk=data.get("ml_false_active_risk"),
            ml_lender_decision=data.get("ml_lender_decision"),
            ml_activity_window_count=data.get("ml_summary", {}).get("ml_activity_window_count"),
            ml_model_version=data.get("model_version"),
        )
    except Exception:
        return None  # Never raise — ml_advisory degrades to null silently
```

### Final API response shape

```json
{
  "land_id": "EG-BHR-2024-00341",
  "land_status": "active",
  "assessment_confidence": "high",
  "activity_windows": [...],

  "ml_advisory": {
    "ml_land_status": "active",
    "ml_assessment_confidence": "high",
    "ml_false_active_risk": "low",
    "ml_lender_decision": "loan_eligible",
    "ml_activity_window_count": 4,
    "ml_model_version": "sits-bert-transfer-v1",
    "advisory_note": "ML output is advisory. Rule-based assessment remains authoritative."
  }
}
```

When model is not available:
```json
{
  "land_status": "active",
  "ml_advisory": null
}
```

---

## 6. Backend Integration Instructions

### If you are adding a new API endpoint or extending the existing one

**Step 1:** Import the mapper function:
```python
from api.assessment_mapper import map_ml_advisory
```

**Step 2:** After building the response object, attach ML advisory:
```python
response.ml_advisory = map_ml_advisory(aoi_id=aoi_id, data_root=DATA_ROOT)
```

That is all. The function returns `None` if the model is not available — Pydantic serializes it as `null` automatically.

### If you need to trigger ML inference manually

```python
from farmtrust_core.ml.inference import run_inference_if_model_available

run_inference_if_model_available(aoi_id="aoi_demo_01", data_root="data")
# Writes: data/ml/aoi_demo_01/sits_prediction.json
# Returns: None (always — check the file, not the return value)
```

### If you replace the model file

⚠️ **Critical:** After replacing `models/sits_bert_finetuned.pt`, you must delete all stale prediction artifacts and re-run inference. Otherwise the API returns predictions from the old model.

```bash
# Delete stale artifacts
find data/ml/ -name "sits_prediction.json" -delete

# Re-run inference for all AOIs
for aoi_id in $(ls data/preprocess/); do
    uv run python scripts/run_sits_inference.py --aoi-id $aoi_id
done
```

### Environment variables needed

```bash
# .env
MODEL_DIR=./models
DATA_ROOT=./data
```

---

## 7. Frontend Integration Instructions

### The `ml_advisory` object

Your API response now has an optional `ml_advisory` object. Always null-check before using it.

### ml_land_status values and what to show

| Value | Color | Badge text | When to show |
|---|---|---|---|
| `"active"` | Green `#1A5C38` | ✓ Active Farm | Always |
| `"bare"` | Red `#DC2626` | ✗ No Activity | Always |
| `"sparse"` | Amber `#D97706` | ~ Weak Activity | Always |
| `"uncertain"` | Gray `#6B7280` | — Insufficient Data | Optional — can hide |
| `null` | — | (hide entire ML section) | When model not deployed |

### ml_assessment_confidence values

| Value | Meaning | UI suggestion |
|---|---|---|
| `"high"` | P(label) > 0.85 | Show confidence as-is |
| `"medium"` | P(label) 0.65–0.85 | Show with note "moderate confidence" |
| `"low"` | P(label) < 0.65 | Show greyed out or with warning |

### React component — minimal implementation

```tsx
// components/MLAdvisoryBadge.tsx

interface MLAdvisory {
  ml_land_status: string | null
  ml_assessment_confidence: string | null
  ml_false_active_risk: string | null
  ml_activity_window_count: number | null
  ml_model_version: string | null
  advisory_note: string
}

interface Props {
  mlAdvisory: MLAdvisory | null
}

const statusColors = {
  active: 'bg-green-800 text-white',
  bare: 'bg-red-600 text-white',
  sparse: 'bg-amber-600 text-white',
  uncertain: 'bg-gray-500 text-white',
}

export function MLAdvisoryBadge({ mlAdvisory }: Props) {
  // Always null-check first
  if (!mlAdvisory) return null

  const colorClass = statusColors[mlAdvisory.ml_land_status ?? 'uncertain']

  return (
    <div className="border-l-4 border-green-600 bg-green-50 p-4 rounded-r">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          ✦ AI Advisory
        </span>
      </div>

      <span className={`px-3 py-1 rounded font-bold text-sm ${colorClass}`}>
        {mlAdvisory.ml_land_status?.toUpperCase() ?? 'UNKNOWN'}
      </span>

      <p className="text-sm text-gray-600 mt-2">
        Model confidence: <strong>{mlAdvisory.ml_assessment_confidence?.toUpperCase()}</strong>
        {' · '}{mlAdvisory.ml_model_version}
      </p>

      {mlAdvisory.ml_activity_window_count !== null && (
        <p className="text-sm text-gray-600">
          {mlAdvisory.ml_activity_window_count} cultivation windows detected
        </p>
      )}

      <p className="text-xs text-gray-400 italic mt-2">
        {mlAdvisory.advisory_note}
      </p>
    </div>
  )
}
```

### React component — disagreement alert (most important feature)

```tsx
// components/MLDisagreementAlert.tsx

interface Props {
  officialStatus: string
  mlAdvisory: MLAdvisory | null
}

export function MLDisagreementAlert({ officialStatus, mlAdvisory }: Props) {
  if (!mlAdvisory) return null
  if (!mlAdvisory.ml_land_status) return null

  // Normalize intermittent → active for comparison
  const normalize = (s: string) =>
    ['active', 'intermittent'].includes(s) ? 'active' : s

  const agree = normalize(officialStatus) === normalize(mlAdvisory.ml_land_status)

  if (agree) {
    return (
      <div className="flex items-center gap-2 text-green-700 text-sm mt-2">
        <span>✓</span>
        <span>AI and rule-based systems agree — high confidence</span>
      </div>
    )
  }

  return (
    <div className="bg-amber-50 border border-amber-300 rounded p-3 mt-2 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-amber-600">⚠</span>
        <span className="text-sm text-amber-800 font-medium">
          AI model and rule-based system disagree on this parcel.
          Manual review recommended before loan approval.
        </span>
      </div>
      <button className="bg-amber-500 text-white text-sm px-3 py-1 rounded ml-4 whitespace-nowrap">
        Request Manual Inspection
      </button>
    </div>
  )
}
```

### Cultivation timeline component

```tsx
// components/CultivationTimeline.tsx
// Reads from ml_advisory via sits_prediction.json activity windows

interface ActivityWindow {
  window_id: string
  label: string
  start_date: string
  end_date: string
  duration_days: number
  mean_confidence: number
}

interface Props {
  windows: ActivityWindow[]
  startYear: number
  endYear: number
}

export function CultivationTimeline({ windows, startYear, endYear }: Props) {
  // Render a horizontal timeline bar
  // Green blocks = active windows
  // Gray blocks = fallow/bare gaps between active windows
  // X-axis = years from startYear to endYear
  // See vis_08_frontend_mockup.png for the design reference
}
```

### Where to use these components

```tsx
// In your land assessment page / component:

import { MLAdvisoryBadge } from '@/components/MLAdvisoryBadge'
import { MLDisagreementAlert } from '@/components/MLDisagreementAlert'
import { CultivationTimeline } from '@/components/CultivationTimeline'

export function LandAssessmentPage({ assessment }) {
  return (
    <div>
      {/* Existing official assessment section */}
      <OfficialAssessmentCard assessment={assessment} />

      {/* New ML advisory section — renders nothing if ml_advisory is null */}
      <MLAdvisoryBadge mlAdvisory={assessment.ml_advisory} />

      {/* Agreement / disagreement indicator */}
      <MLDisagreementAlert
        officialStatus={assessment.land_status}
        mlAdvisory={assessment.ml_advisory}
      />

      {/* Cultivation timeline — only if ML data available */}
      {assessment.ml_advisory && (
        <CultivationTimeline
          windows={assessment.ml_advisory.ml_activity_windows ?? []}
          startYear={2020}
          endYear={2025}
        />
      )}
    </div>
  )
}
```

---

## 8. How to Run ML Inference Locally

### Install ML dependencies

```bash
uv sync --extra ml
```

### Run inference on one AOI

```bash
uv run python scripts/run_sits_inference.py --aoi-id aoi_demo_01 --data-root data --model-dir models
```

Output: `data/ml/aoi_demo_01/sits_prediction.json`

### Run inference on all AOIs

```bash
for aoi_id in $(ls data/preprocess/); do
    echo "Running: $aoi_id"
    uv run python scripts/run_sits_inference.py --aoi-id $aoi_id
done
```

### Run evaluation

```bash
uv run python evaluation/metrics.py
```

Note: prints a warning that test_set.csv is being loaded. This is expected.

### Run all tests (existing + ML)

```bash
uv run pytest tests/ -v
# Expected: 21/21 passing
```

---

## 9. How to Get the Model File

The model file (models/sits_bert_finetuned.pt) is gitignored.
Download the model files from the NeuralAlloy shared Drive:
https://drive.google.com/drive/folders/17XcWRgMFkpXeaA6kwc9Ak4_XATIjFVh2
(access requires company email)

Files to download from the models/ folder:
  sits_bert_finetuned.pt    → save to: models/sits_bert_finetuned.pt
  normalization_stats.json  → save to: models/normalization_stats.json

Or via Kaggle CLI:

```bash
kaggle kernels output faresmamdou/farmtrust-sits-bert-transfer-finetune -p models/
mv models/sits_bert_transfer_finetuned.pt models/sits_bert_finetuned.pt
```

### Verify the model downloaded correctly

```bash
uv run python -c "
import torch
ckpt = torch.load('models/sits_bert_finetuned.pt', map_location='cpu')
print('Model version:', ckpt.get('model_version', 'unknown'))
print('Optimal threshold:', ckpt.get('optimal_threshold', 0.65))
print('Val precision active:', ckpt.get('val_precision_active', 'not set'))
print('OK')
"
```

Expected output:
```
Model version: sits-bert-transfer-v1
Optimal threshold: 0.65
Val precision active: 0.9147
OK
```

---

## 10. What the Model Takes as Input (Exact Dimensions)

The model does **not** take images. It does **not** take text. It takes a **numerical time series**.

```
Input shape per parcel: [64, 10]

64 = number of timesteps (observations in time)
     Real observations are left-padded if fewer than 64 exist
     Padding is zeros with attention_mask = 0

10 = features per timestep:
     Index 0: ndvi            — Normalized Difference Vegetation Index
     Index 1: evi             — Enhanced Vegetation Index
     Index 2: ndmi            — Normalized Difference Moisture Index
     Index 3: ndwi            — Normalized Difference Water Index
     Index 4: bsi             — Bare Soil Index (computed from ndmi and ndvi)
     Index 5: valid_fraction  — fraction of valid satellite pixels in that observation
     Index 6: doy_sin         — sin(2π × day_of_year / 365)
     Index 7: doy_cos         — cos(2π × day_of_year / 365)
     Index 8: gap_days        — days since previous observation (0 for first)
     Index 9: is_usable       — 1.0 if observation passed quality filter, else 0.0

Attention mask shape: [64]
     1 = real observation
     0 = padding (model ignores these)

DOY sequence shape: [64]
     integer day-of-year per timestep
     0 for padding positions

Data type: float32
Normalization: Z-score applied per feature using models/normalization_stats.json
```

---

## 11. What the Model Outputs (Exact Schema)

```
Raw model output shape: [64, 4]

64 = timesteps (same as input)
4  = class probabilities per timestep:
     Index 0: P(active)    — probability this timestep is in a crop cycle
     Index 1: P(bare)      — probability this timestep is fallow/bare soil
     Index 2: P(sparse)    — probability this timestep has weak vegetation
     Index 3: P(uncertain) — probability evidence is insufficient

After false-active gate:
     If P(active) < 0.65 → P(active) set to 0, redistributed to P(uncertain)

After HMM smoothing:
     Per-timestep state sequence: [64] — integer 0/1/2/3

After cycle extraction:
     List of CultivationWindow objects:
     {
       start_date: "2023-11-10",
       end_date: "2024-04-25",
       label: "active",
       mean_confidence: 0.84,
       min_confidence: 0.71,
       observation_count: 22,
       duration_days: 166
     }

Final parcel verdict:
     ml_land_status: "active" | "bare" | "sparse" | "uncertain"
     ml_assessment_confidence: "high" | "medium" | "low"
```

---

## 12. Rules That Must Never Be Broken

These rules are not suggestions. Breaking them corrupts the product.

```
RULE 1: Never replace land_status with ml_land_status.
        land_status is the authoritative lender decision.
        ml_land_status is advisory only.
        A bank approves loans based on land_status, not ml_land_status.

RULE 2: Never crash if ml_advisory is null.
        The model file may not be deployed on every machine.
        Always null-check before accessing any ml_advisory field.

RULE 3: Never load data/ml/labels/test_set.csv during training.
        This file is the held-out evaluation set.
        Loading it during training invalidates all reported metrics.
        Only evaluation/metrics.py is allowed to load it.

RULE 4: After replacing models/sits_bert_finetuned.pt,
        delete all sits_prediction.json files and re-run inference.
        Stale artifacts will make the API return old model predictions.

RULE 5: Never modify farmtrust_core/scoring/ for ML purposes.
        The ML module reads from pipeline artifacts only.
        It does not touch the rule-based scoring logic.

RULE 6: The ml_advisory field must never appear in the official
        lender PDF report or loan decision letter.
        It is a UI advisory feature only.

RULE 7: Never set the decision threshold below 0.65.
        A false active prediction (calling empty land a working farm)
        enables loan fraud. The 0.65 threshold is a business constraint.
```

---

## 13. What to Do When Things Go Wrong

### ml_advisory is always null

Check if the model file exists:
```bash
ls -lh models/sits_bert_finetuned.pt
# If missing: download from Kaggle (see Section 9)
```

Check if torch is installed:
```bash
uv run python -c "import torch; print(torch.__version__)"
# If error: uv sync --extra ml
```

Check if inference ran:
```bash
ls data/ml/<aoi_id>/sits_prediction.json
# If missing: uv run python scripts/run_sits_inference.py --aoi-id <aoi_id>
```

---

### ml_land_status is always "uncertain"

This means the model is running but outputting low confidence. Most likely cause: stale prediction artifacts from before transfer training. Fix:

```bash
find data/ml/ -name "sits_prediction.json" -delete
uv run python scripts/run_sits_inference.py --aoi-id <aoi_id>
```

---

### Evaluation shows precision = 0.0

Same cause as above — stale artifacts. Delete and re-infer.

---

### Import error: No module named 'torch'

```bash
uv sync --extra ml
# NOT: pip install torch
# Always use uv to stay in the project virtual environment
```

---

### Kaggle kernel fails with "farmtrust_core not found"

The dynamic path finder in the notebook handles this. If it still fails:
```python
import os
print(os.listdir('/kaggle/input'))
# Find where farmtrust-sits-code is mounted and update find_farmtrust_core()
```

---

## 14. What Comes Next

These are the confirmed next steps, in priority order:

**1. Real labeled test set (highest priority)**
Replace `data/ml/labels/test_set.csv` proxy labels with manually annotated ground truth. The annotation tool is already built: `scripts/annotate_aois.py`. Target: 50+ parcels labeled by a domain expert or field-verified by bank inspectors.

**2. More Egypt AOIs**
Ingest 50–100 additional Egypt parcels through the existing pipeline and add them to the Kaggle training dataset. More diverse training data = better generalization across Egyptian governorates.

**3. Sentinel-1 SAR integration**
Add radar satellite data (Sentinel-1) alongside Sentinel-2 optical data. Radar penetrates clouds, making the model robust to Egypt's winter cloud cover. The feature pipeline is already designed to accept SAR inputs at index positions 10–15.

**4. Presto backbone evaluation**
Test NASA Harvest's Presto model (https://github.com/nasaharvest/presto) as an alternative backbone. It was pretrained on 21.5 million global pixel time series including African agriculture. May outperform SITS-BERT on Egypt data.

**5. Crop classification**
Once activity detection is stable, add a second model head that classifies what crop is being grown: wheat, rice, maize, cotton, berseem clover. Requires crop-labeled Egypt ground truth.

---

## Quick Reference

```bash
# Install ML deps
uv sync --extra ml

# Run inference on one AOI
uv run python scripts/run_sits_inference.py --aoi-id aoi_demo_01

# Run all tests
uv run pytest tests/ -v

# Download model from Kaggle
kaggle kernels output faresmamdou/farmtrust-sits-bert-transfer-finetune -p models/
mv models/sits_bert_transfer_finetuned.pt models/sits_bert_finetuned.pt

# Delete stale inference artifacts
find data/ml/ -name "sits_prediction.json" -delete

# Run evaluation
uv run python evaluation/metrics.py

# Check model is valid
uv run python -c "import torch; ckpt=torch.load('models/sits_bert_finetuned.pt',map_location='cpu'); print('OK:', ckpt.get('model_version'))"
```

---

*Written by Fares · ML Lead · NeuralAlloy · FarmTrust · June 2026*
*Branch: feature/agri-activity-ml-pipeline · 29 commits · 21/21 tests passing*
*Questions: read ACTIVITY_MODEL_DECISION_LOG.md for why decisions were made, ACTIVITY_MODEL_IMPLEMENTATION_LOG.md for what was built*
