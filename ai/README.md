# ai/

PPE detection model pipeline for RK3588.

- `core/`: Shared engine (dataset loaders, trainer, evaluation metrics, RKNN export).
- `models/`: Model architecture definitions (`nn.Module`).
- `research/`: Experimental architectures and ablation studies.
- `automation/`: Official training and evaluation pipeline with persistent logs.
- `npu/`: RKNN deployment experiments (core_mask, op_target, quantization).
- `program.md`: Autonomous architecture search protocol (inactive).

The Python environment (`.venv`, `pyproject.toml`) resides at repository root.
