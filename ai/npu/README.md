# npu/

NPU deployment-configuration experiments, parallel to `research/` but for a different axis:
`research/` tries new **architectures** (graduates into `models/`); `npu/` tries new
**RKNN deployment configs** for an already-trained architecture (core_mask, op_target,
hybrid quantization, SRAM budget) and graduates into `automation/`.

This is the primary contribution area of the thesis (low-level NPU deployment
optimization), not a side experiment.

- `experiments/<name>/`
  - `notes.md` — hypothesis, config used (core_mask / op_target / quant scheme), result.
    Must go through `core/rknn/deploy.py`, same rule as `research/` going through
    `core/trainer.py` — no separate hand-rolled RKNN build code per experiment.
  - `runs/<date>/` — one config's raw output: `calib_list.txt`, `model.rknn` (gitignore),
    `npu_benchmark.json` (tracked). A new `runs/<date>/` per attempt, so trying several
    core_mask/op_target variants inside the same experiment never overwrites a previous
    result.

When a config in `experiments/` beats the current best latency/mAP-drop tradeoff, graduate
it by adding an official config under `automation/` — same pattern `research/` uses to
graduate a model into `models/`.

Design rationale and the calibration-sampling probability analysis behind this split are
recorded in `tmp/2026-09-17_baseline_rk3588_npu_optimization.md` (section 9), not here.
