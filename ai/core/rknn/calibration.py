"""Calibration image selection utilities for RKNN INT8 quantization."""
from __future__ import annotations

import math
import random
from collections import defaultdict
from pathlib import Path


def sample_calibration_images(
    labels_dir: Path,
    n: int = 100,
    min_per_class: int = 10,
    seed: int = 42,
) -> list[str]:
    """Select calibration image stems, guaranteeing min_per_class per class before filling the rest uniformly."""
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


def write_letterboxed_calib(image_paths: list[Path], out_dir: Path, imgsz: int = 640) -> Path:
    """Write calibration images already letterboxed to imgsz x imgsz as PNG.

    RKNN-Toolkit2 resizes calibration images that differ from the input size in an
    undocumented way, so they are preprocessed here exactly like the evaluator
    (Ultralytics val LetterBox) and stored lossless. Returns the images directory.
    """
    import cv2
    from ultralytics.data.augment import LetterBox

    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    letterbox = LetterBox(new_shape=(imgsz, imgsz), scaleup=False)
    for src in image_paths:
        img = cv2.imread(str(src))
        h0, w0 = img.shape[:2]
        r = imgsz / max(h0, w0)
        if r != 1:  # same long-side resize as BaseDataset.load_image(rect_mode=True)
            img = cv2.resize(img, (min(math.ceil(w0 * r), imgsz), min(math.ceil(h0 * r), imgsz)), interpolation=cv2.INTER_LINEAR)
        cv2.imwrite(str(images_dir / f"{src.stem}.png"), letterbox(image=img))
    return images_dir
