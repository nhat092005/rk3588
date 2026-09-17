# automation/

Vùng chạy chính thức. Mọi kết quả được log đầy đủ, có thể đối chiếu qua các run.
Không chạy training tay ngoài `run.py` — mọi run phải đi qua đây để được log đúng chuẩn.

```
python -m ai.automation.run ai/automation/configs/<ten_config>.yaml
```

- `configs/` — 1 file = 1 thí nghiệm chính thức (model + dataset + hyperparam + seed bắt buộc).
- `runs/<run_id>/` — output tự sinh, không sửa tay: `config.yaml`, `git_commit.txt`, `metrics.csv`,
  `weights/` (gitignore, không commit), `plots/{dataset_stats,sample_predictions,eval_curves}/`.
  `npu_benchmark.json` sẽ xuất hiện khi `core/export.py` có code (lớp 2, chưa làm).
- `leaderboards/<dataset>.csv` — tổng hợp so sánh mọi run, **tách riêng theo từng dataset**
  (không gộp chung, vì `sfchd`/`sh17`/`css` có class taxonomy khác nhau, mAP không so trực tiếp được).
