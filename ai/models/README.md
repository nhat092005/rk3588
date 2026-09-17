# models/

Định nghĩa kiến trúc. 1 file = 1 kiến trúc. Không chứa logic train (logic train nằm ở `core/trainer.py`).

- `yolo_baseline.py` — YOLOv8n gốc từ `ultralytics`, không sửa gì. Dùng làm mốc so sánh cho mọi kiến trúc mới.
- Kiến trúc mới "tốt nghiệp" từ `research/experiments/<ten>/draft_model.py` được đặt vào đây khi đã ổn định.
