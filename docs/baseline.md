# Baseline Flow: Triển khai AI trên RK3588 (Orange Pi 5, 4GB RAM)

## 2 hướng trọng tâm của đề tài - nằm ở bước nào?

Đề tài "Tối ưu (...) chạy trên NPU Core, ứng dụng PPE" có 2 hướng trọng tâm khả dĩ,
mỗi hướng rơi vào đúng 1 nhóm bước trong baseline dưới đây:

| Hướng trọng tâm | Rơi vào bước | Paper nền tảng đã có |
|---|---|---|
| **Tối ưu mô hình** (pruning, quantization, kiến trúc nhẹ) | Bước 1, 2, 4 | Quantization Survey (Gholami), MCUNet |
| **Tối ưu inference/deployment** (multi-core scheduling, memory) | Bước 5, 6, 7 | Flexer, Layer-Puzzle, Eyeriss, TVM |

→ Tên đề tài có chữ **"NPU Core"** nên khớp nhất với hướng **inference/deployment**
(bước 5-7) - đây nên là trọng tâm chính, còn quantization (bước 4) làm nền chuẩn bị
bắt buộc trước khi tối ưu sâu multi-core.

---

## Bảng tổng quan hướng tối ưu theo từng bước

| Bước | Có thể tối ưu? | Hướng tối ưu chính |
|---|---|---|
| 1. Chọn model | Có | Chọn biến thể nhẹ (YOLOv8n thay vì YOLOv8x), giảm input resolution, chọn kiến trúc thiết kế sẵn cho edge (MobileNet, EfficientNet-Lite) |
| 2. Train model | Có | Pruning, Knowledge Distillation, Quantization-Aware Training (QAT) để chuẩn bị cho bước 4 |
| 3. Export ONNX | Có (nhẹ) | Graph simplification, constant folding, loại node thừa trước khi đưa vào RKNN |
| 4. Convert + quantize | Có (quan trọng nhất) | Chọn per-channel vs per-layer quantization, mixed precision INT8+FP16, weight compression, weight sharing |
| 5. Deploy + chạy thử | Có (nhẹ) | Dùng zero-copy API, chọn batch size hợp lý |
| 6. Profile | Không tối ưu, chỉ chẩn đoán | Đây là bước tìm bottleneck để quyết định tối ưu ở đâu, không phải bước tối ưu |
| 7. Tối ưu chuyên sâu | Có (trọng tâm) | Multi-core scheduling, operator fusion, memory reuse/SRAM, tránh CPU fallback, custom op, pipeline overlap |
| 8. Benchmark | Không tối ưu, chỉ đo | Đảm bảo đo đúng phương pháp để so sánh trước/sau chính xác |

---

## 1. Chọn model đã được hỗ trợ tốt `[Tối ưu mô hình]`

- **Việc cần làm:** chọn kiến trúc model đã được RKNN cộng đồng dùng nhiều (YOLOv5/v8, MobileNet, ResNet, EfficientNet)
- **Viết bằng gì:** không cần code - chỉ cần đọc tài liệu
- **Công cụ tra cứu:** list operator support của RKNN-Toolkit2, RKNN Model Zoo
- **Input:** bài toán cần giải (classification/detection/segmentation...)
- **Output:** 1 kiến trúc model cụ thể + biết chắc operator nó dùng được NPU support
- **Hướng tối ưu:**
 - Chọn biến thể nhỏ nhất đủ đáp ứng accuracy yêu cầu (ví dụ YOLOv8n/s thay vì m/l/x)
 - Giảm input resolution (320x320 thay vì 640x640) nếu bài toán cho phép - giảm trực tiếp compute + memory
 - Ưu tiên kiến trúc vốn thiết kế cho mobile/edge (MobileNet, ShuffleNet, EfficientNet-Lite) thay vì kiến trúc gốc cho GPU/server

---

## 2. Train model `[Tối ưu mô hình]`

- **Việc cần làm:** huấn luyện hoặc tải pretrained model, fine-tune nếu cần
- **Viết bằng gì:** Python - PyTorch hoặc TensorFlow
- **Công cụ:** Google Colab / máy có GPU / máy PC thường - chưa cần đụng RK3588
- **Input:** dataset, model architecture đã chọn ở bước 1
- **Output:** file weight (`.pt`, `.h5`/SavedModel)
- **Hướng tối ưu:**
 - **Pruning** (structured/unstructured) - cắt bớt weight/channel ít quan trọng trước khi export, giảm model size
 - **Knowledge Distillation** - train model nhỏ (student) học từ model lớn (teacher) để giữ accuracy tốt hơn dù nhẹ hơn
 - **Quantization-Aware Training (QAT)** - train model đã "biết trước" mình sẽ bị ép về INT8, giúp accuracy sau quantize (bước 4) ít bị rớt hơn so với Post-Training Quantization thông thường

