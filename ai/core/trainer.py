"""Single source of truth for training/eval.

research/ and automation/ must both call into this module instead of writing
their own training loop, so a result from quick research testing and a result
from a formal automation run are always produced the same way.
"""
from dataclasses import dataclass

from ultralytics import YOLO

from .dataset import dataset_yaml_path


@dataclass
class TrainConfig:
    model: str                  # ultralytics checkpoint name (e.g. "yolov8n.pt") or path to an architecture .yaml
    dataset: str                 # dataset name, e.g. "css"
    epochs: int
    imgsz: int = 640
    batch: int = 16
    seed: int = 42
    device: str = "0"            # "0" = first GPU, "cpu" = CPU
    project: str | None = None   # directory ultralytics writes its raw run output into
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
