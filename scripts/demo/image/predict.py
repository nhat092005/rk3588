"""Render detections.npz as predict/<name>.jpg for every source image (boxes with confidence >= --conf).

Usage: python scripts/demo/image/predict.py --detections <npz> [--conf 0.25] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import REPO_ROOT, draw, load_json, load_npz  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detections", required=True, type=Path)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--out-dir")
    args = parser.parse_args()

    meta = load_json(args.detections.with_suffix(".json"))
    det = load_npz(args.detections)
    names = meta["names"]
    source = REPO_ROOT / meta["source"]

    out_dir = Path(args.out_dir) if args.out_dir else args.detections.parent / "predict"
    out_dir.mkdir(parents=True, exist_ok=True)

    keep = det["conf"] >= args.conf
    idx, boxes, conf, cls = det["idx"][keep], det["boxes"][keep], det["conf"][keep], det["cls"][keep]

    for i, name in enumerate(meta["files"]):
        frame = cv2.imread(str(source / name))
        if frame is None:
            raise RuntimeError(f"cannot read {source / name}")
        m = idx == i
        labels = [f"{names[c]} {p:.2f}" for c, p in zip(cls[m], conf[m])]
        draw(frame, boxes[m], cls[m], labels)
        cv2.imwrite(str(out_dir / f"{Path(name).stem}.jpg"), frame)

    print(out_dir)


if __name__ == "__main__":
    main()
