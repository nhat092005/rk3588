# MASTER RESEARCH GUIDE
## PPE Detection + Edge AI + Hardware-Aware Optimization trên RK3588S

# 0. Tóm tắt đề tài đang làm gì?

## 0.1. Application hiện tại

Bài toán ứng dụng:

```text
Industrial PPE Detection
```

Các class hiện tại:

```text
person
helmet
safety_clothes
```

Dataset chính:

```text
SFCHD -> sẽ bổ sung thêm dataset để tăng chất lượng
```

Target hardware:

```text
Orange Pi 5
RK3588S
RKNPU v2
```
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
   - person / helmet / safety_clothes
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

Tư tưởng cốt lõi cần giữ xuyên suốt:

> **Model ít FLOPs hoặc ít parameters chưa chắc chạy nhanh hơn trên NPU. Hiệu quả thật phải được đo trực tiếp trên target hardware.**

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

Do đó:

```text
low FLOPs ≠ low latency
small model ≠ fast model on NPU
```

Research problem tổng quát:

> **Làm thế nào giữ PPE detection accuracy ở mức tốt nhưng đồng thời cải thiện inference efficiency trên RK3588S NPU?**

---

# 3. Form nghiên cứu nên follow

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

---

# 7. Ba nhóm metric bắt buộc

## 7.1. AI Quality

```text
Precision
Recall
mAP50
mAP50-95
AP_person
AP_helmet
AP_safety_clothes
```

## 7.2. Model Complexity

```text
Parameters
FLOPs / MACs
Model size
```

## 7.3. Hardware Performance

```text
Pre-processing latency
Pure NPU inference latency
Post-processing latency
End-to-end latency
FPS
RAM usage
CPU utilization
```

Nếu làm được thêm:

```text
Temperature, Power, Energy / frame
```
---

# 8. Phải so sánh với ai?

## 8.1. Model comparison

Candidate:

```text
YOLOv5n
YOLOv8n
YOLO11n
một lightweight detector khác nếu RKNN support tốt
```

Điều kiện:

```text
same dataset
same train/test split
same image size
same metric
same evaluation protocol
```

## 8.2. Optimization comparison — trọng tâm

```text
FP16 baseline
vs
INT8 PTQ
vs
Pruned model
vs
INT8 + Pruning
vs
Hardware-aware optimized model
```

Hiểu đơn giản:

```text
FP16 baseline
= model chuẩn ban đầu

INT8 PTQ
= giảm datatype để tăng efficiency

Pruned model
= cắt bớt phần ít quan trọng

INT8 + Pruning
= kết hợp compression

Hardware-aware
= chỉnh model theo bottleneck thật của RK3588S
```

## 8.3. Hardware comparison

Tối thiểu: PyTorch CPU vs RKNN FP16 NPU vs RKNN INT8 NPU vs GPU

Nếu sau này có thêm platform thì mở rộng.

---

# 9. Bộ bảng số liệu nên chuẩn bị ngay từ đầu

> Phần này được thiết kế để **điền số liệu dần trong quá trình làm**.  
> Không nhất thiết đưa tất cả bảng vào paper cuối cùng. Sau khi có dữ liệu, chọn bảng quan trọng nhất.

---

## Table A — Dataset Summary

**Mục đích:** chứng minh dữ liệu dùng để train/test được mô tả rõ và có thể reproduce.

| Dataset | #Images | #Train | #Val | #Test | Classes | #Instances | Image Source | Notes |
|---|---:|---:|---:|---:|---|---:|---|---|
| SFCHD | 12,373 | [TBD] | [TBD] | [TBD] | person / helmet / safety_clothes | [TBD] | Industrial surveillance | 3-class mapping |
| External test set (optional) | [TBD] | - | - | [TBD] | [TBD] | [TBD] | [TBD] | Cross-domain |

### Nên bổ sung class distribution

| Class | Train Instances | Val Instances | Test Instances | Total | Percentage |
|---|---:|---:|---:|---:|---:|
| person | [TBD] | [TBD] | [TBD] | [TBD] | [TBD]% |
| helmet | [TBD] | [TBD] | [TBD] | [TBD] | [TBD]% |
| safety_clothes | [TBD] | [TBD] | [TBD] | [TBD] | [TBD]% |

---

## Table B — Training Configuration

**Mục đích:** người khác có thể train lại gần giống thí nghiệm của mình.

