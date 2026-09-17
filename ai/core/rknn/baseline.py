"""Tier 1: quick, correct .rknn artifact via ultralytics' native RKNN export.

Does not expose core_mask / op_target / hybrid quantization - see
rknn/deploy.py for the Tier 2 pipeline that does, and
tmp/2026-09-17_baseline_rk3588_npu_optimization.md section 9.4 for why both
tiers exist. Only use this module for a first sanity-check artifact/number,
not for the thesis' actual NPU optimization comparisons.

Not runnable yet in this repo's current .venv: requires rknn-toolkit2,
torch<=2.4.0, numpy<=1.26.4 (see
tmp/2026-09-17_baseline_rk3588_npu_optimization.md section 9.1). Written and
ready to call once the shared .venv is updated after the current training
runs finish.
"""
from __future__ import annotations

from dataclasses import dataclass

from ultralytics import YOLO

from ai.core.dataset import dataset_yaml_path


@dataclass
class ExportConfig:
    weights: str  # path to a trained .pt checkpoint
    dataset: str  # dataset name, e.g. "sfchd"
    platform: str = "rk3588"
    imgsz: int = 640
    quantize: int = 8  # 8 = INT8, 16 = FP16 (no quantization)
    calib_split: str = "train"


def export_baseline(cfg: ExportConfig) -> str:
    """Export cfg.weights to RKNN via ultralytics' native format="rknn" path."""
    model = YOLO(cfg.weights)
    data_yaml = dataset_yaml_path(cfg.dataset)
    return model.export(
        format="rknn",
        name=cfg.platform,
        quantize=cfg.quantize,
        data=str(data_yaml),
        split=cfg.calib_split,
        imgsz=cfg.imgsz,
    )
