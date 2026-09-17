"""Calibration image selection for RKNN INT8 quantization.

No dependency on rknn-toolkit2 - pure stdlib, so this is testable and stable
regardless of whether the RKNN environment is set up yet. Used by both
rknn/baseline.py (Tier 1) and rknn/deploy.py (Tier 2).
"""
from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path


def sample_calibration_images(
    labels_dir: Path,
    n: int = 100,
    min_per_class: int = 10,
    seed: int = 42,
) -> list[str]:
    """Pick calibration images, guaranteeing coverage of rare classes.

    Plain random sampling risks under-representing rare classes in an
    imbalanced dataset. Example: sfchd's "self_clothes" appears in only
    5.91% of train images - with n=100 pure random, there is a ~16% chance
    of ending up with <=3 images containing it (Poisson, lambda=5.91). See
    tmp/2026-09-17_baseline_rk3588_npu_optimization.md section 9.3 for the
    full calculation. Rarest classes are filled first here, guaranteeing at
    least min_per_class images each, before the remaining slots are filled
    randomly.

    Args:
        labels_dir: directory of YOLO .txt label files, e.g.
            data/<name>/processed/labels/train/.
        n: total number of images to return.
        min_per_class: minimum images guaranteed per class, rarest first.
        seed: for reproducibility.

    Returns:
        Image stems (filename without extension), length <= n.
    """
    rng = random.Random(seed)
    class_to_images: dict[int, set[str]] = defaultdict(set)
    all_images: list[str] = []

    for label_file in sorted(labels_dir.glob("*.txt")):
        classes = {int(line.split()[0]) for line in label_file.read_text().splitlines() if line.strip()}
        all_images.append(label_file.stem)
        for c in classes:
            class_to_images[c].add(label_file.stem)

    selected: set[str] = set()
    for c in sorted(class_to_images, key=lambda c: len(class_to_images[c])):
        candidates = list(class_to_images[c] - selected)
        rng.shuffle(candidates)
        selected.update(candidates[:min_per_class])

    remaining = [img for img in all_images if img not in selected]
    rng.shuffle(remaining)
    selected.update(remaining[: max(0, n - len(selected))])

    return list(selected)[:n]


def write_calib_list(image_stems: list[str], images_dir: Path, out_path: Path) -> Path:
    """Write the calibration image list RKNN-Toolkit2's build(dataset=...) arg
    expects: one absolute image path per line."""
    paths = [str(images_dir / f"{stem}.jpg") for stem in image_stems]
    out_path.write_text("\n".join(paths) + "\n")
    return out_path
