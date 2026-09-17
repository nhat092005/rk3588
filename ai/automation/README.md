# automation/

Vùng chạy chính thức. Mọi kết quả được log đầy đủ, có thể đối chiếu qua các run.
Không chạy training tay ngoài `run.py` — mọi run phải đi qua đây để được log đúng chuẩn.

```
python -m ai.automation.run ai/automation/configs/<ten_config>.yaml
```

- `configs/` — 1 file = 1 thí nghiệm chính thức (model + dataset + hyperparam + seed bắt buộc).
- `runs/<run_id>/` — output tự sinh, không sửa tay: `config.yaml`, `git_commit.txt`, `metrics.csv`,
  `weights/` (gitignore, không commit), `plots/{dataset_stats,sample_predictions,eval_curves}/`,
  `npu_benchmark.json` (from `export_npu.py`, see below).
- `leaderboards/<dataset>.csv` — tổng hợp so sánh mọi run, **tách riêng theo từng dataset**
  (không gộp chung, vì `sfchd`/`sh17`/`css` có class taxonomy khác nhau, mAP không so trực tiếp được).

`export_npu.py`: `python -m ai.automation.export_npu <run_id>`. Runs the Tier 1
(baseline, native `ultralytics` RKNN export) path from `core/rknn/baseline.py` on a
finished training run and writes `runs/<run_id>/npu_benchmark.json`. The Tier 2 manual
optimization pipeline (core_mask / op_target / hybrid quantization) lives in
`core/rknn/deploy.py`, called from `npu/experiments/`, not here — see
`tmp/2026-09-17_baseline_rk3588_npu_optimization.md` section 9.4/9.5 for why the split
exists. Not runnable yet in this repo's current `.venv` (needs `rknn-toolkit2`).
