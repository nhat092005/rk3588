# Research Queue

Tiến độ mở rộng tài liệu (branch `docs/research-expansion`, bắt đầu 2026-09-27).

## Quy trình mỗi paper

1. Tải PDF vào `docs/papers/<topic>/<name>.pdf`
2. Note: `docs/_notes/<topic>/<name>.md` (skill paper-note)
3. Core-value: `docs/outputs/<topic>/<name>.md` (skill paper-synthesizer)
4. Kiểm tra độc lập: đối chiếu mọi con số trong note/core-value với PDF
5. Cập nhật `docs/outputs/<topic>/_synthesis.md`
6. Commit (1 paper = 1 commit)

## Chủ đề ưu tiên

| # | Chủ đề | Thư mục |
|---|---|---|
| 1 | Detector trên RK3588/RKNN, edge NPU | `05_rk3588/` |
| 2 | Detector thân thiện NPU (ReLU, reparam, thay upsample) | `08_npu_friendly_arch/` |
| 3 | PTQ/QAT INT8 cho detection | `02_quantization/` |
| 4 | PPE/helmet nhẹ, chạy trên edge | `07_ppe_detection/` |
| 5 | Latency predictor, benchmark edge | `09_latency_benchmark/` |

## Trạng thái

Trạng thái: `todo` / `wip` (dở, chưa commit) / `done` (đã commit) / `skip` (lý do)

| Paper | Topic | Trạng thái | Ghi chú |
|---|---|---|---|
| edgesoc_benchmark_2026kong | 05_rk3588 | wip | Sci. Rep. 2026, 3 SoC Rockchip |
| rknn_conversion_agent_2026su | 05_rk3588 | todo | arXiv 2609.27249 |
| rk3566_npu_yolo11_2026limaran | 05_rk3588 | todo | TELKOMNIKA 2026 |
| lnbyolo_rk3568_2025zhuo | 05_rk3588 | todo | PLOS ONE 2025 |
| yolov8_rtdetr_energy_2026suchy | 05_rk3588 | todo | Sci. Rep. 2026 |
| yolov5_coral_tpu_2023prokscha | 05_rk3588 | todo | River Publishers OA chapter |
| yolox_hailo8_2024achmadiah | 05_rk3588 | todo | arXiv 2602.10593 |
| ssd_edge_benchmark_2022magalhaes | 05_rk3588 | todo | arXiv 2211.11647 |
| k210_facedetect_2022narduzzi | 05_rk3588 | todo | arXiv 2208.11011 |
| edge_yolo_rk3588_2023 | 05_rk3588 | todo | MDPI Appl. Sci. 2023, cần tra số bài |
| repvgg_reparam_2021ding | 08_npu_friendly_arch | done | arXiv 2101.03697 |
| qarepvgg_quant_2024chu | 08_npu_friendly_arch | done | arXiv 2212.01593 |
| actnas_yolo_2025sah | 08_npu_friendly_arch | todo | CVPRW 2025 |
| yolov6_hwfriendly_2022li | 08_npu_friendly_arch | todo | arXiv 2209.02976 |
| mobileone_reparam_2023vasu | 08_npu_friendly_arch | todo | CVPR 2023 |
| shufflenetv2_guidelines_2018ma | 08_npu_friendly_arch | todo | arXiv 1807.11164 |
| fasternet_pconv_2023chen | 08_npu_friendly_arch | todo | CVPR 2023 |
| dbb_reparam_2021ding | 08_npu_friendly_arch | todo | CVPR 2021 |
| repghost_reparam_2022chen | 08_npu_friendly_arch | todo | arXiv 2211.06088 |
| picodet_mobile_2021yu | 08_npu_friendly_arch | todo | arXiv 2111.00902 |
| rtmdet_realtime_2022lyu | 08_npu_friendly_arch | todo | arXiv 2212.07784 |
| mobilenetv4_2024qin | 08_npu_friendly_arch | todo | ECCV 2024 ecva |
| qyolo_ptq_2023wang | 02_quantization | done | arXiv 2307.04816; verify: sửa 2 page cite, bổ sung RKNN quantized_algorithm ✓API ref p.8 |
| quant_whitepaper_2021nagel | 02_quantization | wip | arXiv 2106.08295 |
| quant_yolov7_2024 | 02_quantization | wip | arXiv 2407.04943 |
| integer_only_quant_2018jacob | 02_quantization | todo | arXiv 1712.05877 |
| fully_quant_od_2019li | 02_quantization | todo | CVPR 2019 CVF |
| taskloss_ptq_od_2023 | 02_quantization | todo | arXiv 2304.09785 |
| brecq_ptq_2021li | 02_quantization | todo | arXiv 2102.05426 |
| adaround_ptq_2020nagel | 02_quantization | todo | arXiv 2004.10568 |
| qdrop_ptq_2022wei | 02_quantization | todo | arXiv 2203.05740 |
| osc_quant_yolo_2023 | 02_quantization | todo | arXiv 2311.05109 |
| lgyolov8_helmet_2024fan | 07_ppe_detection | todo | Appl. Sci. 14(22):10141, mdpi-res |
| helmet_jetsonnano_2023deng | 07_ppe_detection | todo | Hindawi ACE 2023, bị chặn 403 |
| hardhat_yolom3c_2024he | 07_ppe_detection | todo | Electronics 13(13):2507, mdpi-res |
| helmet_yolov4_lite_2023chen | 07_ppe_detection | todo | Sensors 23(3):1256, mdpi-res |
| helmet_yolov5s_kd_2023an | 07_ppe_detection | todo | Sensors 23(13):5824, mdpi-res |
| hardhat_lightweight_cnn_2020wang | 07_ppe_detection | todo | Sensors 20(7):1868, mdpi-res |
| ppe_edgecloud_2023legierski | 07_ppe_detection | todo | arXiv 2301.01501 |
| ppe_visual_detection_2022karlsson | 07_ppe_detection | todo | arXiv 2212.04794 |
| ppe_100fps_2021ke | 07_ppe_detection | todo | PMC8591603, PDF bị chặn 403 |
| nnmeter_latency_2021zhang | 09_latency_benchmark | todo | MobiSys 2021, microsoft.com |
| yolobench_2023lazarevich | 09_latency_benchmark | todo | ICCVW 2023 CVF |
| od_benchmark_embedded_2022cantero | 09_latency_benchmark | todo | Sensors 22(11):4205, mdpi-res |
| hwnasbench_2021li | 09_latency_benchmark | todo | arXiv 2103.10584 |
| mlperf_inference_2020reddi | 09_latency_benchmark | todo | arXiv 1911.02549 |
| mlperf_tiny_2021banbury | 09_latency_benchmark | todo | arXiv 2106.07597 |
| ai_benchmark_mobile_2019ignatov | 09_latency_benchmark | todo | arXiv 1910.06663 |
