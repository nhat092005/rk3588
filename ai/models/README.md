# models/

Định nghĩa kiến trúc. 1 file = 1 kiến trúc. Không chứa logic train (logic train nằm ở `core/trainer.py`).

- `yolov8n_baseline.py` — YOLOv8n gốc từ `ultralytics`, không sửa gì. Dùng làm mốc so sánh cho mọi kiến trúc mới.
- `yolov8s_baseline.py` — YOLOv8s gốc từ `ultralytics`, không sửa gì. Đối chiếu size lớn hơn với `yolov8n_baseline.py`.
- Kiến trúc mới "tốt nghiệp" từ `research/experiments/<ten>/draft_model.py` được đặt vào đây khi đã ổn định.

Note on first-time checkpoint downloads: `WEIGHTS` here is a bare filename (e.g. `"yolov8s.pt"`), resolved by
`ultralytics`' own `attempt_download_asset()`. That function only uses `settings.weights_dir` to check for an
**existing** cached file - a brand new checkpoint name always downloads straight into the current working
directory on its first use, regardless of `weights_dir`. Move it into `~/.cache/ultralytics/weights/` once
after the first run of any new `WEIGHTS` value, and it will never leak into the repo root again for that
checkpoint (verified 2026-09-18, see `tmp/2026-09-17_baseline_rk3588_npu_optimization.md`).
