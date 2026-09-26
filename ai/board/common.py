"""Shared tier-2 helpers that run ON THE BOARD (Guide section 5.3, 5.4).

Only numpy, opencv, psutil and pyyaml: no torch/ultralytics on the board.
Pre-processing reproduces the evaluator input (Ultralytics val LetterBox) and
post-processing reproduces Ultralytics predict NMS, in numpy.
"""
from __future__ import annotations

import math
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import psutil

PROTOCOL_VERSION = "v1"  # must equal ai/core/evaluator.py PROTOCOL_VERSION (checked by make tables)
IMGSZ = 640
# Deployment defaults = Ultralytics predict (cfg/default.yaml: conf 0.25, iou 0.7, max_det 300,
# multi_label=False, max_nms 30000, max_wh 7680); AI Quality instead uses val settings (conf 0.001) on PC.
CONF = 0.25
IOU = 0.7
MAX_DET = 300
MAX_NMS = 30000
MAX_WH = 7680
WARMUP = 20
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


def add_provenance_args(parser) -> None:
    """The board has no git checkout of the current code; the Makefile passes the PC's state."""
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--git-dirty", required=True, choices=["true", "false"])


def provenance(args, model_path: Path) -> dict:
    import datetime
    import hashlib

    h = hashlib.sha256()
    with open(model_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return {
        "git_commit": args.git_commit,
        "git_dirty": args.git_dirty == "true",
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "run_id": args.run_id,
        "tier": 2,
        "protocol_version": PROTOCOL_VERSION,
        "model_file": str(model_path),
        "model_sha256": h.hexdigest(),
    }


def list_images(images_dir: str) -> list[Path]:
    return sorted(p for p in Path(images_dir).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


def preprocess(bgr: np.ndarray) -> tuple[np.ndarray, tuple]:
    """BGR image -> (1, 640, 640, 3) uint8 RGB, same pixels as the evaluator input."""
    h0, w0 = bgr.shape[:2]
    r = IMGSZ / max(h0, w0)
    img = bgr
    if r != 1:  # BaseDataset.load_image(rect_mode=True)
        img = cv2.resize(bgr, (min(math.ceil(w0 * r), IMGSZ), min(math.ceil(h0 * r), IMGSZ)), interpolation=cv2.INTER_LINEAR)
    h, w = img.shape[:2]
    # LetterBox(scaleup=False, center=True): r2 <= 1 and new_unpad == (w, h) after the resize above
    dw, dh = (IMGSZ - w) / 2, (IMGSZ - h) / 2
    top, bottom = round(dh - 0.1), round(dh + 0.1)
    left, right = round(dw - 0.1), round(dw + 0.1)
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    gain = min(h / h0, w / w0)
    return img[None], (gain, left, top, w0, h0)


def nms_xyxy(boxes: np.ndarray, scores: np.ndarray, iou_thres: float) -> np.ndarray:
    order = scores.argsort()[::-1]
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-7)
        order = order[1:][iou <= iou_thres]
    return np.array(keep, dtype=int)


def postprocess(pred: np.ndarray, meta: tuple, normalized: bool, conf_thres: float = CONF) -> np.ndarray:
    """Raw (1, 4 + nc, anchors) -> (N, 6) [x1, y1, x2, y2, conf, cls] in original image pixels."""
    x = pred[0].T.astype(np.float32)  # (anchors, 4 + nc)
    if normalized:  # Ultralytics INT8 RKNN exports divide boxes by the input size
        x[:, :4] *= IMGSZ
    scores = x[:, 4:]
    cls = scores.argmax(1)
    conf = scores[np.arange(len(cls)), cls]
    keep = conf > conf_thres
    x, conf, cls = x[keep], conf[keep], cls[keep]
    if len(x) > MAX_NMS:
        top = conf.argsort()[::-1][:MAX_NMS]
        x, conf, cls = x[top], conf[top], cls[top]
    boxes = np.empty((len(x), 4), dtype=np.float32)
    boxes[:, 0] = x[:, 0] - x[:, 2] / 2
    boxes[:, 1] = x[:, 1] - x[:, 3] / 2
    boxes[:, 2] = x[:, 0] + x[:, 2] / 2
    boxes[:, 3] = x[:, 1] + x[:, 3] / 2
    idx = nms_xyxy(boxes + cls[:, None] * MAX_WH, conf, IOU)[:MAX_DET]
    boxes, conf, cls = boxes[idx], conf[idx], cls[idx]

    gain, padw, padh, w0, h0 = meta  # scale back to the original image (ops.scale_boxes)
    boxes[:, [0, 2]] = ((boxes[:, [0, 2]] - padw) / gain).clip(0, w0)
    boxes[:, [1, 3]] = ((boxes[:, [1, 3]] - padh) / gain).clip(0, h0)
    return np.concatenate([boxes, conf[:, None], cls[:, None].astype(np.float32)], axis=1)


def summarize(values_ms: list[float]) -> dict:
    a = np.asarray(values_ms)
    return {
        "mean": round(float(a.mean()), 3),
        "p50": round(float(np.percentile(a, 50)), 3),
        "p95": round(float(np.percentile(a, 95)), 3),
        "std": round(float(a.std()), 3),
        "n": int(a.size),
    }


def read_text(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def thermal_zone(name: str = "npu-thermal") -> Path | None:
    for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
        if read_text(str(zone / "type")) == name:
            return zone
    return None


def temperature_c(zone: Path | None) -> float | None:
    raw = read_text(str(zone / "temp")) if zone else None
    return round(int(raw) / 1000, 1) if raw else None


def frequency_state() -> dict:
    """Governor and current frequency of CPU clusters, NPU and DDR (RKNPU2 User Guide p.72-73)."""
    state = {}
    for policy in sorted(Path("/sys/devices/system/cpu/cpufreq").glob("policy*")):
        state[policy.name] = {
            "governor": read_text(str(policy / "scaling_governor")),
            "cur_khz": read_text(str(policy / "scaling_cur_freq")),
        }
    for name, node in (("npu", "fdab0000.npu"), ("ddr", "dmc")):
        base = Path("/sys/class/devfreq") / node
        state[name] = {"governor": read_text(str(base / "governor")), "cur_hz": read_text(str(base / "cur_freq"))}
    state["locked"] = all(v["governor"] in ("performance", "userspace") for v in state.values())
    return state


def system_info() -> dict:
    import platform

    os_release = dict(
        line.split("=", 1) for line in (read_text("/etc/os-release") or "").splitlines() if "=" in line
    )
    return {
        "kernel": platform.release(),
        "os": os_release.get("PRETTY_NAME", "").strip('"'),
        "python": platform.python_version(),
        "ram_total_mib": round(psutil.virtual_memory().total / 2**20),
        "cpu_count": psutil.cpu_count(),
    }


class ResourceMonitor:
    """Samples this process' VmRSS and CPU %, system CPU % and NPU temperature every `interval` s."""

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self.proc = psutil.Process()
        self.zone = thermal_zone()
        self.rss_mib, self.proc_cpu, self.sys_cpu, self.temps = [], [], [], []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        self.proc.cpu_percent(None)
        psutil.cpu_percent(None)
        while not self._stop.wait(self.interval):
            self.rss_mib.append(self.proc.memory_info().rss / 2**20)  # = VmRSS in /proc/self/status
            self.proc_cpu.append(self.proc.cpu_percent(None))  # 100 = one full core
            self.sys_cpu.append(psutil.cpu_percent(None))  # 100 = all cores
            self.temps.append(temperature_c(self.zone))

    def __enter__(self):
        self.temp_start = temperature_c(self.zone)
        self.t0 = time.perf_counter()
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
        self.duration_s = time.perf_counter() - self.t0
        self.temp_end = temperature_c(self.zone)

    def result(self) -> dict:
        temps = [t for t in self.temps if t is not None]
        return {
            "peak_rss_mib": round(max(self.rss_mib), 1) if self.rss_mib else None,
            "avg_process_cpu_pct": round(float(np.mean(self.proc_cpu)), 1) if self.proc_cpu else None,
            "avg_system_cpu_pct": round(float(np.mean(self.sys_cpu)), 1) if self.sys_cpu else None,
            "thermal_zone": self.zone.name if self.zone else None,
            "temp_start_c": self.temp_start,
            "temp_end_c": self.temp_end,
            "temp_max_c": max(temps) if temps else None,
            "duration_s": round(self.duration_s, 1),
            "samples": len(self.rss_mib),
        }
