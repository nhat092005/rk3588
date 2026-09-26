# core/

Shared engine for model training, evaluation, and deployment.

- `dataset.py`: Dataset loader interface for `data/<name>/processed/dataset.yaml`.
- `trainer.py`: Model training and validation engine.
- `evaluator.py`: Evaluation Protocol v1 (Guide section 5): one evaluator for every model and precision, dataset fingerprint.
- `backends.py`: Inference backends for the evaluator (PyTorch/ONNX via Ultralytics AutoBackend, RKNN on the board via RKNN-Toolkit2).
- `rknn/`: RKNN conversion and deployment tools:
  - `calibration.py`: Calibration image sampling and letterboxed calibration images.
  - `baseline.py`: Standard Ultralytics RKNN export (FP16/INT8) and FP32 ONNX export.
  - `benchmark.py`: Tier-1 board measurements from the PC (`eval_perf`, `eval_memory`).
  - `deploy.py`: RKNN API builder with multi-core (`core_mask`), operator targeting, and hybrid quantization.
