# MASTER RESEARCH GUIDE
## PPE Detection + Edge AI + Hardware-Aware Optimization trên RK3588S

# 0. Tóm tắt đề tài

## 0.0. Bảng chú giải thuật ngữ

Các thuật ngữ dùng xuyên suốt tài liệu, phân theo nhóm chuyên môn. Nguồn công thức Precision, Recall, F1, mAP: [`docs/papers/07_ppe_detection/shel5k_helmet_2022otgonbold.pdf`](papers/07_ppe_detection/shel5k_helmet_2022otgonbold.pdf), tr.8 (Equation 1-4).

### 0.0.1. Độ đo và Pipeline Computer Vision

| STT | Thuật ngữ | Công thức / Định nghĩa | Ý nghĩa |
|---:|---|---|---|
| 1 | TP / FP / FN | True Positive / False Positive / False Negative | TP: box dự đoán đúng lớp + IoU ≥ ngưỡng. FP: dự đoán sai (lớp sai hoặc IoU thấp). FN: object thật bị bỏ sót |
| 2 | Precision | TP ÷ (TP + FP) | Trong số box mô hình dự đoán, bao nhiêu % là đúng (ít báo nhầm) |
| 3 | Recall | TP ÷ (TP + FN) | Trong số object thật có trong ảnh, mô hình tìm ra được bao nhiêu % (ít bỏ sót) |
| 4 | F1 Score | 2 × (Precision × Recall) ÷ (Precision + Recall) | Trung bình điều hòa Precision/Recall, cân bằng cả 2 |
| 5 | IoU | Diện tích giao ÷ diện tích hợp của 2 box | Đo độ trùng khớp giữa box dự đoán và box ground-truth; ngưỡng 0.5 nghĩa là chồng lấn ≥50% mới tính là đúng |
| 6 | AP | Diện tích dưới đường cong Precision-Recall của 1 class | Độ chính xác tổng hợp cho riêng 1 class, tại 1 ngưỡng IoU |
| 7 | mAP | Trung bình AP qua tất cả class | Độ chính xác tổng thể của mô hình trên toàn bộ class |
| 8 | mAP@0.5 (mAP50) | mAP tính tại ngưỡng IoU = 0.5 | Cách đo phổ biến nhất, khoan dung hơn (chỉ cần chồng lấn 50%) |
| 9 | mAP@0.5:0.95 (mAP50-95) | Trung bình mAP qua các ngưỡng IoU 0.5 → 0.95, bước 0.05 | Khắt khe hơn, phạt cả box lệch vị trí dù đúng lớp; chuẩn COCO |
| 10 | LetterBox | Resize ảnh về khung vuông (vd 640×640) mà không bóp méo | Giữ tỉ lệ khung hình gốc, phần thiếu tô viền màu xám (114, 114, 114) |
| 11 | NMS | Non-Maximum Suppression | Bước hậu xử lý loại bớt các box trùng nhau trên cùng 1 object, giữ box có score cao nhất |

### 0.0.2. Tối ưu hóa mô hình và Lượng tử hóa

| STT | Thuật ngữ | Công thức / Định nghĩa | Ý nghĩa |
|---:|---|---|---|
| 1 | Params | Số tham số học được của model (triệu, M) | Tỉ lệ thuận với dung lượng file model |
| 2 | FLOPs / MACs | Floating-point Operations / Multiply-Accumulate operations | Ước lượng khối lượng tính toán lý thuyết, KHÔNG đồng nghĩa với latency thật trên NPU (mục 1). Ultralytics tính GFLOPs = MACs × 2 (mục 5.2) |
| 3 | PTQ | Post-Training Quantization | Lượng tử hoá model đã train xong (FP32 → INT8), không train lại, chỉ cần 1 bộ ảnh calibration nhỏ |
| 4 | QAT | Quantization-Aware Training | Train lại model có mô phỏng lượng tử hoá ngay trong lúc train để model thích nghi với INT8; tốn công hơn PTQ |

### 0.0.3. Phần mềm và Phần cứng RKNPU Rockchip

| STT | Thuật ngữ | Công thức / Định nghĩa | Ý nghĩa |
|---:|---|---|---|
| 1 | RKNPU2 | Bộ SDK phía board của Rockchip cho NPU: runtime `librknnrt`, `rknn_server`, C API `rknn_api.h` | Không phải package Python; tương ứng thư mục `3rdparty/rknn-toolkit2/rknpu2/` |
| 2 | librknnrt | Thư viện C runtime (`librknnrt.so`) trên board, thực thi model trên NPU | RKNNLite2 gọi trực tiếp; RKNN-Toolkit2 khi điều khiển board từ PC thì đi qua `rknn_server` trên board rồi mới tới thư viện này |
| 3 | RKNN-Toolkit2 | Package Python để convert/quantize model sang `.rknn`, và điều khiển board từ xa để đo | Có bản x86_64 và arm64; project dùng bản x86_64 trên PC, kết nối board qua mạng |
| 4 | RKNNLite2 (`rknn-toolkit-lite2`) | Package Python chạy trên board (bản aarch64), chỉ load và chạy model `.rknn` có sẵn | Không convert/quantize được; tên gần giống RKNN-Toolkit2 nhưng khác hẳn chức năng |
| 5 | core_mask | Tham số chọn core NPU chạy model: tự động (`AUTO`), 1 core (`CORE_0`), hoặc gộp nhiều core (`CORE_0_1_2`) | Đặt lúc gọi `init_runtime()`, không phải lúc build model (`ai/core/rknn/benchmark.py`) |

### 0.0.4. Đánh giá hiệu năng và Hệ thống

| STT | Thuật ngữ | Công thức / Định nghĩa | Ý nghĩa |
|---:|---|---|---|
| 1 | FPS | Frames Per Second | Số ảnh xử lý được mỗi giây. Có 2 loại không so trực tiếp được với nhau: FPS_latency và Throughput FPS (mục 5.3) |
| 2 | P50 / P95 | Percentile 50 (trung vị) / Percentile 95 | Với dãy số đo lặp lại (vd latency): P50 là giá trị ở giữa, 95% số lần đo thấp hơn P95. P95 cho biết mức chậm của những frame chậm, không chỉ trung bình |
| 3 | VmRSS / VmHWM | RAM thật (Resident Set Size) process đang dùng / mức cao nhất từng dùng | Đọc từ `/proc/<pid>/status` trên Linux. Man page `proc_pid_status(5)` ghi về VmHWM: *"This value is inaccurate"*, nên lấy mẫu VmRSS liên tục (mục 5.4) |
| 4 | Golden test | Bài test đối chiếu với số liệu đã lưu | Chạy evaluator trên 1 bộ ảnh và 1 model cố định; ra số khác số đã lưu nghĩa là code evaluator vừa bị đổi (mục 5.0) |

---

## 0.1. Application hiện tại

| | |
|---|---|
| **Bài toán** | Industrial PPE Detection |
| **Class hiện tại** | `person`, `helmet`, `safety_clothes`, `self_clothes`, `head` |

---

## 0.2. Dataset

| Lựa chọn | Trạng thái | Phạm vi | Class | Vì sao |
|---|---|---|---|---|
| 1. SFCHD đơn lẻ | Đang chọn | 5 lớp | `person`<br>`helmet`<br>`safety_clothes`<br>`self_clothes`<br>`head`<br>(lọc từ 7 lớp raw SFCHD, bỏ `blur_head`/`blur_clothes`) | Dataset có sẵn trong repo, không cần gộp. Baseline cũ train 7 lớp, cần train lại 5 lớp |
| 2. Gộp SHEL5K + SFCHD | Cân nhắc | 5 lớp, mapping đề xuất bên dưới | `person`, `helmet`, `head`, `safety_clothes`, `self_clothes` (giống hệt Option 1, chỉ thêm ảnh SHEL5K) | Xem trích dẫn nguồn bên dưới |

**Việc cần làm cho lựa chọn 1:**

- [x] Dataset 5 class `scripts/data/prepare_sfchd_5class.py` → `data/sfchd_5class/processed/` (giữ split 80/10/10 của `sfchd`, cùng thứ tự class với `sfchd_shel5k`)
- [x] Thêm config `ai/automation/configs/sfchd_5class_yolov8n_baseline.yaml` + `sfchd_5class_yolov8s_baseline.yaml`
- [ ] Leaderboard `ai/automation/leaderboards/sfchd_5class.csv`: `ai/automation/run.py` tự tạo khi train run đầu tiên
- [ ] Train lại baseline (yolov8n + yolov8s) trên `sfchd_5class` (mục 8, Phase 2)

**Nguồn cho lựa chọn 2:** [`docs/papers/07_ppe_detection/shel5k_helmet_2022otgonbold.pdf`](papers/07_ppe_detection/shel5k_helmet_2022otgonbold.pdf), Table 2, tr.9 (mục 4.3 "Three-Class Results"):

> So sánh cùng tập ảnh, model YOLOv5x train trên nhãn thiếu sót (SHD) vs nhãn đầy đủ (SHEL5K), lớp Person:
> Precision 0.0345 → 0.9203, Recall 0.0052 → 0.8409, mAP@0.5 **0.03% → 83.11%**.
> mAP@0.5 trung bình 3 lớp (Helmet/Head/Person): 59.50% → 85.28%.

Kết luận của paper (mục 4.3): nhãn Person bị bỏ sót nghiêm trọng trong SHD khiến YOLOv5x gần như không phát hiện được người; bổ sung nhãn đầy đủ trên SHEL5K khắc phục hoàn toàn vấn đề này.

### 0.2.1. Class gốc của từng dataset

**SHEL5K (6 class):**

| Class | Ý nghĩa |
|---|---|
| `helmet` | Mũ bảo hộ — box hẹp, chỉ riêng cái mũ |
| `head` | Đầu trần, không đội mũ — tín hiệu vi phạm |
| `head_with_helmet` | Vùng đầu bao gồm cả mũ — box rộng hơn, lồng với `helmet` |
| `person_with_helmet` | Toàn thân người, có đội mũ |
| `person_no_helmet` | Toàn thân người, không đội mũ — tín hiệu vi phạm |
| `face` | Khuôn mặt (mắt/mũi/miệng) — phục vụ nghiên cứu privacy blur, không phải PPE |

**CHV (6 class) — đã loại khỏi Option 2, xem lý do ở 0.2.2:**

| Class | Ý nghĩa |
|---|---|
| `person` | Toàn thân người, không phân biệt tuân thủ/vi phạm |
| `vest` | Áo phản quang (an toàn) |
| `blue helmet` / `red helmet` / `white helmet` / `yellow helmet` | Mũ bảo hộ theo 4 màu — mã hóa **vai trò công nhân** (chuẩn Build UK), không phải trạng thái tuân thủ |

**SFCHD (7 class raw):**

| Class | Ý nghĩa |
|---|---|
| `person` | Toàn thân người |
| `helmet` | Mũ bảo hộ (an toàn) |
| `safety_clothes` | Áo bảo hộ chống hóa chất (tuân thủ) |
| `self_clothes` | Quần áo thường — tín hiệu vi phạm (paper gọi là "Other Clothing") |
| `head` | Đầu trần, không đội mũ — tín hiệu vi phạm |
| `blur_head` | Vùng đầu bị mờ/nhiễu do camera — lỗi chất lượng ảnh, không phải trạng thái thật |
| `blur_clothes` | Vùng quần áo bị mờ/nhiễu do camera — lỗi chất lượng ảnh, không phải trạng thái thật |

### 0.2.2. Đề xuất Class Mapping cho Lựa chọn 2

Ràng buộc: `ai/core/dataset.py` dùng `dataset.yaml` kiểu Ultralytics chuẩn — flat class list, 1 nhãn/box, không hỗ trợ multi-attribute. Mọi thông tin muốn giữ phải nằm gọn trong 1 tên class duy nhất.

**CHV bị loại khỏi Option 2** (không chỉ trục màu mũ — cả dataset), lý do:
- Trùng ảnh gốc đã xác nhận với SHEL5K (xem cảnh báo bên dưới) — bỏ CHV loại bỏ luôn rủi ro này thay vì phải dedup.
- Pháp lý chưa rõ ràng: license "không ghi rõ" (`data/chv/DATA_CARD.md`). (Số instance thì khớp paper: 9.209.)
- Mất class `vest` (1.784 instance) là mất mát duy nhất — trục màu mũ đã quyết định gộp bỏ từ trước nên không mất thêm gì ở đó.

Nguyên tắc còn lại (cho SHEL5K + SFCHD): giữ trục dù chỉ 1 dataset đóng góp nếu đó là tín hiệu vi phạm cốt lõi (`self_clothes`); bỏ trục không phục vụ compliance (`face`) hoặc box lồng gây nhiễu (`head_with_helmet`).

Số liệu đếm trực tiếp từ `data/<name>/processed/labels/` (không phải số paper báo cáo).

**5 class cuối (giống hệt Option 1):**

| Class cuối | Nguồn → instance | Tổng | Ghi chú |
|---|---|---:|---|
| `person` | SFCHD.person 17.009 + SHEL5K.person_with_helmet 14.767 + SHEL5K.person_no_helmet 5.248 | 37.024 | Gộp bỏ trạng thái with/no_helmet của SHEL5K |
| `helmet` | SFCHD.helmet 14.297 + SHEL5K.helmet 19.252 | 33.549 | |
| `head` | SFCHD.head 1.199 + SHEL5K.head 6.120 | 7.319 | Đầu trần không mũ, tín hiệu vi phạm |
| `safety_clothes` | SFCHD.safety_clothes 14.812 | 14.812 | Chỉ SFCHD |
| `self_clothes` | SFCHD.self_clothes 779 | 779 | Chỉ SFCHD, vi phạm quần áo — giữ dù ít mẫu vì là tín hiệu vi phạm trực tiếp |
| **Tổng cộng** | | **93.483** | |

**Bằng chứng giữ `self_clothes` dù ít mẫu:** [`docs/papers/07_ppe_detection/sfchd_scale_2023yu.pdf`](papers/07_ppe_detection/sfchd_scale_2023yu.pdf), Table V, tr.10 — paper tự gọi `self_clothes` là "Other Clothing", benchmark YOLOv5 đạt AP(50:95) **0.549**, cao hơn cả `Head` (0.507), dù mẫu ít hơn nhiều. Paper viết nguyên văn (tr.9):

> "despite their limited proportion within the dataset, the pronounced divergence in their features from the Safety Clothing and Safety Helmet facilitates the network's capability to distinguish and assimilate these variations."

**Bị loại khỏi taxonomy:**

| Bị loại | Nguồn | Instance | Lý do |
|---|---|---:|---|
| CHV (toàn bộ, gồm `vest` + 4 màu mũ + `person`) | CHV | 9.209 | Loại cả dataset — xem lý do ở trên |
| `person_with_helmet`/`person_no_helmet` riêng | SHEL5K | đã gộp vào `person` | Chỉ SHEL5K có trạng thái này, SFCHD không suy ra được mà không đoán |
| `head_with_helmet` | SHEL5K | 16.048 | Box lồng gần trùng với `helmet`, gây nhiễu NMS/loss nếu tách riêng |
| `face` | SHEL5K | 14.135 | Không liên quan PPE compliance |
| `blur_head` / `blur_clothes` | SFCHD | 1.133 / 1.323 | Ảnh nhiễu/mờ do camera, không phải object class thật |

