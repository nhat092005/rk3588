"""CLI: tier-1 NPU measurements from the PC (Guide section 5.3, Tables G, I, K, L).

Runs 3 separate eval_perf sessions, since perf_debug/eval_mem change the measured time:
latency (median of 5 calls), per-layer table (Table K), and NPU memory (Table L).
Writes runs/<run_id>/bench/tier1_<precision>_<core_mask>.json (+ _layers.json/.txt).
"""
import argparse
import json
from pathlib import Path

from ai.core.evaluator import PROTOCOL_VERSION
from ai.core.provenance import file_sha256, provenance
from ai.core.rknn.benchmark import CORE_MASK, PERF_REPEATS, connect_board, measure_latency, measure_layers, measure_memory

RUNS_DIR = Path(__file__).resolve().parent / "runs"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", help="an existing directory under ai/automation/runs/")
    parser.add_argument("device_id", help="board adb address, e.g. 100.67.251.37:5555")
    parser.add_argument("--precision", choices=["fp16", "int8"], required=True)
    parser.add_argument("--core-mask", default="AUTO", choices=list(CORE_MASK))
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    rknn_path = next((run_dir / "weights" / f"rknn_{args.precision}").glob("*.rknn"))
    out_dir = run_dir / "bench"
    out_dir.mkdir(exist_ok=True)
    stem = f"tier1_{args.precision}_{args.core_mask}"
    connect = lambda **kw: connect_board(str(rknn_path), args.device_id, core_mask=args.core_mask, **kw)  # noqa: E731

    with connect() as rknn:
        sdk_version = str(rknn.get_sdk_version())
        latency = measure_latency(rknn)
    with connect(perf_debug=True) as rknn:
        layers, layers_text = measure_layers(rknn)
    with connect(eval_mem=True) as rknn:
        memory = measure_memory(rknn)

    (out_dir / f"{stem}_layers.txt").write_text(layers_text)
    (out_dir / f"{stem}_layers.json").write_text(json.dumps(layers, indent=1) + "\n")
    record = {
        **provenance(),
        "run_id": args.run_id,
        "tier": 1,
        "protocol_version": PROTOCOL_VERSION,
        "precision": args.precision,
        "core_mask": args.core_mask,
        "model_file": str(rknn_path.relative_to(run_dir)),
        "model_sha256": file_sha256(rknn_path),
        "device_id": args.device_id,
        "sdk_version": sdk_version,
        "fix_freq": True,
        "eval_perf_repeats": PERF_REPEATS,
        **{k: v for k, v in latency.items() if k != "raw_last"},
        "npu_memory_mib": memory,
        "cpu_ops": layers["cpu_ops"],
        "n_layers": layers["n_layers"],
        "debug_total_us": layers["debug_total_us"],
        "eval_perf_summary_raw": latency["raw_last"],
        "layers_files": [f"{stem}_layers.json", f"{stem}_layers.txt"],
    }
    out_path = out_dir / f"{stem}.json"
    out_path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Done: {out_path}  NPU {record['npu_latency_ms']} ms (all: {record['npu_latency_ms_all']}), CPU ops: {record['cpu_ops']}")


if __name__ == "__main__":
    main()
