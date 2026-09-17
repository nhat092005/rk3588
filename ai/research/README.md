# research/

Vùng thử nghiệm kiến trúc mới. Ít ràng buộc hơn `automation/`, nhưng vẫn phải chạy qua
`core/trainer.py` — không tự viết training loop riêng.

- `notebooks/` — notebook thử ý tưởng, phân tích ablation.
- `experiments/<ten_thu_nghiem>/`
  - `notes.md` — ghi rõ ý tưởng lấy từ `docs/outputs/<topic>/_synthesis.md` nào, giả thuyết, kết quả sơ bộ.
  - `draft_model.py` — bản nháp kiến trúc, trước khi thành `models/<ten_kien_truc_moi>.py` chính thức.

Khi 1 kiến trúc trong `experiments/` chạy ổn định và có số liệu tốt hơn baseline trong
`automation/leaderboards/`, "tốt nghiệp" nó bằng cách chuyển sang `models/`, rồi thêm 1
config trong `automation/configs/` để benchmark chính thức.
