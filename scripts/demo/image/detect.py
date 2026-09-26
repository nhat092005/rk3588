"""Run detection once over a directory of images and save detections.npz + detections.json
(pt/onnx on the PC, rknn on the board). Pipeline: detect once, then scripts/demo/image/predict.py
renders from the saved detections, so all backends share identical pre/post-processing.

Usage: python scripts/demo/image/detect.py --run <run_id> [--source data/demo/images]
       [--backend pt|onnx|rknn] [--precision fp16|int8] [--device 0] [--det-conf 0.1]
       [--out-dir DIR] [--board host] [--board-repo path] [--core-mask AUTO]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (  # noqa: E402
    DET_CONF, REPO_ROOT, PCDetector, base_provenance, git_commit, git_dirty, image_out_dir, list_images,
    resolve_model, save_json, save_npz, sh,
)


def detect_pc(images: list[Path], model_path: Path, backend: str, device: str, det_conf: float):
    detector = PCDetector(model_path, backend, device, det_conf)
    idx_all, boxes_all, conf_all, cls_all = [], [], [], []
    for i, path in enumerate(images):
        det = detector(cv2.imread(str(path)))
        if len(det):
            idx_all.append(np.full(len(det), i, dtype=np.int32))
            boxes_all.append(det[:, :4])
            conf_all.append(det[:, 4])
            cls_all.append(det[:, 5])
    idx = np.concatenate(idx_all) if idx_all else np.zeros(0, dtype=np.int32)
    boxes = np.concatenate(boxes_all) if boxes_all else np.zeros((0, 4), dtype=np.float32)
    conf = np.concatenate(conf_all) if conf_all else np.zeros(0, dtype=np.float32)
    cls = np.concatenate(cls_all) if cls_all else np.zeros(0, dtype=np.int32)
    return idx, boxes, conf, cls, detector.names


def detect_board(source: Path, model_dir: Path, out_dir: Path, args: argparse.Namespace) -> None:
    """Mirror ai.automation.evaluate.board_dump: rsync images + model, run ai.board.detect_images, scp back."""
    rel_source = source.resolve().relative_to(REPO_ROOT)
    rel_model = model_dir.relative_to(REPO_ROOT)
    rel_out = Path(os.path.relpath(out_dir, REPO_ROOT))
    remote_npz = f"{rel_out}/detections.npz"
    sh(["ssh", args.board, f"mkdir -p {args.board_repo}/{rel_source} "
        f"{args.board_repo}/{rel_model.parent} {args.board_repo}/{rel_out}"])
    sh(["rsync", "-aL", f"{source}/", f"{args.board}:{args.board_repo}/{rel_source}/"])
    sh(["rsync", "-a", f"{model_dir}/", f"{args.board}:{args.board_repo}/{rel_model}/"])
    sh(["ssh", args.board, f"cd {args.board_repo} && .venv-board/bin/python -m ai.board.detect_images "
        f"--model {rel_model} --source {rel_source} --out {remote_npz} --det-conf {args.det_conf} "
        f"--core-mask {args.core_mask} --run-id {args.run} --git-commit {git_commit()} "
        f"--git-dirty {str(git_dirty()).lower()}"])
    sh(["scp", "-q", f"{args.board}:{args.board_repo}/{remote_npz}",
        f"{args.board}:{args.board_repo}/{remote_npz[:-4]}.json", str(out_dir)])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="run_id under ai/automation/runs/")
    parser.add_argument("--source", default="data/demo/images", help="image directory")
    parser.add_argument("--backend", choices=["pt", "onnx", "rknn"], default="pt")
    parser.add_argument("--precision", choices=["fp16", "int8"], help="rknn only")
    parser.add_argument("--device", default="0", help="pt only: CUDA index or cpu")
    parser.add_argument("--det-conf", type=float, default=DET_CONF)
    parser.add_argument("--out-dir")
    parser.add_argument("--board", default="minhnhat@100.67.251.37", help="rknn only: ssh target")
    parser.add_argument("--board-repo", default="rk3588", help="rknn only: repo path on the board")
    parser.add_argument("--core-mask", default="AUTO", help="rknn only")
    args = parser.parse_args()

    if args.backend == "rknn" and not args.precision:
        parser.error("--backend rknn needs --precision")
    model_path, tag = resolve_model(args.run, args.backend, args.precision)
    source = Path(args.source)
    out_dir = Path(args.out_dir) if args.out_dir else image_out_dir(args.run, tag)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.backend == "rknn":
        detect_board(source, model_path, out_dir, args)
    else:
        images = list_images(source)
        idx, boxes, conf, cls, names = detect_pc(images, model_path, args.backend, args.device, args.det_conf)
        save_npz(out_dir / "detections.npz", idx, boxes, conf, cls)
        backend_name = "pytorch" if args.backend == "pt" else "onnxruntime-cpu-pc"
        meta = base_provenance(args.run, tag, backend_name, model_path, names, args.det_conf)
        meta.update(source=str(source.resolve().relative_to(REPO_ROOT)), files=[p.name for p in images])
        save_json(out_dir / "detections.json", meta)

    print(out_dir)


if __name__ == "__main__":
    main()
