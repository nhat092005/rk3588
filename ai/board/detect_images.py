"""Run RKNN detection once over a directory of images and save detections.npz + detections.json,
run ON THE BOARD. Same pre/post-processing (ai.board.common) and npz/json schema as
scripts/demo/image/detect.py's pt/onnx path. Called by scripts/demo/image/detect.py --backend rknn
over ssh.
Usage (on the board): .venv-board/bin/python -m ai.board.detect_images --model <rknn_dir> --source <dir>
       --out <npz path> --det-conf 0.1 --core-mask AUTO --run-id <id> --git-commit <sha> --git-dirty true|false
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import yaml

from ai.board.bench_npu import CORE_MASK, load_model
from ai.board.common import IMGSZ, IOU, add_provenance_args, postprocess, preprocess, provenance

# scripts/demo/common.py IMAGE_SUFFIXES, duplicated: ai.board.common.IMAGE_SUFFIXES lacks webp/jfif
# and is shared with the tier-2 benchmark image sets, which must not change.
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".jfif"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path, help="rknn_<precision>/ folder")
    parser.add_argument("--source", required=True, type=Path, help="image directory")
    parser.add_argument("--det-conf", type=float, default=0.1)
    parser.add_argument("--core-mask", default="AUTO", choices=list(CORE_MASK))
    parser.add_argument("--out", required=True, type=Path)
    add_provenance_args(parser)
    args = parser.parse_args()

    images = sorted(p for p in args.source.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    names_by_id = yaml.safe_load((args.model / "metadata.yaml").read_text())["names"]
    names = [names_by_id[i] for i in range(len(names_by_id))]
    rknn, normalized = load_model(args.model, args.core_mask)

    idx_all, boxes_all, conf_all, cls_all = [], [], [], []
    for i, path in enumerate(images):
        inp, meta = preprocess(cv2.imread(str(path)))
        det = postprocess(rknn.inference(inputs=[inp])[0], meta, normalized, conf_thres=args.det_conf)
        if len(det):
            idx_all.append(np.full(len(det), i, dtype=np.int32))
            boxes_all.append(det[:, :4])
            conf_all.append(det[:, 4])
            cls_all.append(det[:, 5])
    sdk_version = rknn.get_sdk_version()
    rknn.release()

    idx = np.concatenate(idx_all) if idx_all else np.zeros(0, dtype=np.int32)
    boxes = np.concatenate(boxes_all) if boxes_all else np.zeros((0, 4), dtype=np.float32)
    conf = np.concatenate(conf_all) if conf_all else np.zeros(0, dtype=np.float32)
    cls = np.concatenate(cls_all) if cls_all else np.zeros(0, dtype=np.int32)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.out, idx=idx, boxes=boxes.astype(np.float32), conf=conf.astype(np.float32),
              cls=cls.astype(np.int32))
    record = {
        **provenance(args, next(args.model.glob("*.rknn"))),
        "tag": args.model.name,
        "backend": "rknnlite-on-board",
        "names": names,
        "det_conf": args.det_conf,
        "iou": IOU,
        "imgsz": IMGSZ,
        "sdk_version": str(sdk_version),
        "source": str(args.source),
        "files": [p.name for p in images],
    }
    args.out.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Done: {args.out} ({len(images)} images, {len(idx)} detections)")


if __name__ == "__main__":
    main()
