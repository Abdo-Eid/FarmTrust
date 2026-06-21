#!/bin/bash
set -e
export PYTHONUTF8="${PYTHONUTF8:-1}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

KAGGLE_USER="${KAGGLE_USER:-faresmamdou}"
OUT_DIR="./models"
PRETRAIN_TMP="./.tmp/phase5_download/pretrain"
FINETUNE_TMP="./.tmp/phase5_download/finetune"
PYTHON_BIN="${PYTHON_BIN:-}"

if [ -z "$PYTHON_BIN" ] && command -v python.exe >/dev/null 2>&1; then
  PYTHON_BIN="python.exe"
fi

if [ -z "$PYTHON_BIN" ]; then
  PYTHON_BIN="python"
fi

run_kaggle() {
  "$PYTHON_BIN" -X utf8 -m kaggle "$@"
}

mkdir -p "$OUT_DIR"
rm -rf "$PRETRAIN_TMP" "$FINETUNE_TMP"
mkdir -p "$PRETRAIN_TMP" "$FINETUNE_TMP"

echo "[1/3] Downloading pretrained weights..."
run_kaggle kernels output "$KAGGLE_USER/farmtrust-sits-bert-pretrain" -p "$PRETRAIN_TMP" --force --file-pattern "^(sits_bert_pretrained\\.pt|normalization_stats\\.json)$"
cp "$PRETRAIN_TMP/sits_bert_pretrained.pt" "$OUT_DIR/"
cp "$PRETRAIN_TMP/normalization_stats.json" "$OUT_DIR/"

echo "[2/3] Downloading finetuned weights..."
run_kaggle kernels output "$KAGGLE_USER/farmtrust-sits-bert-finetune" -p "$FINETUNE_TMP" --force --file-pattern "^sits_bert_finetuned\\.pt$"
cp "$FINETUNE_TMP/sits_bert_finetuned.pt" "$OUT_DIR/"

echo "[3/3] Writing model_card.json..."
"$PYTHON_BIN" -c "
import json
import datetime
import torch
from farmtrust_core.ml.sequence_builder import FEATURE_NAMES

stats_path = '$OUT_DIR/normalization_stats.json'
stats = json.load(open(stats_path))
if 'feature_names' not in stats:
    stats['feature_names'] = FEATURE_NAMES
json.dump(stats, open(stats_path, 'w'), indent=2)

ckpt = torch.load('$OUT_DIR/sits_bert_finetuned.pt', map_location='cpu', weights_only=False)
card = {
  'model_version': 'sits-bert-finetune-v1',
  'download_date': datetime.date.today().isoformat(),
  'training_epoch': ckpt.get('epoch', 'unknown'),
  'threshold_policy': ckpt.get('threshold_policy', 0.65),
  'val_precision_active': ckpt.get('val_precision_active', ckpt.get('precision_active', None)),
  'val_false_active_rate': ckpt.get('val_false_active_rate', ckpt.get('false_active_rate', None)),
}
json.dump(card, open('$OUT_DIR/model_card.json', 'w'), indent=2)
print(json.dumps(card, indent=2))
"

echo "=== Download complete. Models in $OUT_DIR/ ==="