**Tổng sau gộp:** ~93.483 instance qua 5 class, từ 2 dataset ~17.372 ảnh (SHEL5K 5.000 + SFCHD 12.372).

**Rủi ro trùng ảnh SHEL5K×SFCHD: đã verify, không trùng.** Chạy perceptual hash (dHash 64-bit, toàn bộ 5.000 ảnh SHEL5K × 12.372 ảnh SFCHD = 61,86 triệu phép so sánh, threshold hamming ≤5) → **0 cặp trùng**. Khớp với dự đoán ban đầu (nguồn gốc khác hẳn: SHEL5K từ ảnh công trường/stock photo, SFCHD từ camera giám sát 2 nhà máy hóa chất) — không cần dedup bước này khi hiện thực.

**Việc cần làm để hiện thực:**

- [x] `data/CLASS_MAPPING.md`
- [x] Script gộp `scripts/data/prepare_sfchd_shel5k.py` → `data/sfchd_shel5k/processed/`
- [x] Thêm config `ai/automation/configs/sfchd_shel5k_yolov8n_baseline.yaml` + `sfchd_shel5k_yolov8s_baseline.yaml`
- [x] Danh sách ảnh test riêng của SHEL5K `data/sfchd_shel5k/processed/test_shel5k.txt` (500 ảnh, eval set `shel5k_test`), do `prepare_sfchd_shel5k.py` sinh ra
- [ ] Leaderboard `ai/automation/leaderboards/sfchd_shel5k.csv`: `ai/automation/run.py` tự tạo khi train run đầu tiên
- [ ] Train lại baseline (yolov8n + yolov8s) trên `sfchd_shel5k` (mục 8, Phase 2)

---

## 0.3. Hardware

| Item | Giá trị |
|---|---|
| Board | Orange Pi 5 |
| SoC | RK3588S |
| RAM | 4 GB (hệ điều hành thấy 3,916 MiB) |
| Accelerator | RKNPU2, driver 0.9.8 |
| OS / Kernel | Orange Pi 1.2.4 Jammy (Ubuntu 22.04.5) / 6.1.99-rockchip-rk3588 |
| RKNN-Toolkit2 / RKNNLite2 / librknnrt | 2.3.2 |
| Camera | OV13855, NV12, 1920×1080 |
| Model input | 640×640 |

RKNN-Toolkit2/librknnrt 2.3.2 đã verify thật trên board qua `get_sdk_version()` (xem `tmp/04_debug-logs/2026-09-18_board-bringup-log.md`). RKNNLite2 2.3.2, driver RKNPU 0.9.8, OS, RAM đọc trực tiếp trên board ngày 2026-09-26 (log `init_runtime` của RKNNLite2: `RKNN Driver Information, version: 0.9.8`; `get_sdk_version()`: `API: 2.3.2`, `DRV: 0.9.8`).

Model input 640×640 là default Ultralytics (paper SHEL5K không nêu kích thước input khi train/test). Paper SFCHD tự dùng 1333×800 ([`sfchd_scale_2023yu.pdf`](papers/07_ppe_detection/sfchd_scale_2023yu.pdf), tr.9: *"the image size was adjusted to 1333 \* 800"*) nên baseline hiện tại không so trực tiếp được với số của paper SFCHD.

