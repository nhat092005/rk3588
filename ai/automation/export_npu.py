"""CLI to export a trained run to RKNN FP16 or INT8, plus the plain FP32 ONNX.

Writes runs/<run_id>/weights/rknn_<precision>/ (.rknn + metadata, git-ignored) and best.onnx
(board CPU baseline, Table H), plus tracked runs/<run_id>/export_<precision>.json.
"""
import argparse
import json
import os
import shutil
from importlib.metadata import version
from pathlib import Path

import yaml

from ai.core.dataset import dataset_yaml_path
from ai.core.provenance import file_sha256, provenance
from ai.core.rknn.baseline import ExportConfig, export_onnx, export_rknn
from ai.core.rknn.calibration import sample_calibration_images, write_letterboxed_calib

RUNS_DIR = Path(__file__).resolve().parent / "runs"

# Calibration set (protocol v1): 300 train images, >=20/class, seed 42.
# 300 avoids Ultralytics' ">300 images recommended" INT8 warning (exporter.py get_int8_calibration_dataloader).
CALIB_N = 300
CALIB_MIN_PER_CLASS = 20
CALIB_SEED = 42


def build_calibration(dataset: str, out_dir: Path) -> dict:
    data = yaml.safe_load(dataset_yaml_path(dataset).read_text())
    images_dir = Path(data["path"]) / data["train"]
    labels_dir = Path(str(images_dir).replace(f"{os.sep}images{os.sep}", f"{os.sep}labels{os.sep}"))
    stems = sorted(sample_calibration_images(labels_dir, n=CALIB_N, min_per_class=CALIB_MIN_PER_CLASS, seed=CALIB_SEED))
    by_stem = {p.stem: p for p in images_dir.iterdir()}
    shutil.rmtree(out_dir, ignore_errors=True)  # no leftovers from a previous export
    write_letterboxed_calib([by_stem[s] for s in stems], out_dir)
    return {"source": f"{dataset}/train", "n": len(stems), "min_per_class": CALIB_MIN_PER_CLASS,
            "seed": CALIB_SEED, "preprocess": "LetterBox 640 (same as evaluator), PNG", "images": stems}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", help="an existing directory under ai/automation/runs/")
    parser.add_argument("--quantize", type=int, choices=[8, 16], default=8, help="8 = INT8 (w8a8), 16 = FP16")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    weights_dir = run_dir / "weights"
    train_cfg = yaml.safe_load((run_dir / "config.yaml").read_text())
    precision = "int8" if args.quantize == 8 else "fp16"
    out_dir = weights_dir / f"rknn_{precision}"

    calib = None
    calib_dir = None
    if args.quantize == 8:
        calib_dir = weights_dir / "calib_int8"
        calib = build_calibration(train_cfg["dataset"], calib_dir)

    export_rknn(
        ExportConfig(weights=str(weights_dir / "best.pt"), quantize=args.quantize,
                     calib_images_dir=str(calib_dir / "images") if calib_dir else None),
        out_dir,
    )
    onnx_path = export_onnx(str(weights_dir / "best.pt"))
    rknn_path = next(out_dir.glob("*.rknn"))

    record = {
        "run_id": args.run_id,
        "precision": precision,
        "export_tier": "baseline_native_api",
        "rknn_path": str(rknn_path.relative_to(run_dir)),
        "rknn_size_mb": round(rknn_path.stat().st_size / 2**20, 3),
        "rknn_sha256": file_sha256(rknn_path),
        "onnx_path": str(onnx_path.relative_to(run_dir)),
        "onnx_size_mb": round(onnx_path.stat().st_size / 2**20, 3),
        "onnx_sha256": file_sha256(onnx_path),
        **provenance(),
        "ultralytics_version": version("ultralytics"),
        "rknn_toolkit2_version": version("rknn-toolkit2"),
        "calibration": calib,
    }
    out_path = run_dir / f"export_{precision}.json"
    out_path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Done: {out_path}")


if __name__ == "__main__":
    main()
