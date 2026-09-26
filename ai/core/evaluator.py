"""Evaluation Protocol v1 (Guide section 5): one evaluator for every model and precision.

Dataset loading, LetterBox, NMS and AP come from the same Ultralytics code that
model.val() uses, so FP32 (PyTorch/ONNX) and NPU (RKNN FP16/INT8) results differ
only by the backend. Changing any constant below requires a new PROTOCOL_VERSION.
"""
from __future__ import annotations

import hashlib
from importlib.metadata import version
from pathlib import Path
from typing import Callable

import numpy as np
import torch
import yaml
from ultralytics.cfg import get_cfg
from ultralytics.data import build_dataloader, build_yolo_dataset
from ultralytics.utils import DEFAULT_CFG, nms
from ultralytics.utils.metrics import DetMetrics, box_iou
from ultralytics.utils.ops import xywh2xyxy

from .dataset import dataset_yaml_path
from .provenance import git_commit, git_dirty

PROTOCOL_VERSION = "v1"
IMGSZ = 640
CONF = 0.001
IOU = 0.7
MAX_DET = 300
IOU_THRESHOLDS = torch.linspace(0.5, 0.95, 10)

# eval set name -> (prepared dataset, split key in its dataset.yaml)
EVAL_SETS = {
    "sfchd_test": ("sfchd_5class", "test"),  # common test set for every model (1,238 images)
    "shel5k_test": ("sfchd_shel5k", "test_shel5k"),  # extra test set for Option 2 models (500 images)
}
# Eval sets reported for a model trained on each dataset (Guide section 7, general rules)
EVAL_SETS_BY_DATASET = {
    "sfchd_5class": ["sfchd_test"],
    "sfchd_shel5k": ["sfchd_test", "shel5k_test"],
}

# A backend maps a uint8 RGB NCHW batch (1, 3, IMGSZ, IMGSZ) and its image path to raw predictions
# (1, 4 + nc, anchors) with xywh boxes in input pixels.
Backend = Callable[..., torch.Tensor]  # backend(img, im_file=...)


def build_eval_loader(eval_set: str):
    dataset_name, split = EVAL_SETS[eval_set]
    data_yaml = dataset_yaml_path(dataset_name)
    data = yaml.safe_load(data_yaml.read_text())
    if split not in data:
        raise KeyError(f"{data_yaml} has no '{split}' key; re-run scripts/data/prepare_{dataset_name}.py")
    img_path = str(Path(data["path"]) / data[split])
    data["names"] = dict(enumerate(data["names"]))
    data["channels"] = 3

    cfg = get_cfg(DEFAULT_CFG, {"imgsz": IMGSZ, "rect": False, "task": "detect", "mode": "val"})
    dataset = build_yolo_dataset(cfg, img_path, 1, data, mode="val", stride=32)
    loader = build_dataloader(dataset, batch=1, workers=4, shuffle=False)
    return loader, data["names"]


def dataset_fingerprint(im_files: list[str], label_files: list[str]) -> str:
    """sha256 over image bytes and label text, in file-name order.

    data/** is git-ignored, so this proves which data a number was measured on.
    """
    h = hashlib.sha256()
    for im, lb in sorted(zip(im_files, label_files)):
        h.update(Path(im).name.encode())
        h.update(Path(im).read_bytes())
        h.update(Path(lb).read_bytes() if Path(lb).exists() else b"")
    return h.hexdigest()


def match_predictions(pred_cls: torch.Tensor, true_cls: torch.Tensor, iou: torch.Tensor) -> np.ndarray:
    """Greedy matching, same as BaseValidator.match_predictions (use_scipy=False)."""
    correct = np.zeros((pred_cls.shape[0], IOU_THRESHOLDS.numel()), dtype=bool)
    iou = (iou * (true_cls[:, None] == pred_cls)).cpu().numpy()
    for i, threshold in enumerate(IOU_THRESHOLDS.tolist()):
        matches = np.array(np.nonzero(iou >= threshold)).T
        if matches.shape[0]:
            if matches.shape[0] > 1:
                matches = matches[iou[matches[:, 0], matches[:, 1]].argsort()[::-1]]
                matches = matches[np.unique(matches[:, 1], return_index=True)[1]]
                matches = matches[np.unique(matches[:, 0], return_index=True)[1]]
            correct[matches[:, 1].astype(int), i] = True
    return correct


def evaluate(backend: Backend, eval_set: str, limit: int | None = None) -> dict:
    """Run protocol v1 on an eval set and return a JSON-serializable result."""
    loader, names = build_eval_loader(eval_set)
    metrics = DetMetrics(names=names)
    im_files, label_files = [], []

    for n, batch in enumerate(loader):
        if limit is not None and n >= limit:
            break
        img = batch["img"]
        preds = backend(img, im_file=batch["im_file"][0])
        det = nms.non_max_suppression(
            preds, CONF, IOU, nc=0, multi_label=True, agnostic=False, max_det=MAX_DET
        )[0].cpu()

        cls = batch["cls"].squeeze(-1)
        gt = xywh2xyxy(batch["bboxes"]) * torch.tensor(img.shape[2:])[[1, 0, 1, 0]]
        pred_cls = det[:, 5]
        if cls.shape[0] and det.shape[0]:
            tp = match_predictions(pred_cls, cls, box_iou(gt, det[:, :4]))
        else:
            tp = np.zeros((det.shape[0], IOU_THRESHOLDS.numel()), dtype=bool)
        metrics.update_stats(
            {
                "tp": tp,
                "conf": det[:, 4].numpy(),
                "pred_cls": pred_cls.numpy(),
                "target_cls": cls.numpy(),
                "target_img": np.unique(cls.numpy()),
                "im_name": Path(batch["im_file"][0]).name,
            }
        )
        im_files.append(batch["im_file"][0])
        label_files.append(loader.dataset.label_files[n])  # shuffle=False, batch=1: batch n is item n

    metrics.process()
    box = metrics.box
    mp, mr, map50, map50_95 = box.mean_results()
    per_class = {}
    for i, c in enumerate(box.ap_class_index):
        p, r, ap50, ap = box.class_result(i)
        per_class[names[int(c)]] = {
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "ap50": round(float(ap50), 4),
            "ap50_95": round(float(ap), 4),
            "instances": int(metrics.nt_per_class[int(c)]),
        }

    return {
        "protocol_version": PROTOCOL_VERSION,
        "protocol": {
            "input": f"LetterBox {IMGSZ}x{IMGSZ}, rect=False, scaleup=False, center, pad 114",
            "conf": CONF,
            "iou": IOU,
            "max_det": MAX_DET,
            "multi_label": True,
        },
        "git_commit": git_commit(),
        "git_dirty": git_dirty(),
        "ultralytics_version": version("ultralytics"),
        "torch_version": version("torch"),
        "eval_set": eval_set,
        "dataset": EVAL_SETS[eval_set][0],
        "split": EVAL_SETS[eval_set][1],
        "n_images": len(im_files),
        "classes": list(names.values()),
        "dataset_fingerprint": dataset_fingerprint(im_files, label_files),
        "precision": round(float(mp), 4),
        "recall": round(float(mr), 4),
        "map50": round(float(map50), 4),
        "map50_95": round(float(map50_95), 4),
        "per_class": per_class,
    }
