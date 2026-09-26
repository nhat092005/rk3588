"""Run a whole phase of Guide section 8 through make (make phase2|phase3|phase4|phase10 DATASET=...).

Each step = one make target + the result file proving it is done. Finished steps are skipped,
the first failure stops the phase, and every phase ends with make tables.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

from ai.core.evaluator import EVAL_SETS_BY_DATASET, PROTOCOL_VERSION

AUTOMATION_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUTOMATION_DIR.parents[1]
RUNS_DIR = AUTOMATION_DIR / "runs"
MODELS = ["yolov8n_baseline", "yolov8s_baseline"]
SEED = 42  # every phase trains one seed (Guide section 7)
EXTRA_SEEDS = [43, 44]  # Phase 10 only
MASKS_1CTX = ["AUTO", "CORE_0", "CORE_0_1", "CORE_0_1_2"]
MASKS_3CTX = "CORE_0,CORE_1,CORE_2"


def config_path(dataset: str, model: str) -> Path:
    return AUTOMATION_DIR / "configs" / f"{dataset}_{model}.yaml"


def run_id(dataset: str, model: str, seed: int) -> str:
    out = subprocess.run([sys.executable, "-m", "ai.automation.run", str(config_path(dataset, model)),
                          "--seed", str(seed), "--print-run-id"], cwd=REPO_ROOT, capture_output=True, text=True)
    if out.returncode == 0:
        return out.stdout.strip().splitlines()[-1]
    # run already exists: same naming rule as run.py
    import yaml
    cfg = yaml.safe_load(config_path(dataset, model).read_text())
    return f"{cfg['dataset']}_{cfg['model']}_{cfg['epochs']}ep_s{seed}"


def leaderboard_runs(dataset: str) -> list[str]:
    path = AUTOMATION_DIR / "leaderboards" / f"{dataset}.csv"
    if not path.exists():
        return []
    with path.open() as fh:
        return sorted({r["run_id"] for r in csv.DictReader(fh) if r["protocol"] == PROTOCOL_VERSION})


def step(target: str, done: Path | None, **make_vars) -> tuple[list[str], Path | None]:
    return ["make", target] + [f"{k}={v}" for k, v in make_vars.items()], done


def phase2(ds: str) -> list:
    first_set = EVAL_SETS_BY_DATASET[ds][0]
    steps = []
    for model in MODELS:
        steps.append(train_step(ds, model, SEED, first_set))
    crosscheck_run = run_id(ds, MODELS[0], SEED)
    steps.append(step("crosscheck", RUNS_DIR / crosscheck_run / "eval" / f"crosscheck_{first_set}.json", RUN=crosscheck_run))
    return steps


def train_step(ds: str, model: str, seed: int, first_set: str):
    rid = run_id(ds, model, seed)
    return step("train", RUNS_DIR / rid / "eval" / f"pt_fp32_{first_set}.json",
                CONFIG=config_path(ds, model).relative_to(REPO_ROOT), SEED=seed)


def npu_eval_steps(rid: str, first_set: str) -> list:
    rd = RUNS_DIR / rid
    return [
        step("export-npu", rd / "export_fp16.json", RUN=rid, PREC="fp16"),
        step("export-npu", rd / "export_int8.json", RUN=rid, PREC="int8"),
        step("evaluate", rd / "eval" / f"rknn_fp16_{first_set}.json", RUN=rid, BACKEND="rknn", PREC="fp16"),
        step("evaluate", rd / "eval" / f"rknn_int8_{first_set}.json", RUN=rid, BACKEND="rknn", PREC="int8"),
    ]


def phase3(ds: str) -> list:
    first_set = EVAL_SETS_BY_DATASET[ds][0]
    steps = [step("board-sync", None)]  # NPU accuracy runs on the board over ssh, no rknn_server needed
    for rid in leaderboard_runs(ds):
        rd = RUNS_DIR / rid
        steps += npu_eval_steps(rid, first_set)[:2] + [
            step("complexity", rd / "complexity.json", RUN=rid),
            step("evaluate", rd / "eval" / f"onnx_fp32_{first_set}.json", RUN=rid, BACKEND="onnx"),
        ] + npu_eval_steps(rid, first_set)[2:]
    return steps


def phase4(ds: str) -> list:
    steps = [step("board-check", None, LOCK=1), step("board-sync", None)]
    for model in MODELS:
        rid = run_id(ds, model, SEED)
        bench = RUNS_DIR / rid / "bench"
        steps.append(step("benchmark-npu", bench / "tier1_fp16_AUTO.json", RUN=rid, PREC="fp16", CORE_MASK="AUTO"))
        steps += [step("benchmark-npu", bench / f"tier1_int8_{m}.json", RUN=rid, PREC="int8", CORE_MASK=m) for m in MASKS_1CTX]
        steps += [step("bench-board", bench / f"tier2_{p}_AUTO.json", RUN=rid, PREC=p, CORE_MASK="AUTO") for p in ("fp16", "int8")]
        steps.append(step("bench-board-cpu", bench / "tier2_cpu_onnx_t4.json", RUN=rid, THREADS=4))
        steps += [step("bench-board-throughput", bench / f"throughput_int8_{m.replace(',', '-')}.json", RUN=rid, PREC="int8", CORE_MASKS=m)
                  for m in MASKS_1CTX + [MASKS_3CTX]]
        steps.append(step("bench-gpu", bench / "gpu_pt_fp32.json", RUN=rid))
    return steps


def phase10(ds: str, models: list[str]) -> list:
    """Seeds 43, 44 for the key models: train, export, NPU accuracy; tier-1 check on one seed-43 run."""
    first_set = EVAL_SETS_BY_DATASET[ds][0]
    steps = [step("board-sync", None)]
    for model in models:
        for seed in EXTRA_SEEDS:
            steps += [train_step(ds, model, seed, first_set)] + npu_eval_steps(run_id(ds, model, seed), first_set)
    rid = run_id(ds, models[0], EXTRA_SEEDS[0])  # same architecture: NPU time should match seed 42
    steps += [step("board-check", None),
              step("benchmark-npu", RUNS_DIR / rid / "bench" / "tier1_int8_AUTO.json", RUN=rid, PREC="int8", CORE_MASK="AUTO")]
    return steps


PHASES = {"phase2": phase2, "phase3": phase3, "phase4": phase4, "phase10": phase10}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=list(PHASES))
    parser.add_argument("--dataset", required=True, choices=list(EVAL_SETS_BY_DATASET))
    parser.add_argument("--models", default=MODELS[0], help="phase10 only: comma-separated, e.g. yolov8n_baseline,<proposed>")
    args = parser.parse_args()

    build = PHASES[args.phase]
    steps = (build(args.dataset, args.models.split(",")) if args.phase == "phase10" else build(args.dataset))
    steps += [step("tables", None, DATASET=args.dataset)]
    for i, (cmd, done) in enumerate(steps, 1):
        label = f"[{args.phase} {i}/{len(steps)}] {' '.join(cmd)}"
        if done is not None and done.exists():
            print(f"{label}  SKIP (done: {done.relative_to(REPO_ROOT)})", flush=True)
            continue
        print(label, flush=True)
        if subprocess.run(cmd, cwd=REPO_ROOT).returncode != 0:
            print(f"STOPPED at step {i}: fix the error above, then re-run `make {args.phase} DATASET={args.dataset}`")
            sys.exit(1)
        if done is not None and not done.exists():
            print(f"STOPPED at step {i}: command succeeded but {done.relative_to(REPO_ROOT)} was not written")
            sys.exit(1)
    print(f"{args.phase} complete. Tables: results/{args.dataset}/")


if __name__ == "__main__":
    main()
