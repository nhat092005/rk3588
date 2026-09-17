# ai/

Toàn bộ code model cho bài toán PPE detection trên RK3588.

- `core/` — engine dùng chung, nguồn sự thật duy nhất cho cách train/đánh giá. `research/` và `automation/` đều gọi vào đây, không tự viết loop riêng.
- `models/` — định nghĩa kiến trúc (chỉ `nn.Module`, không có logic train).
- `research/` — vùng thử nghiệm kiến trúc mới, ít ràng buộc.
- `automation/` — chạy chính thức, mọi kết quả được log đầy đủ, có thể đối chiếu qua các run.
- `program.md` — hướng dẫn agent tự lặp nghiên cứu kiến trúc. Chưa kích hoạt, chờ có baseline chạy ổn trong `automation/`.

Môi trường Python (`.venv`, `pyproject.toml`) nằm ở gốc repo, không nằm trong `ai/`.
