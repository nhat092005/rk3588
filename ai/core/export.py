"""Convert a model to RKNN, benchmark it on the RK3588 NPU (layer 2).

NOT IMPLEMENTED YET. Will be written once at least one baseline has finished
training in automation/ and we need latency/FPS/mAP-drop-under-INT8-quant
numbers from real hardware or the RKNN simulator. Once done, automation/run.py
will call this module and write the result to
automation/runs/<run_id>/npu_benchmark.json.
"""
