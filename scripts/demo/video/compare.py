"""Side-by-side H.264 comparison of two rendered videos (e.g. predict.mp4 vs track.mp4).

Usage: python scripts/demo/video/compare.py a.mp4 b.mp4 [--scale 0.5] [--out out.mp4]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import VideoWriter, descriptor, header  # noqa: E402


def new_size(cap: cv2.VideoCapture, scale: float) -> tuple[int, int]:
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * scale) // 2 * 2
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) * scale) // 2 * 2
    return w, h


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument("--scale", type=float, default=0.5)
    parser.add_argument("--out")
    args = parser.parse_args()

    desc_a, desc_b = descriptor(args.a), descriptor(args.b)
    if args.out:
        out_path = Path(args.out)
    elif desc_a and desc_b:
        out_path = args.a.resolve().parent.parent.parent / "compare" / f"{desc_a}__vs__{desc_b}.mp4"
    else:
        parser.error("inputs are not inside data/demo/outputs/videos/<stem>/<run_id>/<tag>/: pass --out")

    cap_a, cap_b = cv2.VideoCapture(str(args.a)), cv2.VideoCapture(str(args.b))
    if not cap_a.isOpened() or not cap_b.isOpened():
        raise RuntimeError("cannot open one of the input videos")
    n_a, n_b = int(cap_a.get(cv2.CAP_PROP_FRAME_COUNT)), int(cap_b.get(cv2.CAP_PROP_FRAME_COUNT))
    if n_a != n_b:
        raise ValueError(f"frame count mismatch: {args.a} has {n_a}, {args.b} has {n_b}")
    fps = cap_a.get(cv2.CAP_PROP_FPS)

    (wa, ha), (wb, hb) = new_size(cap_a, args.scale), new_size(cap_b, args.scale)
    wb, hb = round(wb * ha / hb) // 2 * 2, ha  # match B's height to A's for hconcat
    writer = VideoWriter(out_path, wa + wb, ha, fps)

    i = 0
    while True:
        ok_a, frame_a = cap_a.read()
        ok_b, frame_b = cap_b.read()
        if not ok_a or not ok_b:
            break
        frame_a = cv2.resize(frame_a, (wa, ha))
        frame_b = cv2.resize(frame_b, (wb, hb))
        header(frame_a, desc_a or args.a.stem)
        header(frame_b, desc_b or args.b.stem)
        writer.write(cv2.hconcat([frame_a, frame_b]))
        i += 1
    cap_a.release()
    cap_b.release()
    writer.close()
    if i != n_a:
        raise ValueError(f"decoded {i} frames, expected {n_a}")
    print(out_path)


if __name__ == "__main__":
    main()
