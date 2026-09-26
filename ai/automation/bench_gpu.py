"""CLI: reference latency of best.pt on the PC GPU (Guide section 6.3, Table H, last row).

Same pre/post-processing (ai/board/common.py), warmup and single pass over sfchd_test as the
tier-2 board scripts; only the inference step runs on the GPU (PyTorch FP32, CUDA-synchronized).
Writes runs/<run_id>/bench/gpu_pt_fp32.json.
"""
import argparse
import json
import time
from importlib.metadata import version
from pathlib import Path

import cv2
import torch
import yaml
from ultralytics.nn.autobackend import AutoBackend

from ai.board.common import WARMUP, list_images, postprocess, preprocess, summarize
from ai.core.dataset import dataset_yaml_path
from ai.core.evaluator import EVAL_SETS, PROTOCOL_VERSION
from ai.core.provenance import file_sha256, provenance

RUNS_DIR = Path(__file__).resolve().parent / "runs"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--device", default="0")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    weights = run_dir / "weights" / "best.pt"
    dev = torch.device(f"cuda:{args.device}")
    model = AutoBackend(str(weights), device=dev, fp16=False, fuse=True, verbose=False).eval()

    dataset, split = EVAL_SETS["sfchd_test"]
    data = yaml.safe_load(dataset_yaml_path(dataset).read_text())
    images = list_images(str(Path(data["path"]) / data[split]))

    def infer(nhwc):
        x = torch.from_numpy(nhwc).to(dev).permute(0, 3, 1, 2).float() / 255
        with torch.no_grad():
            y = model(x)
        y = y[0] if isinstance(y, (list, tuple)) else y
        torch.cuda.synchronize()
        return y.cpu().numpy()

    warm = cv2.imread(str(images[0]))
    for _ in range(WARMUP):
        inp, meta = preprocess(warm)
        postprocess(infer(inp), meta, normalized=False)

    pre, gpu, post, e2e = [], [], [], []
    for path in images:
        bgr = cv2.imread(str(path))
        t0 = time.perf_counter()
        inp, meta = preprocess(bgr)
        t1 = time.perf_counter()
        out = infer(inp)
        t2 = time.perf_counter()
        postprocess(out, meta, normalized=False)
        t3 = time.perf_counter()
        pre.append((t1 - t0) * 1e3)
        gpu.append((t2 - t1) * 1e3)
        post.append((t3 - t2) * 1e3)
        e2e.append((t3 - t0) * 1e3)

    e2e_stats = summarize(e2e)
    record = {
        **provenance(),
        "run_id": args.run_id,
        "tier": "gpu-reference",
        "protocol_version": PROTOCOL_VERSION,
        "model_file": "weights/best.pt",
        "model_sha256": file_sha256(weights),
        "device": torch.cuda.get_device_name(dev),
        "torch_version": version("torch"),
        "n_images": len(images),
        "warmup": WARMUP,
        "latency_ms": {"pre": summarize(pre), "inference": summarize(gpu), "post": summarize(post), "e2e": e2e_stats},
        "fps_latency": round(1000 / e2e_stats["mean"], 2),
    }
    out_path = run_dir / "bench" / "gpu_pt_fp32.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Done: {out_path}  e2e mean {e2e_stats['mean']} ms")


if __name__ == "__main__":
    main()