---

## 3. Export sang ONNX

- **Việc cần làm:** convert model đã train sang định dạng ONNX
- **Viết bằng gì:** Python - `torch.onnx.export()` hoặc `tf2onnx`
- **Công cụ:** thư viện `onnx`, `onnxruntime` để verify lại
- **Input:** file weight từ bước 2
- **Output:** file `.onnx` đã verify đúng
- **Hướng tối ưu:**
 - Chạy **onnx-simplifier** để đơn giản hóa graph (loại node thừa, gộp constant) trước khi đưa vào RKNN-Toolkit2 - giúp bước 4 convert mượt hơn, ít lỗi operator lạ hơn
 - Kiểm tra opset version phù hợp - opset quá cũ/mới có thể khiến RKNN-Toolkit2 không nhận diện được 1 số operator, phải fallback CPU oan uổng

---

## 4. Convert + quantize bằng RKNN-Toolkit2 (trên PC) `[Tối ưu mô hình]`

- **Việc cần làm:** convert `.onnx` → `.rknn`, quantize INT8
- **Viết bằng gì:** Python - API `rknn-toolkit2` (`RKNN()`, `.load_onnx()`, `.build()`, `.export_rknn()`)
- **Công cụ:** cài trên PC x86, KHÔNG cài trên board
- **Input:** file `.onnx` + calibration dataset
- **Output:** file `.rknn` + log accuracy trước/sau quantize
- **Hướng tối ưu (bước quan trọng nhất):**
 - **Per-channel quantization** thay vì per-layer nếu accuracy rớt nhiều - chính xác hơn nhưng tốn thêm chút overhead
 - **Mixed precision INT8+FP16** - giữ FP16 cho các layer nhạy cảm (ví dụ layer đầu/cuối), INT8 cho phần còn lại
 - **Weight Compression** (RKNN-Toolkit2 hỗ trợ sẵn) - giảm dung lượng weight, quan trọng với RAM 4GB
 - **Weight Sharing** - giảm memory usage khi nhiều model dùng chung 1 số weight
 - Chọn **calibration dataset đại diện tốt** (đủ đa dạng, đúng phân phối dữ liệu thật) - calibration kém sẽ khiến quantize sai lệch dù kỹ thuật đúng

---

## 5. Deploy lên board, chạy inference thử `[Tối ưu inference/deployment]`

- **Việc cần làm:** copy `.rknn` lên board, load model, chạy thử
- **Viết bằng gì:** Python (`rknn_toolkit_lite2`) hoặc C/C++ (RKNPU2 C API)
- **Công cụ:** RKNN Runtime có sẵn trên OS board
- **Input:** file `.rknn`, ảnh/video test
- **Output:** kết quả inference + latency/FPS baseline
- **Hướng tối ưu:**
 - Dùng **zero-copy API** (`rknn_create_mem`, tránh copy dư thừa giữa CPU-NPU buffer) - quan trọng với RAM hạn chế
 - Chọn **batch size** hợp lý - batch lớn tăng throughput nhưng tốn RAM, cần cân bằng với giới hạn 4GB

---

## 6. Profile bottleneck `[Tối ưu inference/deployment]`

- **Việc cần làm:** xác định model chậm ở đâu
- **Viết bằng gì:** không code thêm - set biến môi trường + đọc log
- **Công cụ:** `RKNN_LOG_LEVEL=4`, `rknn.eval_perf()`
- **Input:** model `.rknn` đã chạy được ở bước 5
- **Output:** báo cáo layer nào chậm, layer nào fallback CPU, compute-bound hay memory-bound
- **Hướng tối ưu:** không áp dụng - đây là bước **chẩn đoán**, kết quả của nó quyết định bạn sẽ tối ưu gì ở bước 7, tự nó không phải chỗ để tối ưu

---

## 7. Tối ưu chuyên sâu `[Tối ưu inference/deployment]`

- **Việc cần làm:** xử lý đúng bottleneck tìm được ở bước 6
- **Viết bằng gì:** Python (RKNN-Toolkit2 API để quantize/config lại) hoặc C/C++ nếu tự viết scheduler
- **Công cụ:** tham số `core_mask` (RKNN Runtime), kỹ thuật memory reuse từ paper Flexer
- **Input:** kết quả profile ở bước 6
- **Output:** phiên bản có latency thấp hơn, có số liệu so sánh
- **Hướng tối ưu (trọng tâm của đề tài):**
 - **Multi-core scheduling** - set `core_mask` để chia workload qua 3 NPU core (chạy song song nhiều model, hoặc split 1 model lớn)
 - **Operator fusion** - gộp các layer liên tiếp (Conv-BN-ReLU) thành 1 operator để giảm số lần ghi/đọc memory
 - **Memory reuse / SRAM** - tận dụng tính năng "storing weights or feature maps on SRAM" của RK3588 để giảm băng thông DDR
 - **Tránh CPU fallback** - thay layer/operator gây fallback bằng operator tương đương được NPU support
 - **Custom operator** - viết operator riêng nếu 1 layer đặc thù không có sẵn support
 - **Pipeline overlap** - chạy pre/post-processing trên CPU song song với NPU đang inference (double buffering), tránh CPU thành bottleneck mới sau khi NPU đã tối ưu

