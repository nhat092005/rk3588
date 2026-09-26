"""Shared helpers for the demo video/image toolkit (scripts/demo/video, scripts/demo/image).

Model resolution, PC (pt/onnx) detection sharing pre/post-processing with the board, npz/json
detections I/O, drawing, and an H.264 (libx264) video writer via PyAV since OpenCV cannot write a
browser-playable avc1 stream in this environment. Imported as `from common import ...` by scripts
that have already inserted the repo root onto sys.path.
"""
from __future__ import annotations

import datetime
import json
import subprocess
from fractions import Fraction
from pathlib import Path

import av
import cv2
import numpy as np
import torch
from ultralytics.utils.plotting import colors

from ai.board.common import preprocess, postprocess, IMGSZ, IOU
from ai.core.backends import UltralyticsBackend
from ai.core.provenance import REPO_ROOT, file_sha256, git_commit, git_dirty

RUNS_DIR = REPO_ROOT / "ai" / "automation" / "runs"
OUTPUTS_DIR = REPO_ROOT / "data" / "demo" / "outputs"
DET_CONF = 0.1
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".jfif"}


def sh(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def list_images(images_dir: str | Path) -> list[Path]:
    return sorted(p for p in Path(images_dir).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


def resolve_model(run_id: str, backend: str, precision: str | None) -> tuple[Path, str]:
    """run_id + backend + precision -> (model path, tag)."""
    weights = RUNS_DIR / run_id / "weights"
    if backend == "pt":
        return weights / "best.pt", "pt_fp32"
    if backend == "onnx":
        return weights / "best.onnx", "onnx_fp32"
    if not precision:
        raise ValueError("--backend rknn needs --precision")
    return weights / f"rknn_{precision}", f"rknn_{precision}"


def video_out_dir(source: str | Path, run_id: str, tag: str) -> Path:
    return OUTPUTS_DIR / "videos" / Path(source).stem / run_id / tag


def image_out_dir(run_id: str, tag: str) -> Path:
    return OUTPUTS_DIR / "images" / run_id / tag


def descriptor(path: str | Path) -> str | None:
    """<run_id>_<tag>_<kind> for a path at .../<run_id>/<tag>/<kind> under OUTPUTS_DIR, else None.

    `kind` is the file stem (predict/track, video case) or the directory name (predict, image case).
    """
    path = Path(path).resolve()
    if OUTPUTS_DIR.resolve() not in path.parents:
        return None
    kind = path.stem if path.suffix else path.name
    return f"{path.parent.parent.name}_{path.parent.name}_{kind}"


class PCDetector:
    """pt/onnx frame detector: ai.board.common preprocess -> UltralyticsBackend -> postprocess.

    Shares pre/post-processing with the board (ai/board/common.py) so all three backends produce
    detections through identical code; only the model differs.
    """

    def __init__(self, model_path: Path, backend: str, device: str, det_conf: float):
        self.backend = UltralyticsBackend(model_path, device="cpu" if backend == "onnx" else device)
        self.names = [self.backend.model.names[i] for i in range(len(self.backend.model.names))]
        self.det_conf = det_conf

    def __call__(self, bgr: np.ndarray) -> np.ndarray:
        inp, meta = preprocess(bgr)  # (1, 640, 640, 3) uint8 RGB
        img = torch.from_numpy(inp).permute(0, 3, 1, 2).contiguous()
        pred = self.backend(img).numpy()
        return postprocess(pred, meta, normalized=False, conf_thres=self.det_conf)


def base_provenance(run_id: str, tag: str, backend: str, model_path: Path, names: list[str], det_conf: float) -> dict:
    """Common detections.json fields for a PC (pt/onnx) detection run."""
    return {
        "run_id": run_id,
        "tag": tag,
        "backend": backend,
        "model_file": str(model_path.relative_to(REPO_ROOT)),
        "model_sha256": file_sha256(model_path),
        "names": names,
        "det_conf": det_conf,
        "iou": IOU,
        "imgsz": IMGSZ,
        "git_commit": git_commit(),
        "git_dirty": git_dirty(),
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def save_npz(path: Path, idx: np.ndarray, boxes: np.ndarray, conf: np.ndarray, cls: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, idx=idx.astype(np.int32), boxes=boxes.astype(np.float32),
              conf=conf.astype(np.float32), cls=cls.astype(np.int32))


def load_npz(path: Path) -> dict:
    with np.load(path) as d:
        return {k: d[k] for k in ("idx", "boxes", "conf", "cls")}


def save_json(path: Path, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2) + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def header(frame: np.ndarray, text: str) -> np.ndarray:
    """Draw a filled header bar with text in the top-left corner, in place."""
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(frame, (0, 0), (tw + 12, th + baseline + 12), (0, 0, 0), -1)
    cv2.putText(frame, text, (6, th + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    return frame


def draw(frame: np.ndarray, boxes: np.ndarray, cls: np.ndarray, labels: list[str]) -> np.ndarray:
    """Draw boxes with a filled label background, in place. One fixed color per class id."""
    for box, c, label in zip(boxes, cls, labels):
        x1, y1, x2, y2 = box.astype(int)
        color = colors(int(c), bgr=True)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - baseline - 4), (x1 + tw + 4, y1), color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - baseline - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1, cv2.LINE_AA)
    return frame


class VideoWriter:
    """H.264 (libx264) writer via PyAV. cv2.VideoWriter cannot produce avc1 output in this environment."""

    def __init__(self, path: Path, width: int, height: int, fps: float):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.container = av.open(str(path), mode="w")
        self.stream = self.container.add_stream("libx264", rate=Fraction(fps).limit_denominator(1001))
        self.stream.width = width
        self.stream.height = height
        self.stream.pix_fmt = "yuv420p"
        self.stream.options = {"crf": "20"}

    def write(self, frame_bgr: np.ndarray) -> None:
        self.container.mux(self.stream.encode(av.VideoFrame.from_ndarray(frame_bgr, format="bgr24")))

    def close(self) -> None:
        self.container.mux(self.stream.encode())
        self.container.close()
