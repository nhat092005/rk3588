# npu/

NPU deployment optimization experiments targeting the RK3588 NPU (core scheduling, operator offloading, quantization precision).

## Structure

- `experiments/<name>/`:
  - `notes.md`: Target configuration, hypothesis, and benchmark results.
  - `runs/<date>/`: Artifacts (`calib_list.txt`, `model.rknn`, `npu_benchmark.json`).

Graduated configurations are formalized under `automation/configs/`.
