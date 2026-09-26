# RK3588 PPE Detection Pipeline

End-to-end YOLO training/deployment research pipeline for PPE (Personal
Protective Equipment) detection, targeting the Rockchip RK3588 NPU (6 TOPS).
Covers dataset preparation, YOLOv8/YOLOv11 training, INT8/FP16 quantization
via RKNN-Toolkit2, and real multi-core latency benchmarking on the board.

Current scope: 5 classes (`person`, `helmet`, `head`, `safety_clothes`,
`self_clothes`), primary datasets `sfchd_5class` / `sfchd_shel5k`. Class
mapping details: `data/CLASS_MAPPING.md`.

## Quickstart

Prerequisites:
- Linux x86_64, CUDA GPU for training
- [uv](https://docs.astral.sh/uv/) for virtualenv management
- SSH access to the board (`BOARD` variable, see `Makefile`) for the
  on-board benchmark step

```bash
# 1. Set up environment and verify bindings (Torch, CUDA, RKNN)
make sync
make check

# 2. Train baseline (seed 42) + crosscheck evaluator
make phase2 DATASET=sfchd_5class

# 3. Export FP16/INT8, measure complexity, evaluate on ONNX/RKNN
make phase3 DATASET=sfchd_5class

# 4. Tier 1 (PC) + tier 2 (board) benchmark — needs protocol LOCK and a
#    board that has already been set up
make phase4 DATASET=sfchd_5class

# 5. Aggregate result tables
make tables DATASET=sfchd_5class
```

`phase10` reruns seeds 43/44 for the final key models, once the phases above
are stable.

## Full command reference

```bash
make help
```

lists every target (evaluate, golden-test, board-setup/sync, bench-board*,
demo-video/images, archive/restore, ...) with a description — this is the
canonical reference; the README does not duplicate it to avoid drifting out
of sync when the Makefile changes.

## Key locations

- Training configs: `ai/automation/configs/*.yaml`
- Per-run results & weights: `ai/automation/runs/<run_id>/`
- Full runbook (Phase 0-10, evaluation protocol, result tables A-M):
  `docs/PPE_RK3588S_Research_Master_Guide.md`
- Paper notes / synthesis: `docs/_notes/`, `docs/outputs/`