---

## 8. Benchmark + viết báo cáo

- **Việc cần làm:** đo lại toàn bộ pipeline, so sánh trước/sau tối ưu
- **Viết bằng gì:** Python (`time.time()` đo lặp nhiều lần lấy trung bình) + Excel/matplotlib vẽ biểu đồ
- **Công cụ:** đồng hồ đo thời gian, theo dõi nhiệt độ/điện năng nếu có sensor
- **Input:** kết quả benchmark trước và sau tối ưu
- **Output:** bảng số liệu + biểu đồ cho báo cáo đề tài
- **Hướng tối ưu:** không áp dụng - đây là bước **đo lường**, cần chính xác và nhất quán phương pháp đo (cùng điều kiện, cùng số lần lặp) để so sánh trước/sau có ý nghĩa, không phải chỗ để cải thiện hiệu năng

### 8.0 Benchmark ở đâu, lúc nào? - làm rõ trước khi đo

Đây là điểm hay bị mơ hồ nhất, cần tách rõ **3 vị trí đo**, không gộp chung:

| Vị trí đo | Khi nào | Đo được gì | Đo KHÔNG được gì |
|---|---|---|---|
| **(A) Trên PC - lúc build model** (bước 2-4) | Ngay sau train, ngay sau quantize (trước khi đưa lên board) | Accuracy (mAP), accuracy drop sau quantize, số tham số, FLOPs, dung lượng model | Latency/FPS thật, NPU utilization, công suất tiêu thụ - vì **chưa chạy trên NPU thật**, PC không có NPU RK3588 |
| **(B) Trên board - lúc chưa tối ưu (baseline)** (ngay sau bước 5) | Vừa deploy `.rknn` lên board, chạy thử lần đầu | Latency, FPS, NPU utilization, peak RAM, công suất - đây là **baseline thật** để so sánh | Chưa áp dụng multi-core/memory optimization gì cả |
| **(C) Trên board - sau khi tối ưu** (sau bước 7) | Sau khi áp dụng multi-core scheduling, memory reuse... | Toàn bộ chỉ số như (B), đo lại để so sánh | - |

**Nguyên tắc bắt buộc:** mọi chỉ số về **latency, throughput, resource utilization, energy**
CHỈ có giá trị khi đo ở (B) và (C) - tức là **trên chính Orange Pi 5**, không phải trên
PC dù RKNN-Toolkit2 có hiển thị số liệu ước lượng lúc convert. Số liệu PC chỉ mang tính
tham khảo/mô phỏng, không dùng để báo cáo kết quả cuối vì không phản ánh đúng phần cứng
NPU thật (khác biệt schedule, cache, nhiệt độ thực tế...). Riêng **accuracy (mAP)** là
chỉ số duy nhất đo được cả ở PC lẫn board, nhưng vẫn nên đo lại 1 lần trên board sau
quantize để chắc chắn không có sai lệch giữa mô phỏng và chip thật.

### 8.1 Cơ sở tham chiếu: MLPerf Inference

MLPerf Inference (do MLCommons xây dựng, hơn 200 kỹ sư từ Google/Meta/Qualcomm/NVIDIA
đóng góp) là benchmark suite chuẩn công nghiệp cho AI inference, dùng cho cả datacenter
lẫn edge. MLPerf chia benchmark thành đúng 4 trục: **accuracy, latency, throughput,
power** - mọi paper benchmark nghiêm túc (kể cả các paper bạn đã có) đều xoay quanh 4
trục này, chỉ khác cách đo cụ thể theo bài toán.

MLPerf cũng định nghĩa 3 kịch bản đo latency khác nhau, áp dụng được vào đề tài PPE của
bạn (chạy 1 camera realtime = kịch bản 1; chạy nhiều camera cùng lúc = kịch bản 2/3):

| Kịch bản | Ý nghĩa | Áp dụng vào đề tài PPE |
|---|---|---|
| Single-stream | 1 request tại 1 thời điểm, đo latency | Camera đơn, xử lý tuần tự từng frame |
| Server | Nhiều request tới theo tốc độ nhất định (QPS), đo latency percentile | Nhiều camera stream vào cùng 1 board |
| Offline | Đo throughput thuần, có batching, không quan tâm latency từng request | Xử lý hàng loạt video đã quay sẵn (không realtime) |

