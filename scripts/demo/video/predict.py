"""Render detections.npz as predict.mp4: boxes with confidence >= --conf, no tracking.

Usage: python scripts/demo/video/predict.py --detections <npz> [--conf 0.25] [--out out.mp4]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import REPO_ROOT, VideoWriter, draw, header, load_json, load_npz  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detections", required=True, type=Path)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--out")
    args = parser.parse_args()

    meta = load_json(args.detections.with_suffix(".json"))
    det = load_npz(args.detections)
    names = meta["names"]
    n_frames = meta["frames"]

    source = REPO_ROOT / meta["source"]
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {source}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path = Path(args.out) if args.out else args.detections.parent / "predict.mp4"
    writer = VideoWriter(out_path, width, height, fps)

    keep = det["conf"] >= args.conf
    idx, boxes, conf, cls = det["idx"][keep], det["boxes"][keep], det["conf"][keep], det["cls"][keep]

    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        m = idx == i
        labels = [f"{names[c]} {p:.2f}" for c, p in zip(cls[m], conf[m])]
        draw(frame, boxes[m], cls[m], labels)
        header(frame, f"{meta['run_id']} | {meta['tag']} | predict | frame {i + 1}/{n_frames}")
        writer.write(frame)
        i += 1
    cap.release()
    writer.close()
    if i != n_frames:
        raise ValueError(f"{source}: decoded {i} frames, detections.json says {n_frames}")
    print(out_path)


if __name__ == "__main__":
    main()
