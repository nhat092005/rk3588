"""automation/'s NPU export CLI: read a finished training run_id -> call
core/rknn/baseline.py's Tier 1 export -> record npu_benchmark.json.

Run from repo root: python -m ai.automation.export_npu <run_id>

This only runs the Tier 1 baseline export (ultralytics' native RKNN export,
see core/rknn/baseline.py). The Tier 2 manual optimization pipeline
(core_mask / op_target / hybrid quantization) lives in core/rknn/deploy.py,
called from npu/experiments/, not here - see
tmp/2026-09-17_baseline_rk3588_npu_optimization.md section 9.4/9.5.

NOT RUNNABLE YET in this repo's current .venv (needs rknn-toolkit2 +
torch<=2.4.0 + numpy<=1.26.4, see core/rknn/baseline.py's export_baseline()
docstring). Written and ready to run once the shared .venv is updated.
"""
import argparse
import datetime
import json
import subprocess
from pathlib import Path

import yaml

from ai.core.rknn.baseline import ExportConfig, export_baseline

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = Path(__file__).resolve().parent / "runs"


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", help="an existing directory under ai/automation/runs/")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    train_cfg = yaml.safe_load((run_dir / "config.yaml").read_text())
    weights = run_dir / "weights" / "best.pt"

    export_cfg = ExportConfig(weights=str(weights), dataset=train_cfg["dataset"])
    rknn_model_dir = export_baseline(export_cfg)

    benchmark = {
        "run_id": args.run_id,
        "export_tier": "baseline_native_api",
        "rknn_model_dir": rknn_model_dir,
        "exported_at": datetime.datetime.now().isoformat(),
        "git_commit": git_commit(),
        # mAP-drop and latency need model.val() on the .rknn model, which
        # ultralytics only allows running on an actual Rockchip device
        # (RKNNBackend.load_model() raises OSError otherwise - see
        # tmp/2026-09-17_baseline_rk3588_npu_optimization.md section 9.4).
        # Pending board bring-up.
        "map50_95_fp32": None,
        "map50_95_int8": None,
        "latency_ms": None,
        "fps": None,
        "status": "exported, awaiting board bring-up for mAP/latency numbers",
    }
    out_path = run_dir / "npu_benchmark.json"
    out_path.write_text(json.dumps(benchmark, indent=2) + "\n")
    print(f"Done: {out_path}")


if __name__ == "__main__":
    main()