| Item | Value |
|---|---|
| Framework | Ultralytics / PyTorch [version TBD] |
| Model | YOLOv8n |
| Pretrained weights | [TBD] |
| Input size | 640 × 640 |
| Batch size | [TBD] |
| Epochs | [TBD] |
| Optimizer | [TBD] |
| Initial learning rate | [TBD] |
| Weight decay | [TBD] |
| Data augmentation | [TBD] |
| Random seed | [TBD] |
| Train GPU | [TBD] |
| Dataset version | [TBD] |
| Train/Val/Test split | [TBD] |

---

## Table C — Hardware / Software Environment

**Mục đích:** latency phụ thuộc rất mạnh vào board, OS, runtime và version.

| Item | Configuration |
|---|---|
| Board | Orange Pi 5 |
| SoC | RK3588S |
| RAM | 4 GB |
| Accelerator | RKNPU v2 |
| OS | Ubuntu Jammy |
| Kernel | 6.1.99-rockchip-rk3588 |
| RKNN-Toolkit2 | 2.3.2 |
| RKNNLite2 | 2.3.2 |
| librknnrt | 2.3.2 |
| RKNPU Driver | 0.9.8 |
| Camera | OV13855 |
| Camera format | NV12 |
| Camera resolution | 1920 × 1080 |
| Model input | 640 × 640 |
| CPU governor | [TBD] |
| NPU core config | [TBD] |
| Board cooling | [TBD] |
| Ambient condition | [TBD] |

---

## Table E — Baseline Accuracy

| Model | Precision | Recall | mAP50 | mAP50-95 | AP Person | AP Helmet | AP Clothes |
|---|---:|---:|---:|---:|---:|---:|---:|
| YOLOv8n baseline | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv5n | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLO11n | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

> **Quan trọng:** AP Helmet nên có cột riêng vì helmet thường nhỏ và dễ bị ảnh hưởng bởi compression.

---

## Table F — Model Complexity

| Model | Params (M) | MACs (G) | FLOPs (G) | PT/ONNX Size (MB) | RKNN Size (MB) |
|---|---:|---:|---:|---:|---:|
| YOLOv8n | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv5n | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLO11n | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

---

## Table G — Latency Breakdown

**Mục đích:** tìm bottleneck thay vì chỉ nhìn FPS.

| Model | Preprocess (ms) | NPU Inference (ms) | Postprocess (ms) | Render/Other (ms) | E2E Latency (ms) | FPS |
|---|---:|---:|---:|---:|---:|---:|
| FP16 Baseline | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| INT8 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Pruned | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

---

## Table H — Main Accuracy–Efficiency Comparison

> Bảng trọng tâm nên có trong paper

| Model / Method | Precision | Recall | mAP50 | mAP50-95 | AP Helmet | Params | FLOPs | RKNN Size | NPU Latency | E2E Latency | FPS | RAM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| YOLOv8n FP16 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv8n INT8 PTQ | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Structured Pruned | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| INT8 + Pruning | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed HW-aware | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

---

## Table L — Operator / Layer Bottleneck Profile

**Mục đích:** rất quan trọng nếu muốn claim hardware-aware contribution.

| Layer / Block | Main Operator | Input Shape | Output Shape | Time / % | NPU Supported? | Layout Conversion? | Observation |
|---|---|---|---|---:|---|---|---|
| Backbone block 1 | Conv | [TBD] | [TBD] | [TBD] | Yes/No | Yes/No | [TBD] |
| Backbone block 2 | [TBD] | [TBD] | [TBD] | [TBD] | Yes/No | Yes/No | [TBD] |
| Neck | Concat/Resize | [TBD] | [TBD] | [TBD] | Yes/No | Yes/No | [TBD] |
| Detect head | Conv | [TBD] | [TBD] | [TBD] | Yes/No | Yes/No | [TBD] |

Các câu hỏi:

```text
Operator nào chiếm nhiều latency?
Có operator nào bị fallback không?
Có layout conversion thừa không?
Block nào FLOPs không cao nhưng latency lại cao?
```

---

## Table M — Hardware Resource Usage

| Method | Avg CPU (%) | Peak CPU (%) | Avg RAM (MB) | Peak RAM (MB) | Temp Start (°C) | Temp End (°C) | Power (W, optional) |
|---|---:|---:|---:|---:|---:|---:|---:|
| FP16 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| INT8 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Proposed | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

---

## Table N — Ablation Study - đề xuất bảng chính trong paper

| Exp | INT8 | Pruning | NPU-friendly Block | Other Change | mAP50 | mAP50-95 | AP Helmet | NPU Latency | FPS |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| Baseline | ✗ | ✗ | ✗ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| A | ✓ | ✗ | ✗ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| B | ✗ | ✓ | ✗ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| C | ✗ | ✗ | ✓ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| D | ✓ | ✓ | ✓ | - | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

