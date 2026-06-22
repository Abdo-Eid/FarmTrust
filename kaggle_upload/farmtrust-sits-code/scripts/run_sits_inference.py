"""Run FarmTrust SITS-BERT advisory inference for one AOI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from farmtrust_core.ml.inference import run_inference


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ML advisory inference for one AOI.")
    parser.add_argument("--aoi-id", required=True)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--model-dir", default="models")
    args = parser.parse_args()

    model_path = Path(args.model_dir) / "sits_bert_finetuned.pt"
    if not model_path.exists():
        raise FileNotFoundError(f"Missing required model: {model_path}")

    artifact = run_inference(aoi_id=args.aoi_id, data_root=args.data_root, model_dir=args.model_dir)
    output_path = Path(args.data_root) / "ml" / args.aoi_id / "sits_prediction.json"
    summary = artifact.get("ml_summary", {})
    print(f"ml_land_status={artifact.get('ml_land_status')}")
    print(f"ml_assessment_confidence={artifact.get('ml_assessment_confidence')}")
    print(f"ml_activity_window_count={summary.get('ml_activity_window_count', 0)}")
    print(f"output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
