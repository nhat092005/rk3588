# RK3588 PPE Detection Pipeline

End-to-end PPE (Personal Protective Equipment) detection research and training pipeline targeting Rockchip RK3588 NPU (6 TOPS). Covers dataset preparation, YOLO training, INT8 quantization via RKNN-Toolkit2, and on-board multi-core latency benchmarking.

## Quickstart

Prerequisites:
- Linux x86_64
- [uv](https://docs.astral.sh/uv/) package manager

```bash
# 1. Setup environment and verify bindings (Torch, CUDA, RKNN)
make sync
make check

# 2. Train baseline model
make train CONFIG=ai/automation/configs/sfchd_yolov8n_baseline.yaml

# 3. Export trained checkpoint to RKNN INT8 format
make export-npu RUN=2026-09-17_sfchd_yolov8n_baseline_100ep
```

## Commands & Config Reference

| Command | Arguments / Example | Description |
| :--- | :--- | :--- |
| `make sync` | | Install and sync virtual environment via `uv` |
| `make check` | | Validate PyTorch, CUDA, numpy, and RKNN bindings |
| `make prepare-data` | `DATASET=sfchd` | Process raw dataset under `data/<name>/raw/` |
| `make train` | `CONFIG=ai/automation/configs/<file>.yaml` | Train model using specified configuration |
| `make tail` | `RUN=<run_id>` | Stream training metrics (`results.csv`) |
| `make export-npu` | `RUN=<run_id>` | Export model checkpoint to RKNN format |
| `make benchmark-npu` | `RUN=<run_id> DEVICE=<ip:port> [CORE_MASK=AUTO]` | Profile real latency and mAP on physical board |
| `make leaderboard` | `DATASET=sfchd` | Print evaluation leaderboard for dataset |
| `make clean` | | Remove temporary Python cache directories |

Locations:
- Training configs: `ai/automation/configs/*.yaml`
- Experiment outputs & weights: `ai/automation/runs/<run_id>/`
- Research documentation & deep dives: `docs/`