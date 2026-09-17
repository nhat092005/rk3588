# core/

Shared engine for model training, evaluation, and deployment.

- `dataset.py`: Dataset loader interface for `data/<name>/processed/dataset.yaml`.
- `trainer.py`: Model training and validation engine.
- `metrics.py`: Standalone mAP, precision, and recall evaluation for non-Ultralytics inferences.
- `rknn/`: RKNN conversion and deployment tools:
  - `calibration.py`: Calibration image dataset sampling.
  - `baseline.py`: Standard Ultralytics RKNN export pipeline.
  - `deploy.py`: RKNN API builder with multi-core (`core_mask`), operator targeting, and hybrid quantization.