Ablation phải giúp trả lời:

```text
INT8 đóng góp bao nhiêu?
Pruning đóng góp bao nhiêu?
New block đóng góp bao nhiêu?
Kết hợp có tốt hơn thật không?
```
---

# 10. Bảng nào thật sự nên xuất hiện trong paper?

### Bắt buộc / rất nên có

```text
Table A  - Dataset summary
Table B  - Training configuration
Table C  - Hardware/software environment
Table E  - Accuracy comparison
Table H  - Accuracy-efficiency comparison
Table N  - Ablation
```

### Rất quan trọng cho hardware-aware paper

```text
Table G  - Latency breakdown
Table L  - Operator / layer bottleneck
Table M  - Resource usage
```
---

# 13. Experimental Plan đề xuất

## Phase 1 — Freeze Protocol

Trước khi benchmark:

```text
freeze dataset
freeze split
freeze class mapping
freeze input size
freeze metric
freeze measurement method
```

Nếu protocol thay đổi giữa các model thì comparison không còn công bằng.

---

## Phase 2 — Full Baseline Benchmark

Đo đầy đủ:

```text
AI:
Precision
Recall
mAP50
mAP50-95
per-class AP

Complexity:
Params
FLOPs/MACs
model size

Hardware:
NPU latency
preprocess
postprocess
E2E
FPS
RAM
CPU
```

---

## Phase 3 — INT8 PTQ

```text
FP16
   ↓
Calibration dataset
   ↓
RKNN INT8 PTQ
   ↓
Full test-set accuracy
   ↓
RK3588S benchmark
```

Phải trả lời:

```text
Latency giảm bao nhiêu?
mAP giảm bao nhiêu?
AP_helmet giảm bao nhiêu?
```

---

## Phase 4 — Multi-model Baseline

Candidate:

```text
YOLOv5n
YOLOv8n
YOLO11n
```

Chỉ chọn model convert/deploy ổn định.

Mục đích:

> Không phụ thuộc vào một baseline duy nhất.

---

## Phase 5 — Bottleneck Analysis

Phân tích:

```text
FLOPs vs real latency
operator latency
layout conversion
memory copy
pre/post overhead
small-object accuracy
```

Đây là phase quyết định research gap.

---

## Phase 6 — Proposed Optimization

Chỉ chọn sau Phase 5.

Candidate:

```text
INT8
structured pruning
NPU-friendly block
lighter detection head
operator replacement
mixed precision
resolution optimization
```

---

## Phase 7 — Ablation

Tách từng contribution.

---

## Phase 8 — Camera / Real-world Evaluation

```text
OV13855
   ↓
NV12
   ↓
RGB
   ↓
Resize / Letterbox
   ↓
RKNN
   ↓
NPU
   ↓
Postprocess
   ↓
Realtime PPE
```

Đo:

```text
FPS
mean latency
P95 latency
CPU
RAM
temperature
stability
```
---

# 19. Figures / biểu đồ nên có trong paper

Ngoài bảng, paper hardware-aware nên có một số figure.

### Figure 1 — Overall System Architecture

### Figure 2 — Research Methodology

### Figure 3 — Accuracy vs Latency Pareto Plot

### Figure 4 — Latency Breakdown

### Figure 5 — Per-class AP Before/After Optimization

### Figure 6 — Operator / Block Profile

---

# 20. Structure paper/report hoàn chỉnh

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

# 21. Định hướng chia Đồ án 2 và ĐATN

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

# 22. Việc nên làm ngay từ trạng thái hiện tại

Thứ tự đề xuất:

```text
1. Freeze SFCHD 3-class split
2. Chạy full test-set evaluation cho YOLOv8n
3. Thu Precision / Recall / mAP / per-class AP
4. Chuẩn hóa latency benchmark trên RK3588S
5. Đo pre/NPU/post/E2E
6. Tạo INT8 PTQ
7. Đánh giá lại full test set
8. So FP16 vs INT8
9. Benchmark thêm 1–2 lightweight model
10. Tìm bottleneck thật
11. Sau đó mới chọn pruning / QAT / architecture change
```
---

> **Mục tiêu không phải tạo model nhỏ nhất hoặc FPS cao nhất bằng mọi giá; mục tiêu là tìm một PPE detector có accuracy đủ tốt và chạy hiệu quả hơn trên RK3588S, với mọi improvement được chứng minh bằng measurement thực tế, comparison công bằng và ablation rõ ràng.**
