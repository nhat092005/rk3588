"""Run RKNN detection once over a video and save detections.npz + detections.json, run ON THE BOARD.

Same pre/post-processing (ai.board.common) and npz/json schema as scripts/demo/video/detect.py's
pt/onnx path, so predict.mp4 / track.mp4 render identically regardless of backend. Called by
scripts/demo/video/detect.py --backend rknn over ssh.
Usage (on the board): .venv-board/bin/python -m ai.board.detect_video --model <rknn_dir> --source <video>
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path, help="rknn_<precision>/ folder")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--det-conf", type=float, default=0.1)
    parser.add_argument("--core-mask", default="AUTO", choices=list(CORE_MASK))
    parser.add_argument("--out", required=True, type=Path)
    add_provenance_args(parser)
    args = parser.parse_args()

    names_by_id = yaml.safe_load((args.model / "metadata.yaml").read_text())["names"]
    names = [names_by_id[i] for i in range(len(names_by_id))]
    rknn, normalized = load_model(args.model, args.core_mask)

    cap = cv2.VideoCapture(str(args.source))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {args.source}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    idx_all, boxes_all, conf_all, cls_all = [], [], [], []
    frames = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        inp, meta = preprocess(frame)
        det = postprocess(rknn.inference(inputs=[inp])[0], meta, normalized, conf_thres=args.det_conf)
        if len(det):
            idx_all.append(np.full(len(det), frames, dtype=np.int32))
            boxes_all.append(det[:, :4])
            conf_all.append(det[:, 4])
            cls_all.append(det[:, 5])
        frames += 1
    cap.release()
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
        "frames": frames,
        "fps": fps,
        "width": width,
        "height": height,
    }
    args.out.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Done: {args.out} ({frames} frames, {len(idx)} detections)")


if __name__ == "__main__":
    main()
