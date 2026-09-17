# program.md — agent tự lặp nghiên cứu kiến trúc

**Trạng thái: CHƯA KÍCH HOẠT.** File này mô tả trước vòng lặp sẽ hoạt động thế nào, để khi
có baseline chạy ổn trong `automation/leaderboards/` thì không phải thiết kế lại từ đầu.
Đừng chạy agent theo hướng dẫn này cho tới khi có ít nhất 1 dòng kết quả thật trong
`automation/leaderboards/<dataset>.csv` — trước đó `core/trainer.py` chưa được xác nhận
chạy đúng, agent sẽ không có gì để so sánh.

## Vòng lặp dự kiến

1. Đọc `automation/leaderboards/<dataset>.csv`, lấy điểm `test_map50` tốt nhất hiện tại làm mốc.
2. Sửa hoặc tạo 1 kiến trúc trong `research/experiments/<ten_moi>/draft_model.py`, ghi giả
   thuyết vào `notes.md` (bắt buộc trích nguồn ý tưởng từ `docs/outputs/<topic>/_synthesis.md`
   nếu có, để biết vì sao thử hướng đó).
3. Chạy `python -m ai.automation.run` với 1 config trỏ tới kiến trúc nháp, ngân sách thời
   gian/epoch cố định (giống nguyên tắc "5 phút cố định" của `ai/autoresearch` — số cụ thể
   chốt khi kích hoạt, tuỳ tốc độ máy thật).
4. So `test_map50` mới với mốc ở bước 1. Ghi lại quyết định giữ/bỏ vào `notes.md`.
5. Lặp lại bước 2.

## Điều kiện kích hoạt

- `core/trainer.py` đã chạy thành công ít nhất 1 lần qua `automation/run.py`.
- `automation/leaderboards/<dataset>.csv` có ít nhất 1 dòng (baseline YOLOv8n).
- Đã quyết định ngân sách thời gian/epoch cố định cho mỗi vòng thử (dựa trên tốc độ train
  thật đo được ở baseline, không đoán trước).
