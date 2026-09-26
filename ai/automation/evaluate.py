"""CLI: evaluate a run under Evaluation Protocol v1 (Guide section 5.1).

--backend pt/onnx run FP32 on the PC (GPU/CPU); rknn runs NPU inference on the board
(ai/board/infer_dump.py, RKNNLite), since PC-side rknn_server measured ~35s/image over
Tailscale vs 42ms on-board. Writes runs/<run_id>/eval/<backend>_<precision>_<eval_set>.json.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import yaml

from ai.core.backends import RknnDumpBackend, UltralyticsBackend
from ai.core.evaluator import CONF, EVAL_SETS, EVAL_SETS_BY_DATASET, build_eval_loader, evaluate
from ai.core.provenance import REPO_ROOT, file_sha256, git_commit, git_dirty

RUNS_DIR = Path(__file__).resolve().parent / "runs"


def sh(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def board_dump(run_dir: Path, precision: str, eval_set: str, board: str, board_repo: str) -> Path:
    """Copy model + eval-set images to the board, run infer_dump there, copy the dump back."""
    rknn_dir = run_dir / "weights" / f"rknn_{precision}"
    rel_run = run_dir.relative_to(REPO_ROOT)
    loader, _ = build_eval_loader(eval_set)
    images = [str(Path(p).relative_to(REPO_ROOT)) for p in loader.dataset.im_files]
    remote_dump = f"{rel_run}/weights/npu_dump_{precision}_{eval_set}.npz"
    local_dump = run_dir / "weights" / f"npu_dump_{precision}_{eval_set}.npz"
    with tempfile.TemporaryDirectory() as tmp:
        lst = Path(tmp) / f"{eval_set}.txt"
        lst.write_text("\n".join(images) + "\n")
        sh(["ssh", board, f"mkdir -p {board_repo}/{rel_run}/weights"])
        sh(["rsync", "-aL", f"--files-from={lst}", str(REPO_ROOT), f"{board}:{board_repo}/"])  # images (skips unchanged)
        sh(["rsync", "-a", f"{rknn_dir}/", f"{board}:{board_repo}/{rel_run}/weights/rknn_{precision}/"])
        sh(["scp", "-q", str(lst), f"{board}:{board_repo}/{rel_run}/weights/{lst.name}"])
    sh(["ssh", board, f"cd {board_repo} && .venv-board/bin/python -m ai.board.infer_dump "
        f"--model {rel_run}/weights/rknn_{precision} --list {rel_run}/weights/{eval_set}.txt --out {remote_dump} "
        f"--run-id {run_dir.name} --git-commit {git_commit()} --git-dirty {str(git_dirty()).lower()}"])
    sh(["scp", "-q", f"{board}:{board_repo}/{remote_dump}", f"{board}:{board_repo}/{remote_dump[:-4]}.json", str(local_dump.parent)])
    return local_dump


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--backend", choices=["pt", "onnx", "rknn"], required=True)
    parser.add_argument("--precision", choices=["fp16", "int8"], help="rknn only")
    parser.add_argument("--board", default="minhnhat@100.67.251.37", help="rknn only: ssh target")
    parser.add_argument("--board-repo", default="rk3588", help="rknn only: repo path on the board")
    parser.add_argument("--device", default="0", help="pt only: CUDA index or cpu")
    parser.add_argument("--eval-set", choices=list(EVAL_SETS), help="default: every eval set of the run's dataset")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    dataset = yaml.safe_load((run_dir / "config.yaml").read_text())["dataset"]
    eval_sets = [args.eval_set] if args.eval_set else EVAL_SETS_BY_DATASET[dataset]
    out_dir = run_dir / "eval"
    out_dir.mkdir(exist_ok=True)

    def save(result: dict, tag: str, eval_set: str, model_path: Path, extra: dict) -> None:
        result = {**result, "run_id": args.run_id, "model_file": str(model_path.relative_to(run_dir)),
                  "model_sha256": file_sha256(model_path), **extra}
        path = out_dir / f"{tag}_{eval_set}.json"
        path.write_text(json.dumps(result, indent=2) + "\n")
        print(f"{path}: mAP50-95 {result['map50_95']}")

    if args.backend in ("pt", "onnx"):
        model_path = run_dir / "weights" / ("best.pt" if args.backend == "pt" else "best.onnx")
        backend = UltralyticsBackend(model_path, args.device if args.backend == "pt" else "cpu")
        extra = {"backend": "pytorch" if args.backend == "pt" else "onnxruntime-cpu-pc"}
        for eval_set in eval_sets:
            save(evaluate(backend, eval_set), f"{args.backend}_fp32", eval_set, model_path, extra)
        return

    if not args.precision:
        parser.error("--backend rknn needs --precision")
    rknn_dir = run_dir / "weights" / f"rknn_{args.precision}"
    rknn_path = next(rknn_dir.glob("*.rknn"))
    for eval_set in eval_sets:
        dump = board_dump(run_dir, args.precision, eval_set, args.board, args.board_repo)
        backend = RknnDumpBackend(dump, rknn_dir, CONF)
        if backend.meta["model_sha256"] != file_sha256(rknn_path):
            raise ValueError("model on the board differs from the local .rknn")
        result = evaluate(backend, eval_set)
        if backend.rows:
            raise ValueError(f"{len(backend.rows)} board images were not evaluated")
        save(result, f"rknn_{args.precision}", eval_set, rknn_path,
             {"backend": "rknnlite-on-board", "sdk_version": backend.meta["sdk_version"],
              "board_dump": {k: backend.meta[k] for k in ("created_at", "kept_anchors", "normalized_boxes")}})


if __name__ == "__main__":
    main()
