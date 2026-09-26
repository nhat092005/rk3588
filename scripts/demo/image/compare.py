"""Side-by-side comparison of two rendered image directories (e.g. two predict/ outputs).

Usage: python scripts/demo/image/compare.py dirA dirB [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import OUTPUTS_DIR, descriptor, header  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dir_a", type=Path)
    parser.add_argument("dir_b", type=Path)
    parser.add_argument("--out-dir")
    args = parser.parse_args()

    desc_a, desc_b = descriptor(args.dir_a), descriptor(args.dir_b)
    if args.out_dir:
        out_dir = Path(args.out_dir)
    elif desc_a and desc_b:
        out_dir = OUTPUTS_DIR / "images" / "compare" / f"{desc_a}__vs__{desc_b}"
    else:
        parser.error("inputs are not inside data/demo/outputs/images/<run_id>/<tag>/predict/: pass --out-dir")

    names_a = {p.name for p in args.dir_a.iterdir() if p.is_file()}
    names_b = {p.name for p in args.dir_b.iterdir() if p.is_file()}
    common = sorted(names_a & names_b)
    if not common:
        raise ValueError(f"no file names in common between {args.dir_a} and {args.dir_b}")

    out_dir.mkdir(parents=True, exist_ok=True)
    for name in common:
        frame_a = cv2.imread(str(args.dir_a / name))
        frame_b = cv2.imread(str(args.dir_b / name))
        h = frame_a.shape[0]
        frame_b = cv2.resize(frame_b, (int(frame_b.shape[1] * h / frame_b.shape[0]), h))
        header(frame_a, desc_a or args.dir_a.name)
        header(frame_b, desc_b or args.dir_b.name)
        cv2.imwrite(str(out_dir / name), cv2.hconcat([frame_a, frame_b]))

    print(out_dir)


if __name__ == "__main__":
    main()
