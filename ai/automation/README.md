# automation/

Official execution pipeline: training, evaluation, RKNN export, NPU benchmarks, tables.
Run everything through `make` (`make help`); the order of steps is the Runbook in the Guide,
section 8.1 (`docs/PPE_RK3588S_Research_Master_Guide.md`).

## Main commands

```bash
make phase2 DATASET=sfchd_5class   # train YOLOv8n/s x seeds 42,43,44 + crosscheck + tables
make phase3 DATASET=sfchd_5class   # export FP16/INT8, complexity, evaluate ONNX/RKNN + tables
make phase4 DATASET=sfchd_5class   # tier 1 + tier 2 + throughput + GPU reference + tables
make tables DATASET=sfchd_5class   # results/<dataset>/table_*.md, tables.csv, SOURCES.md
```

Phases skip steps whose result file exists and stop at the first error; re-run the same command to continue.

## Structure

- `configs/`: experiment configurations (model, dataset, hyperparameters, seed).
- `runs/<run_id>/`: `config.yaml`, `metrics.csv`, `logs/`, `eval/`, `bench/`, `export_<precision>.json`, `complexity.json`, `weights/` (git-ignored).
- `leaderboards/<dataset>.csv`: protocol v1 FP32 result of every run, written by `make train`.
- `golden/`: golden numbers that lock the evaluator (protocol v1) and the logs of golden/crosscheck runs.
