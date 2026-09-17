"""Custom RKNN conversion and deployment pipeline.

Provides manual RKNN compilation with fine-grained control over operator
targeting (op_target) and hybrid quantization.
"""
from __future__ import annotations


def build_rknn_custom(*args, **kwargs):
    """Convert and quantize model with custom operator targeting and quantization."""
    raise NotImplementedError(
        "Manual RKNN pipeline pending a first op_target configuration to try."
    )