Đầy đủ + các thông số còn `[TBD]` (cooling, ambient condition): xem [Table C](#table-c-hardware--software-environment) ở mục 7.

---

# 1. Đề tài không nên dừng ở mức “YOLO chạy trên Orange Pi”

Nếu chỉ phát biểu:

> “Dùng YOLO để phát hiện PPE trên Orange Pi 5.”

thì đó chủ yếu là **application / implementation**, chưa phải một research problem đủ rõ.

Hướng nghiên cứu mạnh hơn:

> **Hardware-aware optimization of a lightweight PPE detector for real-time inference on RK3588S NPU**

Có thể hiểu đề tài nằm ở giao của hai phía:

```text
A. Computer Vision / PPE Detection
   - person / helmet / head / safety_clothes / self_clothes
   - small objects
   - multi-scale
   - low-light
   - occlusion
   - detection accuracy

                       +

B. Edge AI / Hardware-aware Optimization
   - RK3588S NPU
   - FP16 / INT8
   - quantization
   - pruning
   - operator compatibility
   - latency / FPS / memory
   - compiler/runtime behavior
   - accuracy-efficiency trade-off
```

Trong định hướng hiện tại:

> **B là trọng tâm hơn một chút, A là bài toán ứng dụng và quality constraint.**

Tiền lệ thật cho hướng này: [`docs/papers/05_rk3588/dahd_yolo_rk3588_2025.pdf`](papers/05_rk3588/dahd_yolo_rk3588_2025.pdf), Table 6, tr.18 — DAHD-YOLO (dựa trên YOLOv8s) triển khai thật trên chính RK3588. Paper viết nguyên văn:

> "the INT8 optimized model's single-thread inference time per frame is 0.1162 s, which is insufficient for real-time surveillance camera monitoring at 25 frames per second [...] By utilizing a thread pool for acceleration, we optimize the entire detection process through multithreading."

Số liệu Table 6 (nguyên văn từ paper): DAHD-YOLO INT8 — Size 8.8M, FPS 720P **50.2**/1080P 43.8/1440P 37.7, mAP50 74.36%, Inference-Time 79.1ms, Power 7W. Tức đơn luồng 1 core (0.1162s/frame ≈ 8.6 FPS) không đủ real-time; multi-thread khai thác 3 NPU core đưa lên 50.2 FPS.

Tư tưởng cốt lõi cần giữ xuyên suốt:

> **Model ít FLOPs hoặc ít parameters chưa chắc chạy nhanh hơn trên NPU. Hiệu quả thật phải được đo trực tiếp trên target hardware.**

Bằng chứng: [`docs/papers/00_overview/edge_ai_survey_2025wang.pdf`](papers/00_overview/edge_ai_survey_2025wang.pdf), Table 6 ("Accuracy and Inference Time for PyTorch Mobile on Different Devices"), tr.21 — số liệu thô nguyên văn trong bảng, cùng 1 model InceptionV3 (cùng trọng số, accuracy giữ nguyên 77.82%/77.82%/77.82%/77.82%/77.68% qua 5 thiết bị):

| Thiết bị | Galaxy S10e | Honor V20 | Vivo X27 | Vivo Nex | Oppo R17 |
|---|---:|---:|---:|---:|---:|
| Time (ms) | 433 | 401 | 1509 | 1500 | 1537 |

Cùng kiến trúc, cùng trọng số, accuracy không đổi — nhưng độ trễ chênh lệch tới **3,8 lần** (401ms → 1537ms) chỉ vì đổi chip.

---

# 2. Từ application thành research problem

## 2.1. Research problem đề xuất

Các object detector có thể đạt accuracy tốt, nhưng khi triển khai real-time trên Edge NPU, hiệu quả thực tế còn phụ thuộc vào:

```text
operator support → Mức độ NPU hỗ trợ các phép toán của model như Conv, Add, Resize...

tensor layout → Cách tensor được sắp xếp trong memory, ví dụ NCHW/NHWC.

datatype → Kiểu dữ liệu của model, ví dụ FP32, FP16, INT8.

memory access → Cách model đọc/ghi dữ liệu từ memory trong lúc inference.

memory copy → Việc copy dữ liệu giữa các buffer; copy nhiều sẽ làm tăng latency.

compiler optimization → Các bước compiler tối ưu graph, operator, layout và memory trước khi chạy trên NPU.

NPU architecture → Kiến trúc phần cứng của NPU quyết định loại phép toán nào chạy hiệu quả.

pre/post-processing overhead → Thời gian ngoài inference, như resize, color conversion, NMS, decode output...
```

3 yếu tố dưới đây đã có bằng chứng thật trên chính model/board của project (không phải trích paper ngoài):

| Yếu tố | Phát hiện thật | Nguồn |
|---|---|---|
| `operator support` | `Convolution` hỗ trợ đa nhân ("多核联合: 支持"), nhưng **`Resize`** (upsample trong neck YOLO) **không** ("不支持"), và **`ConvolutionSwish`** (Conv + SiLU gộp) **tạm chưa** ("暂不支持"). Chỉ các biến thể Conv + ReLU/Clip/LeakyReLU mới hỗ trợ. YOLOv8 dùng SiLU sau hầu hết lớp conv (228 op `ConvExSwish` trong build log của model 7 class cũ) | [`03_RKNN_Compiler_Support_Operator_List_V2.3.2.pdf`](papers/05_rk3588/01_vendor_docs/03_rknn_npu/03_RKNN_Compiler_Support_Operator_List_V2.3.2.pdf), mục 3.2 RK3588: 3.2.5 Convolution (trang PDF 59), 3.2.17 ConvolutionSwish (trang PDF 63), 3.2.54 Resize (trang PDF 87) |
| `compiler optimization` | Operator đã được compiler tự gộp thật: 228 op `ConvExSwish` (Conv + SiLU gộp làm 1), cờ `conv_eltwise_activation_fuse = 1` mặc định bật | Build log thật của model `sfchd` YOLOv8n (model 7 class cũ, cần đo lại sau khi train 5 class), `tmp/05_training-logs/2026-09-18_sfchd_yolov8n_rknn_build_verbose_loglevel3.log` (cờ ở dòng 154) |
| `datatype` | Trên RK3588 chỉ dùng được `w8a8` (INT8/INT8, mặc định). Các mode khác đều giới hạn chip: `w4a16` chỉ RK3576/RV1126B, `w8a16` chỉ RK3562, `w16a16i` chỉ RV1103/RV1106, `w4a8` chưa hỗ trợ | [`01_Rockchip_RKNPU_API_Reference_RKNN_Toolkit2_V2.3.2_EN.pdf`](papers/05_rk3588/01_vendor_docs/03_rknn_npu/01_Rockchip_RKNPU_API_Reference_RKNN_Toolkit2_V2.3.2_EN.pdf), hàm `config`, tham số `quantized_dtype`, tr.7 |

Tài liệu Rockchip thứ 2 cho cùng kết luận về đa nhân: [`02_Rockchip_RKNPU_User_Guide_RKNN_API_V1.5.2_EN.pdf`](papers/05_rk3588/01_vendor_docs/03_rknn_npu/02_Rockchip_RKNPU_User_Guide_RKNN_API_V1.5.2_EN.pdf), trang PDF 27, nguyên văn:

> "For multi-cores mode (when enabling RKNN_NPU_CORE_0_1 and RKNN_NPU_CORE_0_1_2), the following ops have better acceleration: Conv, DepthwiseConvolution, Add, Concat, Relu, Clip, Relu6, ThresholdedRelu. Prelu, LeakyRelu. Other type of op will fallback to Core0 to continue running."

Lưu ý: log gọi op là `ConvExSwish`, tài liệu gọi `ConvolutionSwish`. Hai tên cùng chức năng (Conv + Swish gộp) nhưng không tài liệu nào xác nhận là cùng một op. Cần chạy `eval_perf` ở `CORE_0_1_2` trên board để xem từng layer thực sự chạy trên core nào `[chưa kiểm chứng]`.

Do đó:

```text
low FLOPs ≠ low latency
small model ≠ fast model on NPU
```

Minh hoạ nhẹ trên chính model `sfchd` YOLOv8n (model 7 class cũ, cần đo lại sau khi train 5 class; nguồn: build log `tmp/05_training-logs/2026-09-18_sfchd_yolov8n_rknn_build_verbose_loglevel3.log`, dòng 331, cột `Cycles(DDR/NPU/Total)` = `52317/51200/52317`):

| Layer | NPU cycles | DDR cycles | Tỉ lệ DDR/NPU |
|---|---:|---:|---:|
| `model.4/cv2/conv` | 51.200 | 52.317 | **1.022** |

NPU cycles = thời gian tính toán; DDR cycles = thời gian chờ đọc/ghi RAM. Ở các layer khác NPU cycles luôn cao hơn (tính toán là nút thắt). Riêng layer này DDR cycles cao hơn — nút thắt là di chuyển dữ liệu, không phải khối lượng tính toán.

---

## 2.2. Research Question

> **Làm thế nào giữ PPE detection accuracy ở mức tốt nhưng đồng thời cải thiện inference efficiency trên RK3588S NPU?**

---

# 3. Form nghiên cứu nên follow

## 3.1. Các bước của một nghiên cứu (thứ tự trình bày trong paper)

Một flow nghiên cứu hợp lý:

1. **Problem** → Xác định vấn đề thực tế cần giải quyết.

2. **Literature Review** → Đọc paper để biết người khác đã làm gì và còn hạn chế gì.

3. **Research Gap** → Xác định phần chưa được giải quyết tốt trong các nghiên cứu trước.

4. **Baseline** → Chọn model/phương pháp ban đầu làm mốc so sánh.

5. **Measurement / Bottleneck Analysis** → Đo accuracy và hardware performance để tìm bottleneck thật.

6. **Proposed Method** → Đề xuất giải pháp dựa trên bottleneck đã tìm được.

7. **Experimental Setup** → Mô tả dataset, training, hardware và cách đo để thí nghiệm có thể tái lập.

8. **Comparison** → So sánh proposed method với baseline và các phương pháp khác.

9. **Ablation Study** → Tách từng thành phần để biết phần nào thật sự tạo ra cải tiến.

10. **Hardware Deployment** → Chạy trên hardware thật và kiểm tra trong tình huống thực tế.

11. **Discussion** → Phân tích kết quả, nguyên nhân, ưu điểm và limitation.

12. **Contribution / Conclusion** → Tổng kết đóng góp, kết quả đạt được và hướng phát triển tiếp theo.

Lưu ý: thứ tự 12 bước trên là thứ tự trình bày trong paper/báo cáo cuối cùng (khớp mục 11 "Structure paper"). Thứ tự thực hiện nghiên cứu thật khác — xem mục 3.2 và mục 4.2: Baseline/Measurement phải làm trước, Research Gap xác định sau khi đã đo thật, không phải ngược lại.

## 3.2. Thứ tự thực hiện thật

Điểm quan trọng nhất:

> **Không nên chọn giải pháp trước rồi mới đi tìm lý do để biện minh.**

Flow nên là:

```text
Đọc literature
   ↓
Reproduce / benchmark baseline
   ↓
Đo trên RK3588S
   ↓
Tìm bottleneck thật
   ↓
Xác định research gap
   ↓
Mới chọn optimization method
```

---

# 4. Research Gap phải được tìm như thế nào?

## 4.1. Sai cách

```text
“Tôi muốn thêm attention”
   ↓
“Tôi muốn pruning”
   ↓
“Tôi muốn INT8”
   ↓
sau đó mới tìm problem để giải thích
```

## 4.2. Đúng cách

```text
Đọc paper
   ↓
Liệt kê limitation
   ↓
Tìm limitation lặp lại
   ↓
Verify limitation trên RK3588S
   ↓
Tìm bottleneck thật
   ↓
Đặt research question
   ↓
Chọn contribution
```

## 4.3. Ví dụ gap có thể xuất hiện sau benchmark

### Case A — FP16 còn chậm

```text
YOLOv8n
   ↓
accuracy tốt
   ↓
deploy RK3588S thành công
   ↓
nhưng
   ↓
NPU latency còn cao
```

Hướng tối ưu có thể cân nhắc:

```text
architecture optimization
→ Tối ưu cấu trúc model để giảm compute nhưng vẫn giữ accuracy.

operator-aware redesign
→ Chỉnh model theo các operator mà RK3588S NPU hỗ trợ và xử lý tốt.

structured pruning
→ Cắt bỏ nguyên channel/filter/block ít quan trọng để model thật sự nhẹ hơn.

lighter detection head
→ Làm phần đầu ra dự đoán bbox/class của YOLO đơn giản và nhẹ hơn.

input-resolution optimization
→ Chọn kích thước input phù hợp để cân bằng accuracy và latency.
```

Bằng chứng RK3588-relevant: [`docs/papers/06_nas/s3nas_npu_aware_2020lee.pdf`](papers/06_nas/s3nas_npu_aware_2020lee.pdf), Table 6, tr.10. Paper viết nguyên văn về **Selective SE Removal**:

> "Finally, we selectively removed SE blocks from ours-XL+, resulting in ours-XL-rmSE+. [...] After removing SE blocks from ours-XL+ based on the metric, only about 60% of the blocks in the network have SE blocks. As a result, we could make the latency shorter, while the accuracy was slightly improved than ours-XL+. This model achieves 82.72% top-1 accuracy with only 11.66ms latency."

Tức bỏ bớt SE blocks (tốn băng thông bộ nhớ, không khai thác tốt mảng PE của NPU) giúp model **vừa nhanh hơn vừa chính xác hơn** cùng lúc — không phải đánh đổi.

**`architecture optimization` — Linear Depth Scaling:** cùng paper S3NAS, Table 4, tr.9 (dồn nhiều block hơn vào stage sâu, nơi feature map nhỏ nhưng số kênh lớn):

| Cách chia block | Accuracy | Latency |
|---|---:|---:|
| Constant depth (baseline) | 75.85% | 1.28 ms |
| Linear depth | **77.09%** | 1.24 ms |

> "As shown in Table 4, a supernet with linear depth outperforms a supernet with constant depth in terms of accuracy with similar latency. It confirms that this simple change of block assignment in supernet gives notable accuracy boost with the same latency constraint, without any additional optimization techniques."

**`operator-aware redesign` — structural reparameterization:** [`docs/papers/05_rk3588/dahd_yolo_rk3588_2025.pdf`](papers/05_rk3588/dahd_yolo_rk3588_2025.pdf), tr.6, Figure 2 (train dùng nhiều nhánh, inference gộp về 1 conv chuẩn mà NPU hỗ trợ tốt):

> "DBB has six transformation methods, which correspond to transforming conv-BN, branch addition, sequential convolutions, depth concatenation, and average pooling into a single convolutional layer, respectively."

Lưu ý: bản thân phép gộp không tốn thêm chi phí lúc inference, nhưng module DBCA đầy đủ của DAHD-YOLO còn kèm attention (CAA) — xem Case C, cả model vẫn chậm hơn YOLOv8s. Phải đo trên board, không suy từ lý thuyết.

Giả thuyết cụ thể cho đề tài (xem bảng mục 2.1): đổi activation SiLU của YOLOv8 sang ReLU hoặc LeakyReLU, vì theo tài liệu Rockchip chỉ Conv + ReLU/Clip/LeakyReLU mới được tăng tốc khi chạy nhiều core, còn Conv + Swish thì không. Cần đo 2 thứ: latency ở `CORE_0_1_2` trước và sau khi đổi, và mAP có giảm không (phải train lại) `[chưa kiểm chứng]`.

**`lighter detection head`:** [`docs/papers/07_ppe_detection/ppe_yolo_chv_2021wang.pdf`](papers/07_ppe_detection/ppe_yolo_chv_2021wang.pdf), Table 4, tr.12 (mục 3.2 "Different Layers"):

| Model | mAP | Time GPU |
|---|---:|---:|
| YOLO v3 (3 layers) | **82.65%** | **27.15 ms** |
| YOLO v3 (5 layers) | 81.99% | 37.04 ms |

> "In theory, the model with more layers has a stronger ability to detect small objects. However, the results show that the YOLO v3 (3 layers)'s mAP is only slightly higher than YOLO v3 (5 layers)'s. [...] In experiments, YOLO v3 (three layers) needs 27.25 ms to process an image on GPU, which is 27% faster than YOLO v3 (five layers)."

Tức thêm detection layer không tăng accuracy mà còn chậm hơn 27% — ủng hộ hướng head nhẹ hơn. (Paper ghi 27.25 ms trong văn bản nhưng 27.15 ms trong bảng — sai khác nhỏ ngay trong bản gốc.)

### Case B — INT8 nhanh nhưng accuracy giảm

```text
FP16
   ↓
INT8 PTQ
   ↓
latency giảm
   ↓
nhưng
   ↓
AP_helmet / AP_safety_clothes giảm mạnh
```

Hướng tối ưu có thể cân nhắc:

```text
better calibration
→ Chọn calibration dataset đại diện tốt hơn để INT8 giữ accuracy tốt hơn.

QAT
→ Train model có mô phỏng quantization để model thích nghi với INT8.

mixed precision
→ Không ép mọi layer dùng cùng precision; layer nhạy có thể giữ FP16, layer khác dùng INT8.

quantization-sensitive layer analysis
→ Phân tích layer nào bị giảm accuracy nhiều khi quantize để xử lý riêng.
```

Bằng chứng: [`docs/papers/02_quantization/quantization_survey_2021gholami.pdf`](papers/02_quantization/quantization_survey_2021gholami.pdf), Figure 7, tr.12. Bảng số liệu ở công nghệ 45nm: phép cộng INT8 (8b Add) tốn **0,03 pJ / 36 µm²**, phép cộng FP32 (32b FP Add) tốn **0,9 pJ / 7700 µm²** — INT8 rẻ hơn **30 lần năng lượng, ~214 lần diện tích**. Paper viết nguyên văn kết luận từ số liệu này:

> "As one can see, lower precision provides exponentially better energy efficiency and higher throughput."

Đây là lý do NPU luôn thiên về precision thấp, không chỉ vì giảm bộ nhớ.

Các hướng cứu accuracy ở trên, đối chiếu với thực tế RKNN-Toolkit2 trên RK3588 (Toolkit2-API = [`01_Rockchip_RKNPU_API_Reference_RKNN_Toolkit2_V2.3.2_EN.pdf`](papers/05_rk3588/01_vendor_docs/03_rknn_npu/01_Rockchip_RKNPU_API_Reference_RKNN_Toolkit2_V2.3.2_EN.pdf)):

| Hướng | Thực tế trên RKNN-Toolkit2 |
|---|---|
| `better calibration` | DAHD-YOLO dùng 200 ảnh calibration, [`dahd_yolo_rk3588_2025.pdf`](papers/05_rk3588/dahd_yolo_rk3588_2025.pdf) tr.18: *"We establish a calibration set, comprising 200 randomly selected images from the training data"* |
| `mixed precision` | API thật: `hybrid_quantization_step1` / `hybrid_quantization_step2` (Toolkit2-API mục 2.12, trang PDF 20) |
| Quantize theo channel | Đã là mặc định, không cần làm thêm. Toolkit2-API trang PDF 8: *"quantized_method: Currently support layer, channel or group{SIZE}. The default value is channel."* |

Chú thích "quantize theo channel": khi quantize trọng số 1 layer conv, cần chọn khoảng giá trị (clipping range) để map sang INT8.
- **Theo layer (layerwise)**: cả layer dùng chung 1 khoảng → filter nào có giá trị dao động hẹp sẽ bị mất độ chính xác, vì khoảng chung bị kéo rộng theo filter có giá trị dao động rộng nhất.
- **Theo channel (channelwise)**: mỗi filter có khoảng riêng → giữ độ chính xác cho từng filter, chi phí gần như không đáng kể.

[`quantization_survey_2021gholami.pdf`](papers/02_quantization/quantization_survey_2021gholami.pdf), Figure 3, tr.6, nguyên văn:

> "In layerwise quantization, the same clipping range is applied to all the filters that belong to the same layer. This can result in bad quantization resolution for the channels that have narrow distributions [...]. One can achieve better quantization resolution using channelwise quantization that dedicates different clipping ranges to different channels."

### Case C — FLOPs thấp nhưng NPU vẫn chậm

```text
Model A
   ↓
FLOPs thấp

nhưng

operator/layout/memory behavior
   ↓
RKNN/NPU xử lý không hiệu quả
   ↓
latency cao
```

Đây là dạng gap rất hợp với hướng **hardware-aware**.

Bằng chứng trên đúng RK3588: [`docs/papers/05_rk3588/dahd_yolo_rk3588_2025.pdf`](papers/05_rk3588/dahd_yolo_rk3588_2025.pdf), GFLOPs từ Table 4 (tr.15), FPS từ Table 6 (tr.18):

| Model | GFLOPs | Size | FPS 720P trên RK3588 (INT8) |
|---|---:|---:|---:|
| YOLOv8s | 28.4 | 12.6M | **70.9** |
| DAHD-YOLO | 21.8 (−23,2%) | 8.8M | **50.2** |

DAHD-YOLO ít FLOPs hơn 23% và nhỏ hơn 30%, nhưng chạy chậm hơn ~29% trên NPU thật. Lưu ý: mức 50.2 FPS dẫn ở mục 1 là nhờ multi-thread 3 core; bản thân thay đổi kiến trúc của DAHD-YOLO lại làm model chậm hơn YOLOv8s gốc.

Chiều ngược lại cũng đúng — model nhiều FLOPs/params hơn vẫn có thể chạy nhanh hơn trên NPU. [`docs/papers/06_nas/s3nas_npu_aware_2020lee.pdf`](papers/06_nas/s3nas_npu_aware_2020lee.pdf), tr.9 (so sánh `ours-M` với EfficientNet-B1 trên NPU MIDAP), nguyên văn:

> "Note that the number of parameters and the number of FLOPS in ours-M is larger than EfficientNet-B1. It implies that the complexity of the network is not a direct indicator of the end-to-end latency of the network. The end-to-end latency depends on the NPU architecture, and the proposed NAS technique could find a larger network with shorter latency by adding the latency factor to the loss function directly."

---

# 5. Bốn nhóm metric bắt buộc

## 5.0. Evaluation Protocol v1

Mọi model (FP32 hay INT8, Lựa chọn 1 hay 2, baseline hay model đề xuất) phải đo qua **cùng 1 evaluator** với tham số khoá ở các mục 5.1 đến 5.4. Khác biệt duy nhất giữa 2 lần đo là model.

Quy tắc khoá:

- Protocol có số phiên bản, hiện là **v1**. Mọi kết quả lưu kèm phiên bản protocol và git commit của evaluator.
- **Golden test**: evaluator chạy trên 1 bộ ảnh và 1 model cố định phải ra đúng số đã lưu. Sửa code làm lệch số thì test báo lỗi.
  - Model cố định: `yolov8n.pt` chính thức của Ultralytics (ai cũng tải lại được, kiểm bằng sha256). Model này train trên COCO nên mAP trên PPE không có ý nghĩa; chỉ cần số không đổi.
  - Bộ ảnh: eval set `sfchd_test` (1,238 ảnh), kiểm cả dấu vân tay dataset. Chạy trên CPU vì GPU có thể lệch ở chữ số thứ 4 giữa các máy. Sai khác cho phép: 0.0005 trên mỗi metric.
  - Số đã lưu: `ai/automation/golden/evaluator_v1.json`. Lệnh: `make golden-test` (khoảng 3 phút).
- **Kiểm chéo**: evaluator và `model.val()` (cùng `rect=False`) trên cùng weights phải lệch không quá 0.001 trên mọi metric. Lệnh: `make crosscheck RUN=<run_id>` (ghi `runs/<run_id>/eval/crosscheck_sfchd_test.json`). Đã chạy với model 7 class cũ (`2026-09-17_sfchd_yolov8n_baseline_100ep`) trên `sfchd_test`: 24 metric lệch lớn nhất 0.0001.
- Code: `ai/core/evaluator.py` (protocol), `ai/core/backends.py` (PyTorch/ONNX/RKNN), `ai/automation/check_evaluator.py` (golden, kiểm chéo).
- Đổi bất kỳ tham số nào thì lên phiên bản mới (v2) và đo lại toàn bộ model đang so sánh. Không đặt số của 2 phiên bản khác nhau trong cùng 1 bảng. Chỉ thêm metric mới mà không đổi số cũ thì lên phiên bản phụ (v1.1).

## 5.1. AI Quality

```text
Precision
Recall
mAP50
mAP50-95
AP_person
AP_helmet
AP_head
AP_safety_clothes
AP_self_clothes
ΔmAP khi quantize = mAP (FP32) - mAP (INT8), kèm ΔAP từng class
```

`AP_head` và `AP_self_clothes` là 2 tín hiệu vi phạm trong 5 class đã chốt (mục 0.1). ΔmAP là metric trực tiếp của Case B (mục 4.3).

**Cách đo (khoá v1)**, theo mặc định val của Ultralytics 8.4.154, đã kiểm trong `.venv`:

| Tham số | Giá trị |
|---|---|
| Tập đánh giá | eval set `sfchd_test` (1,238 ảnh) cho mọi model; thêm `shel5k_test` (500 ảnh) cho model Lựa chọn 2 |
| Resize | Resize cạnh dài về 640, rồi LetterBox 640×640 vuông (`rect=False`), không phóng to thêm, căn giữa, viền màu 114 |
| NMS | conf 0.001, IoU 0.7, max_det 300, tính riêng từng class, 1 box có thể mang nhiều class (`multi_label=True`) |
| mAP | IoU 0.50 đến 0.95 bước 0.05, AP nội suy 101 điểm (chuẩn COCO) |
| Precision / Recall | lấy tại ngưỡng conf cho F1 trung bình lớn nhất |
| Model `.rknn` (FP16/INT8) | Inference chạy trên board bằng RKNNLite với đúng input của evaluator; NMS và AP chạy trên PC bằng cùng code như FP32 |

Nguồn trong `.venv/lib/python3.12/site-packages/ultralytics/`: `cfg/default.yaml` (conf, iou, max_det), `data/base.py` `load_image` (resize cạnh dài), `data/dataset.py` dòng 320 (LetterBox khi val), `models/yolo/detect/val.py` `postprocess` (`multi_label=True`), `utils/metrics.py` (`compute_ap`: *"101-point interp (COCO)"*; `ap_per_class`: *"max-F1 precision, recall"*).

**Accuracy của `.rknn`:** `ai/board/infer_dump.py` chạy trên board, ghi output thô của mọi anchor có score lớn nhất > 0.001 (anchor khác không thể qua NMS ở conf 0.001, nên không mất thông tin) kèm md5 input từng ảnh; PC đọc lại bằng `RknnDumpBackend`, kiểm md5 trùng input của evaluator, rồi NMS và AP như FP32. Không gọi `rknn.inference()` từ PC qua `rknn_server`: đo ngày 2026-09-26 qua Tailscale, 1 ảnh FP16 mất khoảng 35 s (trên board 42 ms), tức khoảng 12 giờ cho 1,238 ảnh. Kiểm đường đo mới với model nháp: FP16 ra mAP50-95 0.3677 so với FP32 0.3669.

**Khác với `model.val()` mặc định:** gọi `model.val()` trên file `.pt` thì Ultralytics tự bật ảnh chữ nhật (`engine/model.py` dòng 633: `custom = {"rect": True}`), còn với model đã export (`.onnx`, `.rknn`) thì tắt (`engine/validator.py`: `self.args.rect = False`). Nếu dùng `model.val()` nguyên bản, FP32 và INT8 sẽ khác nhau cả ở cách resize chứ không chỉ ở model. NPU chỉ nhận input vuông 640×640, nên protocol v1 khoá `rect=False` cho mọi backend. Vì vậy số của `model.val()` in ra lúc train (thư mục `plots/`) không dùng để điền bảng.

Lý do: đây là cách tính chuẩn COCO, và các paper trong `docs/papers/` đều báo mAP theo kiểu này, không đặt ngưỡng conf triển khai. Precision/Recall tại ngưỡng conf dùng khi báo vi phạm trên camera sẽ thêm ở v1.1, sau khi chốt ngưỡng đó.

## 5.2. Model Complexity

```text
Parameters (model đã fuse Conv + BN)
GFLOPs ở 640×640
MACs = GFLOPs / 2
Model size: file .onnx (FP32) và file .rknn (chạy trên board)
```

**Cách đo (khoá v1):**

- Tính trên model đã fuse, vì Ultralytics tự fuse trước khi export: build log dòng 2 ghi `Model summary (fused)`.
- GFLOPs lấy từ hàm `get_flops` của Ultralytics, công thức `thop.profile(...)[0] / 1e9 * 2` (số MACs nhân 2). Hàm này trả về 0.0 khi lỗi mà không báo gì, nên evaluator phải chặn trường hợp GFLOPs = 0.
- Không dùng kích thước file `.pt`: Ultralytics lưu `best.pt` ở FP16 (`strip_optimizer`: `x["model"].half()  # to FP16`).
- Code: `ai/automation/complexity.py` (`make complexity RUN=<run_id>`), báo lỗi nếu GFLOPs = 0.

## 5.3. Hardware Performance

```text
Pre-processing latency
Pure NPU inference latency (1 frame)
Post-processing latency
End-to-end latency
FPS_latency = 1000 / E2E mean (tầng 2); từ tầng 1 thì = 1000 / NPU latency, ghi rõ tầng
Throughput FPS (đo trên pipeline thật, ghi rõ số context/luồng và core_mask)
```

Hai loại FPS đo 2 thứ khác nhau, không đặt cạnh nhau như cùng một loại:

- **FPS_latency**: suy từ latency 1 frame. Latency đo bằng `rknn.eval_perf()` khi board kết nối PC; `fix_freq=True` (mặc định) cố định tần số phần cứng để đo lặp lại được ([`01_Rockchip_RKNPU_API_Reference_RKNN_Toolkit2_V2.3.2_EN.pdf`](papers/05_rk3588/01_vendor_docs/03_rknn_npu/01_Rockchip_RKNPU_API_Reference_RKNN_Toolkit2_V2.3.2_EN.pdf), API `eval_perf`, trang PDF 18).
- **Throughput FPS**: số frame/giây của cả pipeline khi chạy nhiều context/luồng song song. Ví dụ DAHD-YOLO ([`dahd_yolo_rk3588_2025.pdf`](papers/05_rk3588/dahd_yolo_rk3588_2025.pdf), tr.18): latency 1 ảnh 79.1 ms nhưng báo 50.2 FPS (trong khi 1000 / 79.1 ≈ 12.6), vì FPS đo với thread pool 3 core. Paper nguyên văn:

> "In Table 6, benefiting from the efficient scheduling of the NPU under the thread pool, the inference latency of the quantized model for a single image with a resolution of 1280 × 720 reaches 79.1 ms."

**Cách đo (khoá v1)**, chia 2 tầng:

| Tầng | Đo gì | Cách đo |
|---|---|---|
| 1. Từ PC | Latency NPU, thời gian từng layer, bộ nhớ NPU | `eval_perf(fix_freq=True)` qua board kết nối PC, 3 phiên `init_runtime` riêng (bảng dưới). Thời gian do phần cứng trên board đo, không bị ảnh hưởng bởi mạng. Code: `ai/automation/benchmark_npu.py` |
| 2. Trên board | Pre, NPU, post, E2E | Chạy trực tiếp trên board bằng `rknn-toolkit-lite2`: 20 lần warmup, rồi 1 lượt qua toàn bộ ảnh `sfchd_test`. Báo mean, P50, P95, std cho từng bước. Code: `ai/board/bench_npu.py` |

3 phiên của tầng 1 (khoá v1):

| Phiên | `init_runtime` | Lấy gì | Vì sao tách phiên |
|---|---|---|---|
| 1 | mặc định | NPU latency = median của 5 lần `eval_perf` (lưu cả 5 giá trị) | Đo thử ngày 2026-09-26 (INT8, 2 phiên × 5 lần): từng lần dao động 18.5–22.4 ms, median 2 phiên 19.25 và 19.56 ms |
| 2 | `perf_debug=True` | Bảng từng layer: op, CPU/NPU, DDR/NPU cycles, thời gian | Chế độ debug in *"The performance result is just for debugging, may worse than actual performance!"* |
| 3 | `eval_mem=True` | Bộ nhớ NPU (`eval_memory`) | Bắt buộc để `eval_memory` chạy (toolkit báo lỗi *"When init runtime, parameter <eval_mem> should be set to True"*); đo thử: bật `eval_mem` làm `eval_perf` tăng từ 17.2 lên 22.9 ms |

Định dạng output của bản 2.3.2 (lưu ở `tests/fixtures/eval_perf_2.3.2_*.txt`, kiểm bằng `make test-parsers`): phiên 1 in `Total Time(us): <n>`, phiên 2 in `Total Operator Elapsed Per Frame Time(us): <n>` và bảng layer. `fix_freq=True` chuyển governor NPU và DDR sang `userspace` ở tần số tối đa (NPU 1 GHz, DDR 2112 MHz) và giữ nguyên sau khi đo.

Định nghĩa từng bước ở tầng 2 (khoá v1):

| Bước | Gồm | Không gồm |
|---|---|---|
| Pre | Resize + LetterBox + BGR→RGB, từ ảnh BGR đã giải mã trong RAM. Giống từng pixel input của evaluator (đã kiểm md5 trên 4 ảnh) | Đọc và giải mã file ảnh (pipeline camera không có bước này) |
| NPU | `RKNNLite.inference()` | |
| Post | NMS + đưa box về toạ độ ảnh gốc, theo mặc định **predict** của Ultralytics: conf 0.25, IoU 0.7, max_det 300, 1 class/box | NMS kiểu val (conf 0.001) chỉ dùng cho AI Quality |
| E2E | Pre + NPU + Post | |

Post dùng conf 0.25 (`cfg/default.yaml`: *"defaults: predict=0.25, val=0.001"*) vì tầng 2 đo tốc độ lúc triển khai; với conf 0.001 số box qua NMS lớn hơn nhiều và thời gian post không phản ánh lúc chạy thật.

- Không bấm giờ quanh `rknn.inference()` gọi từ PC: con số sẽ cộng cả thời gian truyền ảnh qua mạng.
- Tầng 2 dùng ảnh thật vì thời gian NMS phụ thuộc số object trong ảnh. So sánh NPU giữa các model thì dùng tầng 1, vì thời gian NPU không phụ thuộc nội dung ảnh.
- Khoá tần số CPU/DDR/NPU trước khi đo tầng 2, theo [`02_Rockchip_RKNPU_User_Guide_RKNN_API_V1.5.2_EN.pdf`](papers/05_rk3588/01_vendor_docs/03_rknn_npu/02_Rockchip_RKNPU_User_Guide_RKNN_API_V1.5.2_EN.pdf), trang PDF 72–73. Tài liệu dùng governor `userspace`; board này có sẵn governor `performance` cho cả CPU, NPU (`fdab0000.npu`) và DDR (`dmc`), giữ mọi clock ở tần số tối đa mà không cần đường debugfs, nên script `ai/board/lock_freq.sh` dùng `performance`. Mọi file kết quả tầng 2 tự ghi governor và tần số trước/sau khi đo (`frequency_before`, `frequency_after`, cờ `locked`).
- Throughput FPS ghi rõ số context/luồng và `core_mask`. Code: `ai/board/bench_throughput.py` (mỗi context 1 luồng Python, frame lấy từ 200 ảnh test đã giải mã sẵn trong RAM).

## 5.4. Resource & Energy

```text
RAM usage
CPU utilization
Thời gian từng layer, layer nào chạy CPU / NPU
Temperature
Power, Energy / frame (ngoài v1)
```

**Cách đo (khoá v1):**

- **RAM**: lấy mẫu `VmRSS` của process tầng 2 trong suốt lúc chạy, báo giá trị lớn nhất. Không dùng `VmHWM` vì man page Linux (`proc_pid_status(5)`) ghi *"This value is inaccurate"*. Bộ nhớ driver NPU cấp cho model có thể không tính trong RSS, nên lấy riêng bằng `rknn.eval_memory()` ở tầng 1, phiên 3 (`init_runtime(eval_mem=True)`) ([`01_Rockchip_RKNPU_API_Reference_RKNN_Toolkit2_V2.3.2_EN.pdf`](papers/05_rk3588/01_vendor_docs/03_rknn_npu/01_Rockchip_RKNPU_API_Reference_RKNN_Toolkit2_V2.3.2_EN.pdf), mục 2.10, trang PDF 19: *"Fetch memory usage when model is running on hardware platform"*, trả về `weight_memory`, `internal_memory`, `other_memory`, `total_memory`).
- **CPU utilization**: trung bình trong suốt tầng 2.
- **Thời gian từng layer, layer CPU/NPU**: tầng 1, `eval_perf` khi `init_runtime(perf_debug=True)`. Toolkit2-API trang PDF 18: 
> *"If the perf_debug is set to True, the running time of each layer will also be captured in detail."*
- **Nhiệt độ**: đọc lúc bắt đầu, kết thúc và lấy mẫu trong suốt tầng 2 từ thermal zone có `type` = `npu-thermal` (trên board này là `/sys/class/thermal/thermal_zone6`, đã kiểm ngày 2026-09-26).
- **Power, Energy/frame**: chưa có cách đo đã kiểm chứng (cảm biến trên board hoặc thiết bị đo ngoài), nên để ngoài v1.

**Code của protocol v1 (đã có, chi tiết file và lệnh ở mục 8.1):**

- [x] Evaluator chung cho FP32 và NPU: `ai/core/evaluator.py`, `ai/core/backends.py`
- [x] Bỏ `measure_map_drop` cũ trong `ai/core/rknn/benchmark.py` (lệch protocol ở 3 chỗ: `cv2.resize` kéo thẳng, NMS IoU 0.65, chỉ đọc `*.jpg`); accuracy NPU nay đo bằng evaluator với backend RKNN (inference trên board, NMS và AP trên PC, xem mục 5.1)
- [x] Code tầng 2 trên board: `ai/board/bench_npu.py`, `bench_cpu_onnx.py`, `bench_throughput.py`
- [x] Golden test: `ai/automation/check_evaluator.py`, số lưu ở `ai/automation/golden/evaluator_v1.json`
---

# 6. Phải so sánh với ai?

Mọi phép so sánh trong mục này đo theo Evaluation Protocol v1 (mục 5.0): cùng dataset, split, kích thước input, metric và cách đo. Mỗi phép so sánh chỉ khác mốc của nó đúng 1 yếu tố.

## 6.1. Model comparison

```text
YOLOv8n
YOLOv8s
YOLO11n, YOLO11s (giai đoạn sau, mục 8 Phase 5)
```

- **YOLOv8n/s**: đã có code (`ai/models/yolov8n_baseline.py`, `yolov8s_baseline.py`) và kế hoạch train (mục 0.2). YOLOv8s là model duy nhất có số FPS trên chính RK3588 trong kho tài liệu: INT8 70.9 FPS, FP16 32.9 FPS ở 720P ([`dahd_yolo_rk3588_2025.pdf`](papers/05_rk3588/dahd_yolo_rk3588_2025.pdf), Table 6, tr.18). Số này chỉ dùng để kiểm độ hợp lý, không so trực tiếp (khác dataset, khác kích thước input).
- **Không dùng YOLOv5n**: chạy qua Ultralytics thì nó là YOLOv5nu, dùng head không anchor giống YOLOv8 (`ultralytics/utils/downloads.py` dòng 27: `yolov5{k}{resolution}u.pt`), khác YOLOv5 gốc mà các paper CHV, SHEL5K, SFCHD dùng, nên cũng không so được với số của paper.
- **Không so mAP trực tiếp với paper SFCHD**: split gốc không được phát hành (`data/sfchd/DATA_CARD.md`), paper dùng ảnh 1333×800 và MMDetection (tr.9). Mọi so sánh accuracy là so sánh nội bộ dưới cùng protocol v1.

## 6.2. Optimization comparison (trọng tâm)

| Nhóm | Biến thể | So với | Yếu tố thay đổi | Train lại? |
|---|---|---|---|---|
| 1. Nén model | FP16 baseline | - | Mốc gốc | - |
| | INT8 PTQ | FP16 baseline | Datatype FP16 → INT8 | Không |
| | Structured pruning (FP16) | FP16 baseline | Cắt channel/filter ít quan trọng | Có (fine-tune) |
| | Structured pruning + INT8 | INT8 PTQ | Thêm pruning | Có (fine-tune) |
| 2. Cấu hình triển khai (cùng model INT8) | `core_mask` `CORE_0` / `CORE_0_1_2` | `core_mask` `AUTO` | Số core NPU | Không |
| | Nhiều luồng (thread pool) | 1 luồng | Số context chạy song song, đo Throughput FPS | Không |
| 3. Hardware-aware | Activation ReLU / LeakyReLU | Activation SiLU | Activation (giả thuyết mục 2.1) | Có |
| | Model đề xuất | Baseline tốt nhất | Theo bottleneck thật tìm ở mục 4 | Có |

- **FP16** chạy được trên NPU RK3588 (DAHD-YOLO có số FP16, tr.18). Export: `make export-npu RUN=<run_id> PREC=fp16`.
- **Pruning** chỉ tính structured pruning (cắt hẳn channel/filter để model nhỏ đi). Công cụ `autosparsity` của Rockchip chỉ tăng tốc sparse inference trên RK3576: `3rdparty/rknn-toolkit2/autosparsity/README.md` ghi *"Only supports RK3576 target platform"*. Chưa có bằng chứng structured pruning tăng tốc trên RK3588, phải đo.

## 6.3. Hardware comparison

| Thiết bị | Vai trò | Chạy gì |
|---|---|---|
| CPU của board (4 nhân Cortex-A76 + 4 nhân Cortex-A55) | Bắt buộc: cho thấy lợi ích của NPU trên cùng thiết bị | File `.onnx` FP32 (`weights/best.onnx`, export cùng opset 19 với `.rknn`) bằng ONNX Runtime 1.23.2 (đã cài trong `.venv-board`), ghi số thread |
| NPU của board, FP16 | Bắt buộc | `.rknn` FP16 |
| NPU của board, INT8 | Bắt buộc | `.rknn` INT8 |
| GPU của PC: NVIDIA GeForce RTX 3050 Laptop | Chỉ tham chiếu, không phải thiết bị triển khai | PyTorch FP32 |

Nguồn: CPU theo [`01_HYY_Rockchip_RK3588_Datasheet.pdf`](papers/05_rk3588/01_vendor_docs/01_datasheet/01_HYY_Rockchip_RK3588_Datasheet.pdf) (*"quad-core Cortex-A76 and quad-core Cortex-A55"*); GPU theo log train `tmp/05_training-logs/` (`CUDA:0 (NVIDIA GeForce RTX 3050 Laptop GPU, 3762MiB)`). GPU Mali trên board nằm ngoài phạm vi, vì repo chưa có pipeline chạy model trên Mali.

**Code cho các phép so sánh:**

- [x] Export FP16: `ai/automation/export_npu.py --quantize 16`
- [x] Chạy `.onnx` trên CPU của board (ONNX Runtime): `ai/board/bench_cpu_onnx.py`
- [x] Nhiều context song song để đo Throughput FPS: `ai/board/bench_throughput.py`
- [ ] Code structured pruning + fine-tune (viết ở Phase 7, sau khi Phase 6 cho thấy cần)

---

# 7. Bộ bảng số liệu nên chuẩn bị ngay từ đầu

> Phần này được thiết kế để **điền số liệu dần trong quá trình làm**. Không nhất thiết đưa tất cả bảng vào paper cuối cùng; mục 9 ghi bảng nào bắt buộc.

**Quy tắc chung cho mọi bảng:**

- Mọi số đo theo Evaluation Protocol v1 (mục 5.0). Protocol lên phiên bản mới thì đo lại toàn bộ bảng, không trộn số của 2 phiên bản.
- Accuracy đánh giá trên **tập test chung là tập test của SFCHD (1,238 ảnh)** cho mọi model, dù train trên Lựa chọn 1 (`sfchd_5class`) hay Lựa chọn 2 (`sfchd_shel5k`). Split của SFCHD được giữ nguyên ở cả 2 dataset và SHEL5K không trùng ảnh với SFCHD (mục 0.2.2), nên tập test này sạch cho cả 2. Model Lựa chọn 2 báo thêm kết quả trên tập test SHEL5K (500 ảnh), tách riêng.
- **Seed:** mọi phase train **1 seed (42)**. Phase 10 (mục 8) train thêm **seed 43, 44** cho các model của bảng so sánh chính (YOLOv8n baseline và model đề xuất), báo mean ± std. Lý do: thời gian train có hạn (YOLOv8n 100 epoch khoảng 2.25 giờ, YOLOv8s khoảng 4.72 giờ trên RTX 3050 Laptop, theo `tmp/05_training-logs/`).
  - **Seed là gì:** số khởi tạo cho bộ sinh số ngẫu nhiên. Trong Ultralytics, `seed` đặt đồng thời `random.seed`, `np.random.seed`, `torch.manual_seed` (`ultralytics/utils/torch_utils.py`, hàm `init_seeds`), nên quyết định thứ tự xáo dữ liệu, các phép augmentation ngẫu nhiên và giá trị khởi tạo của các lớp mới. Cùng seed thì train lại ra kết quả gần như giống hệt (`deterministic: True` là mặc định); đổi seed thì ra model khác, AP lệch đi một chút.
  - **Lợi ích của 3 seed:** với 1 seed, nếu model A hơn model B 0.5% mAP thì không biết đó là cải tiến thật hay chỉ do may rủi. Với 3 seed có std: chênh lệch lớn hơn std mới coi là khác biệt thật. Quan trọng nhất với `head` và `self_clothes` vì tập test chỉ có 110 và 74 instance (Table A).
  - **Hệ quả của 1 seed trước Phase 10:** chọn dataset (sau Phase 2) và chọn candidate (Phase 7) dựa trên 1 seed, chưa biết std. Mọi kết luận trước Phase 10 ghi rõ "1 seed". Chênh lệch dưới 1% mAP50-95 coi là chưa phân biệt được; 1% là giá trị chọn trước (chưa có std để căn cứ), thay bằng std thật sau Phase 10.
  - **Chỉ seed train thay đổi:** split dữ liệu luôn cố định bằng seed 42 của `scripts/data/prepare_sfchd.py`, nên mọi lần train dùng đúng cùng tập train/val/test. Seed 42 là giá trị đang dùng trong `ai/automation/configs/*.yaml`; 43 và 44 là 2 giá trị kế tiếp, chọn cố định trước khi train để không bị nghi chọn seed đẹp.
  - **Căn cứ:** 4 paper PPE trong `docs/papers/07_ppe_detection/` đều không báo độ lệch chuẩn; DAHD-YOLO tự nhận việc chỉ dùng 1 seed là hạn chế ([`dahd_yolo_rk3588_2025.pdf`](papers/05_rk3588/dahd_yolo_rk3588_2025.pdf), tr.20):

> "While we employed a fixed random seed to ensure reproducibility and facilitate comparisons of improvements, this approach also imposes limitations on the statistical significance of our results."

---

## Table A. Dataset Summary

**Mục đích:** chứng minh dữ liệu dùng để train/test được mô tả rõ và có thể reproduce.

| Dataset | Dùng cho | #Images | #Train | #Val | #Test | Classes | #Instances | Nguồn ảnh |
|---|---|---:|---:|---:|---:|---|---:|---|
| `sfchd_5class` | Lựa chọn 1 | 12,372 | 9,897 | 1,237 | 1,238 | 5 class (mục 0.1) | 48,096 | Camera giám sát 2 nhà máy hóa chất |
| `sfchd_shel5k` | Lựa chọn 2 | 17,372 | 13,897 | 1,737 | 1,738 (1,238 SFCHD + 500 SHEL5K) | 5 class | 93,483 | Thêm ảnh công trường xây dựng (SHEL5K) |
| External test set (optional) | Cross-domain | [TBD] | - | - | [TBD] | [TBD] | [TBD] | [TBD] |

`#Instances` = số object được gán nhãn (số bounding box). Một ảnh có thể chứa nhiều instance.

| Ghi chú | Chi tiết | Nguồn |
|---|---|---|
| Split SFCHD | 80/10/10 (8:1:1), seed 42, tự tạo | `scripts/data/prepare_sfchd.py` |
| Split SHEL5K | 80/10/10, seed 42, tự tạo (bản tải về không kèm split) | `scripts/data/prepare_shel5k.py`, `data/shel5k/DATA_CARD.md` |
| Dataset 5 class | `sfchd_5class` và `sfchd_shel5k` giữ nguyên split của từng dataset gốc | `scripts/data/prepare_sfchd_5class.py`, `prepare_sfchd_shel5k.py` |
| So với paper | Paper SFCHD chia train:test 4:1, paper SHEL5K chia 4000:1000 (không có val); cả 2 không phát hành danh sách split, nên không so trực tiếp được với số của paper | [`sfchd_scale_2023yu.pdf`](papers/07_ppe_detection/sfchd_scale_2023yu.pdf) tr.1; [`shel5k_helmet_2022otgonbold.pdf`](papers/07_ppe_detection/shel5k_helmet_2022otgonbold.pdf) tr.8 |
| Số ảnh SFCHD | Paper ghi 12,373, bản tải về có 12,372 (lệch 1 ảnh) | paper SFCHD tr.1; `data/sfchd/DATA_CARD.md` |
| Class | Bỏ `blur_head`, `blur_clothes` của SFCHD | mục 0.2 |
| Số instance | Đếm trực tiếp từ file nhãn | `data/<dataset>/processed/labels/` |

### Class distribution trên tập test chung (SFCHD)

| Class | Train Instances | Val Instances | Test Instances | Total | Percentage |
|---|---:|---:|---:|---:|---:|
| person | 13,624 | 1,697 | 1,688 | 17,009 | 35.4% |
| helmet | 11,442 | 1,446 | 1,409 | 14,297 | 29.7% |
| head | 987 | 102 | 110 | 1,199 | 2.5% |
| safety_clothes | 11,846 | 1,507 | 1,459 | 14,812 | 30.8% |
| self_clothes | 641 | 64 | 74 | 779 | 1.6% |
| **Tổng** | **38,540** | **4,816** | **4,740** | **48,096** | 100% |

`head` (đầu trần, không đội mũ) và `self_clothes` (quần áo thường) là 2 class báo vi phạm, nhưng chỉ chiếm 2.5% và 1.6% số object. Tập test chỉ có 110 và 74 object của 2 class này, nên bắt đúng hay bỏ sót 1 object đã làm recall của class đổi khoảng 0.9% và 1.4% (1/110, 1/74), so với khoảng 0.06% ở `person` (1/1,688). Vì vậy AP của 2 class này có thể lệch đáng kể giữa các lần train khác seed `[suy luận, chưa đo]`. Đây là lý do bảng so sánh chính cần 3 seed ở Phase 10 (quy tắc chung đầu mục 7).

---

## Table B. Training Configuration

**Mục đích:** người khác có thể train lại gần giống thí nghiệm của mình.

| Item | Giá trị | Nguồn |
|---|---|---|
| Framework | Ultralytics 8.4.154, PyTorch 2.4.0+cu124 | `.venv` hiện tại |
| Model / weights khởi tạo | YOLOv8n (`yolov8n.pt`), YOLOv8s (`yolov8s.pt`), weights pretrained chính thức của Ultralytics | `ai/models/yolov8{n,s}_baseline.py` |
| Input size | 640 × 640 | `ai/automation/configs/*.yaml` |
| Batch size | 16 (YOLOv8n), 8 (YOLOv8s, cho vừa 4 GB VRAM như run cũ `sfchd_yolov8s_100ep`) | `ai/automation/configs/*.yaml` |
| Epochs | 100 | `ai/automation/configs/*.yaml` |
| Optimizer | MuSGD, lr0 0.01, momentum 0.9, `warmup_bias_lr` 0.0, ghi tường minh trong config | `ai/automation/configs/*.yaml`; `ultralytics/engine/trainer.py` `build_optimizer` |
| Weight decay | 0.0005 | log train |
| Data augmentation | Mặc định Ultralytics 8.4.154 | `ultralytics/cfg/default.yaml` |
| Random seed | 42 cho mọi phase; thêm 43, 44 ở Phase 10 cho model chính | quy tắc chung mục 7 |
| Train GPU | NVIDIA GeForce RTX 3050 Laptop (3762 MiB) | log train `tmp/05_training-logs/` |
| Dataset | `sfchd_5class` hoặc `sfchd_shel5k` | Table A |

- Config ghi đúng những gì `optimizer=auto` tự chọn, để kết quả không phụ thuộc logic tự chọn này (có thể đổi theo version):
  - `auto` chọn MuSGD (lr 0.01, momentum 0.9) khi số iteration > 10,000, còn lại AdamW (`build_optimizer`).
  - Số iteration = `ceil(số ảnh train / max(batch, nbs=64)) × epochs` (`engine/trainer.py` dòng 312): `sfchd_5class` = 155 × 100 = 15,500; `sfchd_shel5k` = 218 × 100 = 21,800. Cả 2 vượt ngưỡng, kể cả YOLOv8s batch 8 (vì dùng `max(batch, 64)`).
  - `auto` còn tự đặt `warmup_bias_lr = 0.0` (mặc định 0.1), nên config ghi cả tham số này.
  - Log train 1 epoch ngày 2026-09-26 xác nhận: `optimizer: MuSGD(lr=0.01, momentum=0.9)`, `warmup_bias_lr=0.0`.
- Các run cũ 7 class được train bằng PyTorch 2.6.0 (log train), khác môi trường hiện tại; không dùng lại số của chúng.

---

## Table C. Hardware / Software Environment

**Mục đích:** latency phụ thuộc rất mạnh vào board, OS, runtime và version.

| Item | Configuration |
|---|---|
| Board | Orange Pi 5 (`/proc/device-tree/model`) |
| SoC | RK3588S |
| RAM | 4 GB (hệ điều hành thấy 3,916 MiB) |
| Accelerator | RKNPU2, 3 core |
| OS | Orange Pi 1.2.4 Jammy (Ubuntu 22.04.5 LTS) |
| Kernel | 6.1.99-rockchip-rk3588 |
| Python trên board | 3.10.12 (`.venv-board`) |
| RKNN-Toolkit2 (PC) | 2.3.2 |
| RKNNLite2 (board) | 2.3.2 |
| librknnrt | 2.3.2 |
| RKNPU Driver | 0.9.8 |
| ONNX Runtime (CPU board, Table H) | 1.23.2 |
| numpy / OpenCV trên board | 1.26.4 / 4.11.0 (cùng version với PC) |
| Tần số tối đa | CPU A55 1.8 GHz, A76 2.256 / 2.304 GHz; NPU 1 GHz; DDR 2112 MHz |
| Governor mặc định | CPU `ondemand`, NPU `rknpu_ondemand`, DDR `dmc_ondemand` |
| Governor khi đo | `performance` cho CPU, NPU, DDR (`ai/board/lock_freq.sh`, mục 5.3); sau tầng 1, NPU và DDR ở `userspace`, tần số tối đa (do `eval_perf(fix_freq=True)`) |
| NPU thermal zone | `thermal_zone6` (`npu-thermal`) |
| Camera | OV13855 |
| Camera format | NV12 |
| Camera resolution | 1920 × 1080 |
| Model input | 640 × 640 |
| NPU core config | Theo từng thí nghiệm (Table I) |
| Board cooling | [TBD] |
| Ambient condition | [TBD] |

Nguồn: librknnrt, `rknn_server` và API 2.3.2 verify qua `get_sdk_version()` (`tmp/04_debug-logs/2026-09-18_board-bringup-log.md`). Các dòng còn lại đọc trực tiếp trên board ngày 2026-09-26: RKNNLite2 và driver từ log `init_runtime` (`RKNN Driver Information, version: 0.9.8`) và `get_sdk_version()` (`API: 2.3.2`, `DRV: 0.9.8`); OS từ `/etc/os-release`; RAM, governor, tần số, thermal zone từ `/proc` và `/sys`. Mỗi file kết quả tầng 2 tự ghi lại các thông tin này (`system`, `sdk_version`, `frequency_before/after`), nên nếu board đổi firmware thì thấy ngay trong kết quả. Model input 640×640 là default Ultralytics (paper SHEL5K không nêu kích thước input); paper SFCHD tự dùng 1333×800 (tr.9) nên không so trực tiếp được với số của paper SFCHD.

---

## Table D. Baseline Accuracy (FP32)

**Mục đích:** accuracy gốc trước mọi tối ưu. FP32 PyTorch, tập test chung SFCHD (1,238 ảnh). Seed 42; dòng nào có Phase 10 thì báo mean ± std qua 3 seed. Bảng sinh tự động: `results/<ds>/table_D_fp32.md`.

| Model | Train trên | Precision | Recall | mAP50 | mAP50-95 | AP person | AP helmet | AP head | AP safety_clothes | AP self_clothes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| YOLOv8n | Lựa chọn 1 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8n | Lựa chọn 2 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8s | Lựa chọn 1 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8s | Lựa chọn 2 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLO11n | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLO11s | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

Model train trên Lựa chọn 2 báo thêm 1 dòng trên tập test SHEL5K (500 ảnh), cùng các cột, ghi rõ là tập test khác.

---

## Table E. Model Complexity

| Model | Params (M) | GFLOPs | MACs (G) | ONNX FP32 Size (MB) | RKNN Size (MB) |
|---|---:|---:|---:|---:|---:|
| YOLOv8n | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8s | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLO11n | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLO11s | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

Đo theo mục 5.2: model đã fuse, input 640×640, MACs = GFLOPs / 2. Không dùng kích thước file `.pt` vì Ultralytics lưu `best.pt` ở FP16.

---

## Table F. Quantization Impact (FP32 → NPU)

**Mục đích:** trả lời Case B (mục 4.3): quantize làm mất bao nhiêu accuracy, class nào mất nhiều nhất. Cùng 1 evaluator cho cả 3 dòng (mục 5.0); mỗi seed quantize riêng, báo mean ± std khi có Phase 10. Bảng sinh tự động: `results/<ds>/table_F_quantization.md`.

| Model | Precision | mAP50-95 | ΔmAP50-95 so với FP32 | ΔAP person | ΔAP helmet | ΔAP head | ΔAP safety_clothes | ΔAP self_clothes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| YOLOv8n | FP32 (PyTorch) | [TBD] | mốc | mốc | mốc | mốc | mốc | mốc |
| YOLOv8n | FP16 (NPU) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8n | INT8 (NPU) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8s | FP32 (PyTorch) | [TBD] | mốc | mốc | mốc | mốc | mốc | mốc |
| YOLOv8s | FP16 (NPU) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8s | INT8 (NPU) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

**Cách đọc:**

- **Δ** = giá trị của FP32 − giá trị của dòng đó (định nghĩa ở mục 5.1).
- **Δ dương** = bị mất accuracy khi chạy trên NPU; Δ càng lớn càng mất nhiều.
- **"mốc"** = dòng FP32 là mốc để trừ, nên không có Δ. AP từng class của FP32 xem ở Table D.

---

## Table G. Latency Breakdown

**Mục đích:** tìm bottleneck thay vì chỉ nhìn FPS. NPU đo ở tầng 1 (`eval_perf`), các cột khác đo ở tầng 2 trên board (mục 5.3).

| Model | Precision | Pre P50 (ms) | NPU (ms) | Post P50 (ms) | E2E mean (ms) | E2E P50 (ms) | E2E P95 (ms) | FPS_latency |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| YOLOv8n | FP16 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8n | INT8 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8s | FP16 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8s | INT8 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Pruned | INT8 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed | INT8 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

---

## Table H. Hardware Comparison

**Mục đích:** cho thấy lợi ích của NPU so với CPU trên cùng board (mục 6.3). Làm cho YOLOv8n và YOLOv8s.

| Thiết bị | Model / Precision | mAP50-95 | E2E P50 (ms) | E2E P95 (ms) | FPS_latency | Ghi chú |
|---|---|---:|---:|---:|---:|---|
| CPU board (4× Cortex-A76 + 4× Cortex-A55) | `.onnx` FP32, ONNX Runtime | [TBD] | [TBD] | [TBD] | [TBD] | Ghi số thread, nhân CPU dùng |
| NPU board | `.rknn` FP16 | [TBD] | [TBD] | [TBD] | [TBD] | |
| NPU board | `.rknn` INT8 | [TBD] | [TBD] | [TBD] | [TBD] | |
| GPU PC RTX 3050 Laptop (tham chiếu) | PyTorch FP32 | [TBD] | [TBD] | [TBD] | [TBD] | Không phải thiết bị triển khai |

---

## Table I. Deployment Configuration

**Mục đích:** so sánh cấu hình triển khai trên cùng 1 model INT8, không train lại (mục 6.2 nhóm 2).

| `core_mask` | Số luồng (context) | NPU latency (ms) | Throughput FPS | Avg CPU (%) | Temp end (°C) |
|---|---:|---:|---:|---:|---:|
| `AUTO` | 1 | [TBD] | [TBD] | [TBD] | [TBD] |
| `CORE_0` | 1 | [TBD] | [TBD] | [TBD] | [TBD] |
| `CORE_0_1` | 1 | [TBD] | [TBD] | [TBD] | [TBD] |
| `CORE_0_1_2` | 1 | [TBD] | [TBD] | [TBD] | [TBD] |
| `CORE_0` / `CORE_1` / `CORE_2` (mỗi luồng 1 core) | 3 | [TBD] | [TBD] | [TBD] | [TBD] |

Với 1 luồng, Throughput FPS xấp xỉ FPS_latency; với nhiều luồng thì khác (mục 5.3). Chế độ gộp core chỉ tăng tốc một số op (Conv, Add, Concat, ReLU...), op khác tự chạy trên Core0 (mục 2.1).

---

## Table J. Main Accuracy–Efficiency Comparison

> Bảng trọng tâm nên có trong paper.

| Model / Method | mAP50-95 | ΔmAP so với FP32 | AP head | AP self_clothes | Params | GFLOPs | RKNN Size | NPU latency | E2E P95 | Throughput FPS | Peak RAM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| YOLOv8n FP16 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8n INT8 PTQ | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Structured pruning | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Structured pruning + INT8 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Activation ReLU / LeakyReLU + INT8 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed HW-aware | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

`AP head` và `AP self_clothes` là 2 tín hiệu vi phạm, ít mẫu nhất (Table A), dễ bị ảnh hưởng nhất khi nén model.

---

## Table K. Operator / Layer Bottleneck Profile

**Mục đích:** rất quan trọng nếu muốn claim hardware-aware contribution. Thời gian từng layer và DDR/NPU cycles lấy từ bảng layer của `eval_perf` khi `perf_debug=True` (tầng 1, phiên 2); bảng này sinh tự động ở `results/<dataset>/table_K_layers.md`. Build log `RKNN_LOG_LEVEL=3` (`runs/<run_id>/logs/export_int8_*.log`) có cycles ước tính lúc build, dùng để đối chiếu.

| Layer | Loại op | Chạy trên (CPU/NPU) | Hỗ trợ đa nhân trên RK3588 | Thời gian (µs) | % tổng | DDR/NPU cycles | Ghi chú |
|---|---|---|---|---:|---:|---:|---|
| [TBD] | Conv + SiLU (`ConvExSwish`) | [TBD] | Tạm chưa ("暂不支持", 3.2.17 ConvolutionSwish), nếu 2 tên là cùng 1 op | [TBD] | [TBD] | [TBD] | |
| [TBD] | Resize (upsample trong neck) | [TBD] | Không ("不支持", 3.2.54) | [TBD] | [TBD] | [TBD] | |
| [TBD] | Conv không activation | [TBD] | Có ("支持", 3.2.5) | [TBD] | [TBD] | [TBD] | |
| [TBD] | Concat | [TBD] | Có (RKNPU2 User Guide, trang PDF 27) | [TBD] | [TBD] | [TBD] | |

Cột "Hỗ trợ đa nhân" theo tài liệu Rockchip, đã kiểm ở mục 2.1. Các câu hỏi bảng phải trả lời:

```text
Operator nào chiếm nhiều latency?
Operator không hỗ trợ đa nhân chiếm bao nhiêu % thời gian?
Có operator nào chạy CPU không?
Layer nào DDR cycles cao hơn NPU cycles (nghẽn vì di chuyển dữ liệu)?
Block nào FLOPs không cao nhưng latency lại cao?
```

---

## Table L. Hardware Resource Usage

Đo theo mục 5.4, trong lúc chạy tầng 2.

| Model / Precision | Peak RAM (MB, VmRSS) | NPU memory (MB) | Avg CPU (%) | Temp start (°C) | Temp end (°C) |
|---|---:|---:|---:|---:|---:|
| YOLOv8n FP16 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8n INT8 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

NPU memory lấy qua `RKNN_QUERY_MEM_SIZE` nếu dùng được (mục 5.4). Power và Energy/frame nằm ngoài v1, chưa có cách đo đã kiểm chứng.

---

## Table M. Ablation Study

> Đề xuất là bảng chính trong paper. Mỗi dòng bật/tắt từng thay đổi ở mục 6.2 để tách đóng góp của từng cái.

| Exp | INT8 | Structured pruning | Activation ReLU | Thay đổi khác | mAP50-95 | ΔmAP so với FP32 | AP head | AP self_clothes | NPU latency | Throughput FPS |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| Baseline | ✗ | ✗ | ✗ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| A | ✓ | ✗ | ✗ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| B | ✗ | ✓ | ✗ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| C | ✗ | ✗ | ✓ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| D | ✓ | ✓ | ✓ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

**Cách đọc:**

- **✓** = thay đổi đó được áp dụng trong thí nghiệm.
- **✗** = không áp dụng. Riêng ✗ ở cột INT8 nghĩa là model chạy FP16 trên NPU (giống dòng đầu của Table J).
- **A, B, C so với Baseline** = biết riêng mỗi thay đổi đóng góp bao nhiêu.
- **D so với A, B, C** = biết kết hợp cả 3 có tốt hơn từng cái riêng lẻ không.
- **Tổ hợp 2 thay đổi** (vd INT8 + pruning, đã có ở Table J) chưa có trong bảng; chỉ thêm nếu D khác xa tổng đóng góp của A, B, C.

Ablation phải giúp trả lời:

```text
INT8 đóng góp bao nhiêu?
Pruning đóng góp bao nhiêu?
Đổi activation đóng góp bao nhiêu (có mở khoá chạy đa nhân không)?
Kết hợp có tốt hơn thật không?
```

---

# 8. Experimental Plan đề xuất

Kế hoạch thực hiện toàn bộ đề tài theo thứ tự thực hiện thật ở mục 3.2. Mọi bước chạy qua `make`; mỗi lệnh tự lưu log, tự ghi file kết quả kèm thông tin truy vết, và `make tables` sinh toàn bộ bảng ở mục 7 từ các file đó. Không gõ tay, không tính tay số nào.

**Quy ước:**

- Lệnh chạy ở thư mục gốc repo trên PC. Dòng ghi **[board, sudo]** chạy trên board (`ssh minhnhat@100.67.251.37`, trong `~/rk3588`).
- `<ds>` = dataset: `sfchd_5class` (Lựa chọn 1) hoặc `sfchd_shel5k` (Lựa chọn 2).
- `<run_id>` = `<dataset>_<model>_<epochs>ep_s<seed>`, ví dụ `sfchd_5class_yolov8n_baseline_100ep_s42`. Không có ngày, nên cùng config + seed luôn là cùng 1 run.

## 8.0. Tổng quan

| Phase | Tên | Lệnh | Cần board | Bảng được sinh |
|---:|---|---|---|---|
| 0 | Chuẩn bị môi trường và board | lệnh lẻ (8.1, bước 1–4) | Có | C |
| 1 | Khoá protocol v1 | `make golden-test`, `make test-parsers` | Không | - |
| 2 | Train baseline YOLOv8n/s, seed 42 | `make phase2 DATASET=<ds>` | Không | A, B, D |
| 3 | Quantization FP16 / INT8 | `make phase3 DATASET=<ds>` | Có | E, F |
| 4 | Benchmark trên board | `make phase4 DATASET=<ds>` | Có, khoá tần số | G, H, I, K, L |
| 5 | Multi-model YOLO11n/s | như Phase 2–4 sau khi thêm model | Có | D–L (dòng YOLO11) |
| 6 | Bottleneck analysis | đọc `table_K_layers.md` | Không | K |
| 7 | Proposed optimization | như Phase 2–4 cho candidate | Có | J |
| 8 | Ablation | như Phase 2–4 | Có | M |
| 9 | Camera / real-world | code viết ở Phase 9 | Có | - |
| 10 | Chốt số liệu: seed 43, 44 cho model chính | `make phase10 DATASET=<ds> MODELS=...` | Có | D, F, J, M (mean ± std) |

`make phase2/3/4/10` chạy lần lượt mọi bước của phase, **bỏ qua bước đã có file kết quả**, dừng ở lỗi đầu tiên, và kết thúc bằng `make tables`. Bị ngắt (mất điện, lỗi mạng) thì sửa lỗi rồi chạy lại đúng lệnh đó.

---

## 8.1. Runbook

Chạy từ trên xuống. Cột "Kết quả đúng" là thứ cần thấy trước khi sang bước sau.

| # | Lệnh | Chạy khi | Kết quả đúng |
|---:|---|---|---|
| 1 | `make sync`<br>`make check` | 1 lần trên PC | In `rknn.api.RKNN OK` |
| 2 | `make board-sync` | 1 lần, và sau mỗi lần sửa `ai/board/` | Board có `~/rk3588/ai/board/` và 1,238 ảnh `sfchd_test` |
| 3 | `make board-setup` | 1 lần | In `RKNNLite OK` |
| 4 | [board, sudo] `sudo bash ai/board/start_rknn_server.sh` | Sau mỗi lần khởi động lại board, trước Phase 4 (tầng 1 cần) | In `adbd listening on 5555` và pid `rknn_server` |
| 5 | `make golden-test`<br>`make test-parsers` | Trước khi sinh số liệu, và sau mỗi lần sửa code đo | `GOLDEN TEST PASSED`, `PARSERS OK` |
| 6 | `make phase2 DATASET=sfchd_5class`<br>`make phase2 DATASET=sfchd_shel5k` | Train baseline seed 42 (khoảng 17 giờ GPU cho cả 2) | `phase2 complete`; `results/<ds>/table_D_fp32.md` đủ 2 dòng |
| 7 | Chọn dataset, ghi vào `tmp/02_decisions/` | Sau bước 6 | Quyết định có số từ Table D |
| 8 | `make phase3 DATASET=<ds>` | Sau bước 7 (chỉ cần ssh tới board) | `phase3 complete`; Table E, F không còn `[TBD]` |
| 9 | [board, sudo] `sudo bash ai/board/lock_freq.sh lock` | Trước bước 10 | Mọi dòng in `performance` |
| 10 | `make phase4 DATASET=<ds>` | Sau bước 4 và 9 (tầng 1 FP16 mất khoảng 30 phút/model) | `phase4 complete`; Table G, H, I, K, L không còn `[TBD]` |
| 11 | [board, sudo] `sudo bash ai/board/lock_freq.sh unlock` | Sau bước 10 | Governor về `ondemand` |
| 12 | Đọc `results/<ds>/SOURCES.md` | Sau mỗi phase | Mục "Errors" ghi `none` |
| 13 | `make phase10 DATASET=<ds> MODELS=yolov8n_baseline,<model đề xuất>` | Cuối đề tài, sau Phase 7–9 | `phase10 complete`; Table D, F có mean ± std cho các model chính |

Phase 5–9 dùng lại đúng các lệnh trên cho model mới (xem từng phase).

## 8.2. Kết quả và log nằm ở đâu

```text
ai/automation/runs/<run_id>/            # 1 run = 1 model × 1 seed
├── config.yaml, args.yaml, git_commit.txt, metrics.csv
├── logs/                               # log của MỌI lệnh make, tên <lệnh>_<YYYYmmdd-HHMMSS>.log
│   ├── train_*.log, export_fp16_*.log, export_int8_*.log (build log RKNN_LOG_LEVEL=3)
│   ├── evaluate_*.log, tier1_*.log, tier2_*.log (gồm log trên board), throughput_*.log, bench_gpu_*.log
├── eval/                               # AI Quality, protocol v1
│   ├── pt_fp32_<eval_set>.json, onnx_fp32_<eval_set>.json
│   ├── rknn_fp16_<eval_set>.json, rknn_int8_<eval_set>.json
│   └── crosscheck_sfchd_test.json      # chỉ run YOLOv8n seed 42
├── export_fp16.json, export_int8.json, complexity.json
├── bench/                              # tốc độ, tài nguyên (run seed 42; Phase 10 thêm tầng 1 cho YOLOv8n seed 43)
│   ├── tier1_<prec>_<mask>.json, tier1_<prec>_<mask>_layers.json/.txt
│   ├── tier2_<prec>_AUTO.json, tier2_cpu_onnx_t4.json, gpu_pt_fp32.json
│   └── throughput_int8_<masks>.json
└── weights/                            # không đưa lên git: best.pt, best.onnx, rknn_fp16/, rknn_int8/, calib_int8/

ai/automation/leaderboards/<ds>.csv     # 1 dòng / run / eval set (FP32), do make train ghi
results/<ds>/                           # do make tables sinh, không sửa tay
├── table_A_dataset.md ... table_L_resource.md, table_J_M.md
├── tables.csv                          # mỗi ô 1 dòng: giá trị + file:trường nguồn
└── SOURCES.md                          # số run, số ô thiếu, lỗi, cảnh báo
```

**Mỗi file kết quả tự ghi:** `protocol_version`, `git_commit`, `git_dirty` (có sửa code chưa commit), `created_at`, `model_sha256`; file đo trên board ghi thêm governor và tần số trước/sau khi đo (`frequency_before/after`, cờ `locked`). Mỗi log có header: lệnh, thời điểm, git commit, và dòng cuối `exit_code`. Log được làm gọn (bỏ mã màu, gộp dòng cập nhật thanh tiến trình): log train 100 epoch cũ từ 9.2 MB còn 54.7 KB, vẫn giữ dòng kết quả cuối của cả 100 epoch.

**`make tables` tự kiểm** và báo ở `SOURCES.md` (lỗi thì lệnh trả exit code 1):

| Kiểm | Lỗi khi |
|---|---|
| Phiên bản protocol | File nào khác `v1` |
| Dấu vân tay dataset | Các file cùng eval set có dấu vân tay khác nhau |
| sha256 model | `.rknn` đã đo khác `.rknn` trong `export_<prec>.json` (model bị export lại sau khi đo) |
| Khoá tần số | File tầng 2 có `locked = false` |
| Code chưa commit | Cảnh báo (không phải lỗi) nếu `git_dirty = true` |

## 8.3. Khi có lỗi

| Thông báo | Nguyên nhân | Cách sửa |
|---|---|---|
| `adb cannot reach the board` hoặc `rknn_server is not running` | Board vừa khởi động lại, hoặc `adbd` tự thoát (gặp ngày 2026-09-27: board chạy liên tục nhưng `adbd` mất, log trống, chưa rõ nguyên nhân) | [board, sudo] `sudo bash ai/board/start_rknn_server.sh`, rồi chạy lại phase |
| `frequencies not locked` | Chưa khoá tần số trước Phase 4 | [board, sudo] `sudo bash ai/board/lock_freq.sh lock` |
| `... already exists; move it away` | Run bị ngắt giữa lúc train (có `weights/` nhưng chưa có `eval/`) | Xoá thư mục run đó, chạy lại `make phase2` |
| `STOPPED at step i` | Lệnh make của bước i lỗi | Đọc log mới nhất trong `runs/<run_id>/logs/`, sửa, chạy lại phase |
| `ERROR:` khi `make tables` | Một kiểm ở 8.2 không đạt | Chạy lại lệnh sinh file bị báo (xoá file đó rồi chạy lại phase) |

Không chạy lệnh `adb` nào khác (kể cả `make board-check`) khi lệnh tầng 1 (`benchmark-npu`) đang chạy: đo thử ngày 2026-09-26, phiên đang đo bị treo sau khi có lệnh `adb connect` chen vào. Tầng 1 FP16 chậm là bình thường: `init_runtime` khoảng 4.7 phút (upload model qua `rknn_server`), mỗi `eval_perf` 1.5–2 phút.

---

## Phase 0. Chuẩn bị môi trường và board

**Mục tiêu:** PC và board sẵn sàng; đủ thông tin cho Table C.

**Lệnh:** Runbook bước 1–4.

- [x] Bước 2, 3: `make board-sync`, `make board-setup` (2026-09-26: numpy 1.26.4, OpenCV 4.11.0, onnxruntime 1.23.2, RKNNLite2 2.3.2)
- [x] Bước 4: `start_rknn_server.sh` chạy được (2026-09-26, sau khi sửa lỗi `adbd` khởi động trước khi bản cũ thoát hẳn)
- [x] `lock_freq.sh lock` khoá được CPU, NPU, DDR ở tần số tối đa (2026-09-26)
- [x] Table C (Guide): OS, kernel, RAM, RKNNLite2, driver RKNPU 0.9.8, ONNX Runtime, governor, thermal zone
- [ ] Ghi cách tản nhiệt và nhiệt độ phòng vào Table C

**Tiêu chí xong:** `make board-check LOCK=1` in `adb: ok, rknn_server: ok, frequencies locked: True`.

---

## Phase 1. Khoá protocol v1

**Mục tiêu:** mọi công cụ đo đúng protocol v1 (mục 5) trước khi sinh số liệu.

**Lệnh:** `make golden-test`, `make test-parsers`. Kiểm chéo với `model.val()` chạy tự động trong `make phase2`.

- [x] `make golden-test` pass (2026-09-26, log `ai/automation/golden/logs/`); golden file `ai/automation/golden/evaluator_v1.json`
- [x] `make crosscheck` với model 7 class cũ: 24 metric, lệch lớn nhất 0.0001
- [x] Parser `eval_perf` khớp output thật của RKNN 2.3.2: tổng thời gian 119 layer đúng bằng tổng board in ra (`tests/test_parsers.py`)
- [x] Tiền xử lý trên board trùng từng pixel với evaluator (md5 4 ảnh); ảnh calibration trùng input evaluator (sai khác 0)
- [x] Accuracy `.rknn` đo trên board: FP16 cho mAP50-95 0.3677, sát FP32 0.3669 (model nháp), md5 input trùng ở cả 1,238 ảnh
- [x] Chạy thử qua `make` với model nháp (kết quả nháp đã xoá): train 1 epoch (có log, chạy lại bị chặn), export FP16/INT8, evaluate PyTorch/ONNX/RKNN INT8, tầng 1 INT8, tầng 2 FP16/INT8, `bench-gpu`, `make tables` (117 ô, sinh đúng)
- [x] Tầng 1 FP16 chạy được bằng script tay (2 lần `eval_perf`: 29.8, 29.9 ms)
- [ ] Chạy thử qua `make` còn thiếu (board offline giữa chừng ngày 2026-09-26): `evaluate BACKEND=rknn PREC=fp16` sau khi sửa lỗi hết RAM, `bench-board-cpu`, `bench-board-throughput`, `benchmark-npu PREC=fp16`, và 1 lần `make phase3` để kiểm bỏ qua bước đã xong

**Tiêu chí xong:** 2 lệnh trên pass trên commit sẽ dùng để sinh số liệu.

---

## Phase 2. Train baseline YOLOv8n/s

**Mục tiêu:** accuracy FP32 của baseline (seed 42) trên cả 2 lựa chọn dataset.

**Lệnh:**

```bash
make phase2 DATASET=sfchd_5class
make phase2 DATASET=sfchd_shel5k
```

Mỗi lệnh: train YOLOv8n và YOLOv8s seed 42 (2 run), kiểm chéo evaluator trên run YOLOv8n, rồi `make tables`.

- [ ] `phase2` xong cho `sfchd_5class`
- [ ] `phase2` xong cho `sfchd_shel5k`
- [ ] `eval/crosscheck_sfchd_test.json` có `"passed": true` ở cả 2 dataset
- [ ] Chọn dataset theo Table D (mAP50-95 trên `sfchd_test`, AP `head`, `self_clothes`), ghi vào `tmp/02_decisions/`, ghi rõ quyết định dựa trên 1 seed (quy tắc seed, mục 7)

**Bảng:** `results/<ds>/table_A_dataset.md`, `table_B_training.md`, `table_D_fp32.md`.

**Tiêu chí xong:** Table D đủ YOLOv8n/s ở cả 2 dataset; đã chọn dataset. Các phase sau chỉ chạy trên dataset đã chọn.

---

## Phase 3. Quantization FP16 / INT8

**Mục tiêu:** trả lời Case B (mục 4.3): quantize mất bao nhiêu accuracy, class nào mất nhiều nhất.

**Điều kiện:** Phase 2 xong; ssh tới board được. Accuracy của `.rknn` chỉ đo được trên board: simulator của RKNN-Toolkit2 không chạy file nạp bằng `load_rknn` (API Reference mục 2.7, trang PDF 16: *"When target is set to None, the build or hybrid_quantization interface needs to be called first."*).

**Lệnh:** `make phase3 DATASET=<ds>`

Với mỗi run của dataset (2 run): export FP16, export INT8 (300 ảnh calibration), complexity, evaluate ONNX, evaluate RKNN FP16, evaluate RKNN INT8; rồi `make tables`. `evaluate BACKEND=rknn` tự chép model và ảnh lên board, chạy inference ở board (`ai/board/infer_dump.py`), chép output về và tính NMS, AP trên PC (mục 5.1); khoảng 1–2 phút mỗi lần.

- [ ] `phase3` xong
- [ ] `eval/onnx_fp32_*.json` lệch `pt_fp32` không quá 0.001 (ONNX export đúng)
- [ ] Table F: class nào mất accuracy nhiều nhất
- [ ] Kiểm giả thuyết từ lần chạy thử (model nháp 5 epoch, 7 class, không dùng làm kết quả): INT8 giảm mAP50-95 từ 0.367 xuống 0.134, FP16 không giảm (0.368). Output INT8 của Ultralytics chia toạ độ box cho 640 rồi dùng chung 1 scale lượng tử với score (0.004222), nên toạ độ box chỉ có bước khoảng 640 × 0.004222 ≈ 2.7 px

**Bảng:** `table_E_complexity.md`, `table_F_quantization.md`.

**Tiêu chí xong:** Table E, F không còn `[TBD]`; `SOURCES.md` không có lỗi.

---

## Phase 4. Benchmark trên board

**Mục tiêu:** tốc độ và tài nguyên theo protocol v1.

**Điều kiện:** Phase 3 xong; Runbook bước 4 và 9.

**Lệnh:** `make phase4 DATASET=<ds>`, sau đó Runbook bước 11.

Với run seed 42 của YOLOv8n và YOLOv8s:

| Đo | Lệnh make bên trong | Bảng |
|---|---|---|
| Tầng 1 FP16, INT8 (AUTO) và INT8 ở `CORE_0`, `CORE_0_1`, `CORE_0_1_2` | `benchmark-npu` | G, I, K, L |
| Tầng 2 FP16, INT8 trên NPU | `bench-board` | G, H, L |
| Tầng 2 `.onnx` trên CPU board, 4 thread | `bench-board-cpu` | H |
| Throughput 1 context ở 4 core_mask, và 3 context `CORE_0,CORE_1,CORE_2` | `bench-board-throughput` | I |
| GPU PC (tham chiếu) | `bench-gpu` | H |

- [ ] `phase4` xong
- [ ] `SOURCES.md` không có lỗi khoá tần số

**Bảng:** `table_G_latency.md`, `table_H_hardware.md`, `table_I_deployment.md`, `table_K_layers.md`, `table_L_resource.md`.

**Tiêu chí xong:** G, H, I, K, L không còn `[TBD]`.

---

## Phase 5. Multi-model YOLO11n/s

**Mục tiêu:** không phụ thuộc vào 1 họ model (mục 6.1).

**Điều kiện:** Phase 2–4 chạy trọn với YOLOv8.

| Việc | File cần tạo / sửa |
|---|---|
| Thêm model | `ai/models/yolo11n_baseline.py`, `yolo11s_baseline.py` (`WEIGHTS = "yolo11n.pt"`, `"yolo11s.pt"`) |
| Thêm config | `ai/automation/configs/<ds>_yolo11{n,s}_baseline.yaml` (chép config YOLOv8 tương ứng) |
| Cho phase chạy cả YOLO11 | `ai/automation/pipeline.py`: thêm 2 model vào `MODELS` |

Sau đó chạy lại `make phase2/3/4 DATASET=<ds>` (các bước YOLOv8 đã có sẽ được bỏ qua).

- [ ] Thêm model, config, sửa `MODELS`
- [ ] `phase2`, `phase3`, `phase4` xong cho YOLO11
- [ ] Ghi op không hỗ trợ hoặc chạy CPU (`cpu_ops` trong `tier1_*.json`)

**Tiêu chí xong:** có dòng YOLO11 ở D–L, hoặc ghi rõ lý do loại.

---

## Phase 6. Bottleneck analysis

**Mục tiêu:** tìm bottleneck thật bằng số đo; phase quyết định research gap (mục 4.2).

**Dữ liệu:** `results/<ds>/table_K_layers.md` (theo loại op và 20 layer lâu nhất, CPU/NPU, DDR/NPU cycles), `tier1_int8_<mask>_layers.json`, Table E, G.

- [ ] Trả lời 5 câu hỏi dưới Table K (Guide mục 7)
- [ ] So `tier1_int8_CORE_0_layers.json` với `tier1_int8_CORE_0_1_2_layers.json` theo từng layer: op nào không nhanh lên khi thêm core; đối chiếu `ConvExSwish` với `ConvolutionSwish` (mục 2.1)
- [ ] Op chạy trên CPU: đo thử với model nháp ngày 2026-09-26 thấy `Transpose` chạy CPU (590 µs / 20,663 µs); kiểm lại trên model thật
- [ ] So FLOPs (Table E) với latency (Table G) giữa các model (Case C)
- [ ] Ghi research gap và hướng tối ưu vào `tmp/02_decisions/`, có số đo làm căn cứ

**Tiêu chí xong:** có ít nhất 1 bottleneck đo được bằng số, dẫn ra 1 hướng tối ưu cụ thể.

---

## Phase 7. Proposed optimization

**Mục tiêu:** cải thiện hiệu quả trên RK3588S mà giữ accuracy, theo bottleneck của Phase 6.

| Candidate (mục 4.3, 6.2) | Code cần viết | Train lại? |
|---|---|---|
| Structured pruning + fine-tune | Chưa có | Có |
| Activation SiLU → ReLU / LeakyReLU | Model mới trong `ai/models/`, config mới | Có |
| `op_target` cho op không hỗ trợ đa nhân | `ai/core/rknn/deploy.py` (hiện `NotImplementedError`) | Không |
| Mixed precision (`hybrid_quantization_step1/2`) | `ai/core/rknn/deploy.py` | Không |
| Lighter head, input resolution | Model/config mới | Có |

Candidate cần train lại: thêm model + config như Phase 5 rồi chạy `make phase2/3/4`. Candidate không train lại: thêm bước export mới vào `pipeline.py` phase3.

- [ ] Viết code cho candidate được chọn
- [ ] Train 1 seed (42), chạy đủ phase 3–4; kết luận ghi rõ "1 seed" (quy tắc seed, mục 7)
- [ ] Table J

**Tiêu chí xong:** có model đề xuất tốt hơn baseline trên RK3588S (1 seed); xác nhận chênh lệch lớn hơn std ở Phase 10.

---

## Phase 8. Ablation

**Mục tiêu:** tách đóng góp của từng thay đổi (Table M).

- [ ] Chạy các dòng Baseline, A, B, C, D của Table M (mỗi dòng: phase 2–4)
- [ ] Thêm tổ hợp 2 thay đổi nếu D khác xa tổng đóng góp của A, B, C
- [ ] Vẽ Figure 3 (Pareto) và Figure 5 (AP từng class) ở mục 10 từ `results/<ds>/tables.csv`

**Tiêu chí xong:** trả lời được 4 câu hỏi dưới Table M.

---

## Phase 9. Camera / real-world evaluation

**Mục tiêu:** kiểm tra model đề xuất trên camera thật.

```text
OV13855 → NV12 → RGB → LetterBox → RKNN (NPU) → NMS → cảnh báo PPE
```

| Việc | File |
|---|---|
| Pipeline camera trên board, dùng lại `preprocess`, `postprocess`, `ResourceMonitor` | `ai/board/camera.py` (chưa có), `ai/board/common.py` |
| Ghi FPS, nhiệt độ NPU mỗi phút | `runs/<run_id>/bench/camera_<ngày>.json` |

- [ ] Code pipeline camera, thêm target `make bench-camera`
- [ ] Chạy tới khi nhiệt độ ổn định (tăng không quá 1°C trong 10 phút liền), rồi chạy thêm 30 phút. Các ngưỡng 1°C, 10 phút, 30 phút là giá trị chọn, chốt trước khi đo
- [ ] Báo FPS, latency mean/P95, CPU, RAM trong 30 phút ổn định; so FPS lúc đầu và lúc ổn định
- [ ] Lưu video/ảnh mẫu các trường hợp đúng, sót, nhầm

**Tiêu chí xong:** chạy hết 30 phút ổn định không lỗi; có đường FPS và nhiệt độ theo thời gian.

---

## Phase 10. Chốt số liệu (seed 43, 44)

**Mục tiêu:** mean ± std cho các model của bảng so sánh chính (quy tắc seed, mục 7).

**Điều kiện:** Phase 7 đã chọn model đề xuất (Phase 8, 9 xong hoặc chạy song song).

**Lệnh:**

```bash
make phase10 DATASET=<ds> MODELS=yolov8n_baseline,<model đề xuất>
```

Với mỗi model × seed 43, 44: train, export FP16/INT8, evaluate RKNN FP16/INT8; thêm tầng 1 INT8 của YOLOv8n seed 43 để kiểm giả định "cùng kiến trúc thì thời gian NPU như nhau"; rồi `make tables`. Model đề xuất phải có config theo tên `ai/automation/configs/<ds>_<model>.yaml`. Cần Runbook bước 4 (tầng 1).

- [ ] `phase10` xong cho YOLOv8n và model đề xuất
- [ ] So `tier1_int8_AUTO.json` của YOLOv8n seed 42 và 43
- [ ] Kiểm lại các kết luận 1 seed ở Phase 2 (chọn dataset) và Phase 7 (chọn candidate) với std thật; ghi kết quả vào `tmp/02_decisions/`

**Tiêu chí xong:** Table D, F, J, M có mean ± std cho các model chính; chênh lệch chính của đề tài lớn hơn std.

---

## 8.A. Phụ lục

### 8.A.1. Bản đồ code

| File | Làm gì | Gọi bởi |
|---|---|---|
| `ai/automation/pipeline.py` | Chạy cả phase, bỏ qua bước đã xong | `make phase2/3/4` |
| `ai/automation/run.py`, `ai/core/trainer.py` | Train, evaluator v1 trên `best.pt`, ghi leaderboard | `make train` |
| `ai/core/evaluator.py` | Protocol v1: LetterBox, NMS, AP, dấu vân tay dataset | evaluate, run, check |
| `ai/core/backends.py` | PyTorch/ONNX trên PC; `.rknn`: đọc output board, kiểm md5 input | evaluator |
| `ai/core/provenance.py` | git commit, git_dirty, sha256, thời điểm | mọi file kết quả |
| `ai/automation/evaluate.py` | AI Quality 1 run × 1 backend; với `.rknn` điều phối chạy trên board qua ssh | `make evaluate` |
| `ai/board/infer_dump.py` | Inference `.rknn` trên board, lưu output thô + md5 input | `evaluate.py` qua ssh |
| `ai/automation/check_evaluator.py` | Golden test, kiểm chéo | `make golden-test`, `make crosscheck` |
| `ai/automation/export_npu.py`, `ai/core/rknn/baseline.py`, `calibration.py` | Calibration, export `.rknn`, `.onnx` | `make export-npu` |
| `ai/automation/complexity.py` | Params, GFLOPs, MACs, kích thước | `make complexity` |
| `ai/automation/benchmark_npu.py`, `ai/core/rknn/benchmark.py` | Tầng 1: 3 phiên `eval_perf` / layer / `eval_memory` | `make benchmark-npu` |
| `ai/automation/bench_gpu.py` | Latency GPU PC (tham chiếu) | `make bench-gpu` |
| `ai/automation/board_check.py` | Kiểm adb, `rknn_server`, khoá tần số | `make board-check` |
| `ai/automation/tables.py` | Sinh bảng A–L, kiểm nhất quán | `make tables` |
| `ai/board/common.py` | Pre/post giống evaluator, đo RAM/CPU/nhiệt độ, đọc governor | 3 script board |
| `ai/board/bench_npu.py`, `bench_cpu_onnx.py`, `bench_throughput.py` | Tầng 2 trên board | `make bench-board*` |
| `ai/board/start_rknn_server.sh`, `lock_freq.sh` | Lệnh sudo trên board | chạy tay |
| `scripts/logtee.py` | Chạy lệnh, lưu log đã làm gọn + header | mọi target sinh kết quả |
| `tests/test_parsers.py`, `tests/fixtures/` | Kiểm parser với output thật RKNN 2.3.2 | `make test-parsers` |

### 8.A.2. Quyết định đã khoá trong protocol v1

| Việc | Chốt | Căn cứ |
|---|---|---|
| Input khi đánh giá | LetterBox 640×640 vuông, `rect=False`, mọi backend | NPU chỉ nhận 640×640; `model.val()` trên `.pt` tự bật `rect=True` (mục 5.1) |
| Calibration INT8 | 300 ảnh train, ≥ 20 ảnh/class, seed 42, đã LetterBox, PNG | `ultralytics/engine/exporter.py` dòng 1044: *">300 images recommended for INT8 calibration"*; RKNN tự resize ảnh khác kích thước input mà không báo (đo thử) |
| NPU latency tầng 1 | Median 5 lần `eval_perf(fix_freq=True)`, phiên riêng | Dao động 18.5–22.4 ms giữa các lần (mục 5.3) |
| Post-processing tầng 2 | Mặc định predict: conf 0.25, IoU 0.7, max_det 300 | Đo tốc độ lúc triển khai (mục 5.3) |
| E2E tầng 2 | Pre + NPU + post, không gồm giải mã file | Pipeline camera không có bước giải mã |
| Khoá tần số | Governor `performance` (hoặc `userspace` ở tần số tối đa do `eval_perf` đặt) | RKNPU2 User Guide trang PDF 72–73 |
| Seed | 42 cho mọi phase; 43, 44 chỉ ở Phase 10 cho model chính; mean ± std dùng std mẫu (`ddof=1`); bảng phần cứng dùng run seed 42 | Quy tắc seed, mục 7; `ai/automation/tables.py` |

---

# 9. Bảng nào thật sự nên xuất hiện trong paper

| Bảng | Tên | Nhóm | Trả lời câu hỏi |
|---|---|---|---|
| A | Dataset summary | Bắt buộc | Dữ liệu gì, chia split thế nào |
| B | Training configuration | Bắt buộc | Người khác train lại được không |
| C | Hardware/software environment | Bắt buộc | Đo trên môi trường nào |
| D | Baseline accuracy | Bắt buộc | Model gốc (FP32) chính xác đến đâu |
| E | Model complexity | Hardware-aware | FLOPs có phản ánh latency thật không (Case C) |
| F | Quantization impact | Hardware-aware | INT8 mất bao nhiêu accuracy, class nào mất nhiều nhất (Case B) |
| G | Latency breakdown | Hardware-aware | Thời gian nằm ở bước nào (pre, NPU, post) |
| H | Hardware comparison | Hardware-aware | NPU nhanh hơn CPU bao nhiêu trên cùng board |
| I | Deployment configuration | Hardware-aware | `core_mask` và chạy nhiều luồng giúp được bao nhiêu |
| J | Accuracy-efficiency comparison | Bắt buộc | Đánh đổi giữa accuracy và tốc độ (research question mục 2.2) |
| K | Operator / layer bottleneck | Hardware-aware | Op nào là nút thắt (Case C, mục 2.1) |
| L | Resource usage | Hardware-aware | Tốn RAM, CPU, nhiệt độ thế nào |
| M | Ablation | Bắt buộc | Mỗi thay đổi đóng góp bao nhiêu |

"Bắt buộc" là bảng mọi paper detection cần có. "Hardware-aware" là bảng chứng minh contribution về phần cứng, nên có đủ vì đây là trọng tâm đề tài (mục 1).

---

# 10. Figures / biểu đồ nên có trong paper

| STT | Figure | Nội dung | Dữ liệu từ |
|---:|---|---|---|
| 1 | Overall System Architecture | Pipeline: camera → tiền xử lý (LetterBox) → NPU → hậu xử lý (NMS) → cảnh báo vi phạm | Mục 8 Phase 9 |
| 2 | Research Methodology | Flow thực hiện thật: literature → baseline → đo trên RK3588S → bottleneck → research gap → optimization | Mục 3.2 |
| 3 | Accuracy vs Latency (Pareto) | Trục x: E2E latency P50; trục y: mAP50-95, error bar = std qua 3 seed (chỉ các điểm có Phase 10); mỗi điểm là 1 dòng của Table J | Table J, Table D |
| 4 | Latency Breakdown | Cột chồng pre / NPU / post cho từng model và precision | Table G |
| 5 | Per-class AP trước/sau tối ưu | AP 5 class của FP32, INT8 và model đề xuất; nhấn 2 class vi phạm `head`, `self_clothes` | Table F, Table J |
| 6 | Operator Profile | % thời gian theo loại op, tô màu theo "hỗ trợ đa nhân / không" | Table K |
| 7 | Throughput theo cấu hình triển khai | Throughput FPS theo `core_mask` và số luồng | Table I |

---

# 11. Structure paper/report hoàn chỉnh

## 1. Introduction

```text
1.1 Industrial PPE safety problem
1.2 Edge AI motivation
1.3 Limitation of existing lightweight models
1.4 Research gap on target NPU
1.5 Contributions
```

## 2. Related Work

```text
2.1 PPE detection
2.2 Lightweight object detection
2.3 Quantization
2.4 Pruning / compression
2.5 Hardware-aware optimization
2.6 Edge NPU deployment
```

## 3. Baseline and Platform

```text
3.1 SFCHD dataset
3.2 Class mapping
3.3 YOLO baseline
3.4 Orange Pi 5 / RK3588S
3.5 RKNN stack
3.6 Baseline reproduction
```

## 4. Measurement and Bottleneck Analysis

```text
4.1 Accuracy baseline
4.2 Complexity baseline
4.3 Latency breakdown
4.4 Operator / layer profiling
4.5 Identified bottleneck
```

> Với hardware-aware paper, nên có section này **trước Proposed Method** để giải thích vì sao method được chọn.

## 5. Proposed Method

```text
5.1 Design objective
5.2 Optimization strategy
5.3 Architecture modification
5.4 Quantization / pruning
5.5 Hardware-aware rationale
```

## 6. Experimental Setup

```text
6.1 Dataset split
6.2 Training configuration
6.3 Conversion configuration
6.4 Hardware configuration
6.5 Accuracy metrics
6.6 Hardware metrics
6.7 Measurement protocol
```

## 7. Results

```text
7.1 Detection accuracy
7.2 Model complexity
7.3 RK3588S latency
7.4 Resource usage
7.5 Accuracy–latency trade-off
7.6 Per-class analysis
```

## 8. Ablation Study

```text
8.1 Quantization only
8.2 Pruning only
8.3 Architecture change only
8.4 Combined
```

## 9. Real-world Evaluation

```text
9.1 Camera pipeline
9.2 Real-time FPS
9.3 Lighting/occlusion
9.4 Long-run stability
```

## 10. Discussion

```text
10.1 Why proposed method works
10.2 When it fails
10.3 FLOPs vs actual latency
10.4 Limitation
10.5 Generalization
```

# 12. Định hướng chia Đồ án 2 và ĐATN

## Đồ án 2

Ưu tiên: reliable baseline + deployment + system integration + measurement

Deliverable hợp lý:

```text
SFCHD
YOLO baseline
RKNN FP16
INT8 baseline
OV13855 realtime
full metric baseline
```

## ĐATN

Dựa trên dữ liệu từ Đồ án 2:

```text
benchmark
   ↓
find bottleneck
   ↓
hardware-aware optimization
   ↓
proposed method
   ↓
ablation
   ↓
accuracy-efficiency improvement
```

Tức là Đồ án 2 trở thành:

> **Research foundation cho ĐATN.**

---

# 13. Việc nên làm ngay từ trạng thái hiện tại

Trạng thái ngày 2026-09-26: Phase 0 xong; Phase 1 còn các bước kiểm cần board (checklist Phase 1, mục 8). Việc tiếp theo: `make phase2` cho cả 2 dataset (không cần board, khoảng 17 giờ GPU), song song với các bước kiểm còn lại khi board online.

---

> **Mục tiêu không phải tạo model nhỏ nhất hoặc FPS cao nhất bằng mọi giá; mục tiêu là tìm một PPE detector có accuracy đủ tốt và chạy hiệu quả hơn trên RK3588S, với mọi improvement được chứng minh bằng measurement thực tế, comparison công bằng và ablation rõ ràng.**
