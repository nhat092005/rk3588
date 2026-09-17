"""Tier 2: manual rknn.api.RKNN pipeline with core_mask / op_target / hybrid
quantization control - the thesis' actual NPU deployment-optimization layer.

Called from npu/experiments/<name>/, one call per configuration being
compared (see npu/README.md). Must not be duplicated per-experiment - all
experiments call into this module so results stay comparable, same rule
core/trainer.py enforces for research/ vs automation/ training runs.

NOT IMPLEMENTED YET. Blocked on:
  1. 3rdparty/rknn-toolkit2 submodule (cloning, size/approach still undecided
     - see tmp/2026-09-17_baseline_rk3588_npu_optimization.md section 9.7).
  2. Shared .venv update to torch==2.4.0+cu124 + numpy<=1.26.4 +
     rknn-toolkit2==2.3.2 - only safe to do after the current YOLOv8n/v8s
     100-epoch training runs finish (see
     tmp/2026-09-17_baseline_rk3588_npu_optimization.md section 9.1).
  3. Choosing the first core_mask/op_target configuration to try.

Will use rknn.calibration.sample_calibration_images() / write_calib_list()
for its calibration set, then call rknn.config() / load_onnx() / build() /
export_rknn() directly (not the ultralytics wrapper in baseline.py), passing
core_mask / op_target through parameters matched to the specific experiment.
"""
from __future__ import annotations


def build_rknn_custom(*args, **kwargs):
    """Convert + quantize with explicit core_mask / op_target / hybrid
    quantization control. See this module's docstring for why it is not
    implemented yet."""
    raise NotImplementedError(
        "Manual RKNN pipeline pending rknn-toolkit2 install and a first "
        "core_mask/op_target configuration to try; see this module's docstring."
    )


def benchmark_on_board(*args, **kwargs):
    """rknn.eval_perf(fix_freq=True) against a real RK3588 board.

    NOT IMPLEMENTED YET. Blocked on board bring-up (owned by the project
    author, not started yet) and on build_rknn_custom() above. See
    tmp/2026-09-17_baseline_rk3588_npu_optimization.md section 6/9.4 for the
    verified API: rknn.eval_perf() requires init_runtime(target='rk3588',
    device_id=...) to have already connected to the board.
    """
    raise NotImplementedError("Needs board bring-up; see this module's docstring.")
