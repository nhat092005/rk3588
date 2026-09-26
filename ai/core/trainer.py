"""Central model training and evaluation interface using Ultralytics YOLO."""
from dataclasses import dataclass

from ultralytics import YOLO

from .dataset import dataset_yaml_path


@dataclass
class TrainConfig:
    model: str  # Model checkpoint name (e.g. "yolov8n.pt") or architecture YAML path
    dataset: str  # Dataset identifier, e.g. "sfchd"
    epochs: int
    imgsz: int = 640
    batch: int = 16
    seed: int = 42
    device: str = "0"  # Target device, e.g. "0" for GPU, "cpu" for CPU
    optimizer: str = "auto"  # Set explicitly in configs so the choice does not depend on Ultralytics' auto logic
    lr0: float = 0.01
    momentum: float = 0.937
    warmup_bias_lr: float = 0.1  # optimizer=auto silently sets this to 0.0, so configs pin it too
    project: str | None = None  # Output directory for run artifacts
    run_name: str = "train"


def train(cfg: TrainConfig) -> YOLO:
    data_yaml = dataset_yaml_path(cfg.dataset)
    model = YOLO(cfg.model)
    model.train(
        data=str(data_yaml),
        epochs=cfg.epochs,
        imgsz=cfg.imgsz,
        batch=cfg.batch,
        seed=cfg.seed,
        device=cfg.device,
        optimizer=cfg.optimizer,
        lr0=cfg.lr0,
        momentum=cfg.momentum,
        warmup_bias_lr=cfg.warmup_bias_lr,
        project=cfg.project,
        name=cfg.run_name,
        exist_ok=True,
    )
    return model


def evaluate(
    model: YOLO,
    dataset: str,
    split: str = "test",
    project: str | None = None,
    run_name: str = "test_eval",
):
    data_yaml = dataset_yaml_path(dataset)
    return model.val(
        data=str(data_yaml),
        split=split,
        project=project,
        name=run_name,
        exist_ok=True,
    )