### 8.2 Bảng mẫu các nhóm giá trị benchmark

| Nhóm | Chỉ số cụ thể | Đơn vị | Đo ở đâu | Cách đo trên RK3588 | Paper tham chiếu |
|---|---|---|---|---|---|
| **Accuracy** | mAP@0.5, mAP@0.5:0.95 | % | (A) PC + (B)/(C) board (đo lại để chắc chắn) | So khớp output với ground truth tập test PPE | DAHD-YOLO, ppe_yolo_chv_2021wang |
| | Precision / Recall / F1-score | % | (A) PC | Tính từ confusion matrix | ppe_yolo_chv_2021wang |
| | Accuracy drop sau quantize | % (delta so FP32) | (A) PC, so sánh trước/sau bước 4 | So sánh mAP trước/sau quantize | Quantization Survey (Gholami) |
| **Latency** | Latency trung bình / frame | ms | **(B)/(C) board - bắt buộc** | `time.time()` quanh `rknn.inference()` | Flexer, Layer-Puzzle |
| | Latency percentile (p50/p95/p99) | ms | **(B)/(C) board - bắt buộc** | Đo N lần, sort, lấy phân vị | MLPerf Inference |
| | Time-to-first-result | ms | **(B)/(C) board - bắt buộc** | Từ lúc nhận input tới output đầu | MLPerf Inference (single-stream) |
| **Throughput** | FPS (frame/giây) | fps | **(B)/(C) board - bắt buộc** | 1000/latency hoặc đếm frame/thời gian | DAHD-YOLO (50.2 fps), Eyeriss |
| | Số stream đồng thời tối đa | luồng | **(C) board - bắt buộc** | Tăng dần camera input tới khi FPS tụt | Flexer, Layer-Puzzle |
| **Resource Utilization** | NPU/PE utilization | % | **(B)/(C) board - bắt buộc** | `RKNN_LOG_LEVEL=4`, xem MAC utilization | Eyeriss |
| | Tỷ lệ operator fallback CPU | % số layer | **(B)/(C) board - bắt buộc** | Đếm log layer chạy CPU thay vì NPU | eIQ Neutron, TVM |
| | Peak RAM usage | MB | **(B)/(C) board - bắt buộc** | `free -h` hoặc script theo dõi lúc chạy | MCUNet |
| | Memory bandwidth usage | GB/s | **(B)/(C) board - bắt buộc** | Tool profiling DDR nếu có, hoặc ước lượng | Eyeriss, Flexer |
| **Energy Efficiency** | Công suất tiêu thụ | W | **(B)/(C) board - bắt buộc** | Đo qua adapter có công suất kế | TPU paper (TOPS/W) |
| | Hiệu năng/W | inference/s/W | **(B)/(C) board - bắt buộc** | FPS chia công suất đo được | TPU paper, Eyeriss |
| | Năng lượng/inference | mJ/nJ | **(B)/(C) board - bắt buộc** | Công suất × latency | Eyeriss |
| **Model Efficiency** | Số tham số | triệu (M) | (A) PC | Đếm trực tiếp từ model | MCUNet, DAHD-YOLO |
| | FLOPs / MACs | GFLOPs | (A) PC | Tool `thop`, `ptflops` | DAHD-YOLO |
| | Dung lượng model | MB | (A) PC | So `.onnx` vs `.rknn` sau quantize | Quantization Survey |

### 8.3 Cách trình bày kết quả trước/sau tối ưu

Mỗi bảng kết quả nên có tối thiểu 3 cột: **Baseline (chưa tối ưu)** - **Sau tối ưu** - 
**% cải thiện**, để giám khảo/hội đồng thấy ngay hiệu quả. Ví dụ khung bảng cho báo cáo
cuối:

| Chỉ số | Baseline (FP32, 1 core) | Sau tối ưu (INT8, multi-core) | % cải thiện |
|---|---|---|---|
| mAP@0.5 | ... % | ... % | (ghi rõ nếu giảm, không chỉ khoe phần tăng) |
| Latency trung bình | ... ms | ... ms | ... % |
| FPS | ... | ... | ... % |
| Peak RAM | ... MB | ... MB | ... % |
| Model size | ... MB | ... MB | ... % |

**Lưu ý quan trọng:** luôn báo cáo cả accuracy lẫn performance cùng lúc - chỉ khoe FPS
tăng mà giấu accuracy giảm bao nhiêu là điểm hội đồng/phản biện sẽ hỏi ngay, vì đây
chính là trade-off cốt lõi mà toàn bộ mảng quantization/pruning xoay quanh.
