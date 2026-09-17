# core/

Engine dùng chung — nguồn sự thật duy nhất cho cách train/đánh giá model.
`research/` và `automation/` đều import từ đây, không được tự viết training loop riêng
(tránh trường hợp kết quả nghiên cứu và kết quả benchmark chính thức không đối chiếu được với nhau).

- `dataset.py` — đọc `data/<name>/processed/dataset.yaml`.
- `trainer.py` — train/eval loop, hiện bọc quanh thư viện `ultralytics`.
- `metrics.py` — mAP/precision/recall computed by hand (reuses `ultralytics.utils.metrics`),
  for predictions that don't go through `ultralytics`' own `val()` — e.g. RKNN inference in
  `rknn/`, or a `research/` architecture with a custom forward pass.
- `rknn/` — RKNN export/benchmark engine, split by responsibility (see each module's own
  docstring and `tmp/2026-09-17_baseline_rk3588_npu_optimization.md` section 9):
  - `calibration.py` — calibration image sampling, no `rknn-toolkit2` dependency.
  - `baseline.py` — Tier 1, native `ultralytics` RKNN export. Written but not runnable yet
    (needs `rknn-toolkit2` in `.venv`).
  - `deploy.py` — Tier 2, manual `rknn.api.RKNN` for core_mask/op_target/hybrid
    quantization — the thesis' actual optimization layer. Not implemented yet.
