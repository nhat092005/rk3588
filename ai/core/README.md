# core/

Engine dùng chung — nguồn sự thật duy nhất cho cách train/đánh giá model.
`research/` và `automation/` đều import từ đây, không được tự viết training loop riêng
(tránh trường hợp kết quả nghiên cứu và kết quả benchmark chính thức không đối chiếu được với nhau).

- `dataset.py` — đọc `data/<name>/processed/dataset.yaml`.
- `trainer.py` — train/eval loop, hiện bọc quanh thư viện `ultralytics`.
- `metrics.py` — tính mAP/precision/recall thủ công, dùng khi kiến trúc mới không đi qua API train của `ultralytics`.
- `export.py` — convert model sang RKNN, benchmark trên NPU. **Chưa có code**, chờ giai đoạn deploy.
