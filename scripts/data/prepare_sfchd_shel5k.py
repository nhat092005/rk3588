"""Merge sfchd + shel5k into a unified 5-class dataset.

Reads data/{sfchd,shel5k}/processed/ (already split 80/10/10), remaps and
filters label classes, and writes data/sfchd_shel5k/processed/. See
data/CLASS_MAPPING.md for the mapping and its rationale.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_classes, write_dataset_yaml

ROOT = Path(__file__).resolve().parents[2] / "data"
OUT = ROOT / "sfchd_shel5k" / "processed"
SPLITS = ["train", "val", "test"]

CLASSES = ["person", "helmet", "head", "safety_clothes", "self_clothes"]

# Source class order this script was written against (see data/CLASS_MAPPING.md).
# Checked at runtime so a reordering of a source classes.txt fails loudly
# instead of silently mislabeling the merged dataset.
EXPECTED_SOURCE_CLASSES = {
    "sfchd": ["person", "helmet", "self_clothes", "safety_clothes", "head", "blur_head", "blur_clothes"],
    "shel5k": ["helmet", "head", "head_with_helmet", "person_with_helmet", "person_no_helmet", "face"],
}

# old class index -> new class index, or None to drop the object
REMAP = {
    "sfchd": {0: 0, 1: 1, 2: 4, 3: 3, 4: 2, 5: None, 6: None},
    "shel5k": {0: 1, 1: 2, 2: None, 3: 0, 4: 0, 5: None},
}


def check_source_classes(name: str) -> None:
    actual = (ROOT / name / "processed" / "classes.txt").read_text().splitlines()
    expected = EXPECTED_SOURCE_CLASSES[name]
    if actual != expected:
        raise ValueError(
            f"{name}/processed/classes.txt changed order/content.\n"
            f"expected: {expected}\ngot: {actual}\n"
            f"Update REMAP in this script and data/CLASS_MAPPING.md to match."
        )


def remap_label_file(src: Path, mapping: dict) -> list[str]:
    lines_out = []
    for line in src.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split()
        new_idx = mapping.get(int(parts[0]))
        if new_idx is None:
            continue
        lines_out.append(" ".join([str(new_idx)] + parts[1:]))
    return lines_out


def merge_split(name: str, split: str, images_dst: Path, labels_dst: Path) -> int:
    src_images = ROOT / name / "processed" / "images" / split
    src_labels = ROOT / name / "processed" / "labels" / split
    mapping = REMAP[name]

    count = 0
    for image_src in sorted(src_images.iterdir()):
        label_src = src_labels / f"{image_src.stem}.txt"
        if not label_src.exists():
            continue

        dst_stem = f"{name}_{image_src.stem}"
        image_dst = images_dst / f"{dst_stem}{image_src.suffix}"
        if not image_dst.exists():
            image_dst.symlink_to(image_src.resolve())

        new_lines = remap_label_file(label_src, mapping)
        label_dst = labels_dst / f"{dst_stem}.txt"
        label_dst.write_text("\n".join(new_lines) + ("\n" if new_lines else ""))
        count += 1
    return count


def main() -> None:
    for name in REMAP:
        check_source_classes(name)

    for split in SPLITS:
        images_dst = OUT / "images" / split
        labels_dst = OUT / "labels" / split
        images_dst.mkdir(parents=True, exist_ok=True)
        labels_dst.mkdir(parents=True, exist_ok=True)

        total = sum(merge_split(name, split, images_dst, labels_dst) for name in REMAP)
        print(f"{split}: {total} images")

    # SHEL5K-only test list: extra eval set "shel5k_test" for Option 2 models (ai/core/evaluator.py)
    shel5k_test = sorted((OUT / "images" / "test").glob("shel5k_*"))
    (OUT / "test_shel5k.txt").write_text("".join(f"./images/test/{f.name}\n" for f in shel5k_test))
    print(f"test_shel5k: {len(shel5k_test)} images")

    write_classes(CLASSES, OUT / "classes.txt")
    write_dataset_yaml(
        OUT / "dataset.yaml",
        OUT,
        CLASSES,
        {"train": "images/train", "val": "images/val", "test": "images/test", "test_shel5k": "test_shel5k.txt"},
    )


if __name__ == "__main__":
    main()
