"""Baseline RKNN export using Ultralytics native RKNN backend."""
from __future__ import annotations

from dataclasses import dataclass

from ultralytics import YOLO

from ai.core.dataset import dataset_yaml_path


@dataclass
class ExportConfig:
    weights: str
    dataset: str
    platform: str = "rk3588"
    imgsz: int = 640
    quantize: int = 8  # 8 for INT8 quantization, 16 for FP16
    calib_split: str = "train"


def export_baseline(cfg: ExportConfig) -> str:
    """Export model weights to RKNN using Ultralytics native backend."""
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
