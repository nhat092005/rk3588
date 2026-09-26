"""Prepare CHV dataset: maps author-provided train/valid/test split into processed directory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import symlink_pair, write_classes, write_dataset_yaml

ROOT = Path(__file__).resolve().parents[2] / "data" / "chv"
RAW = ROOT / "raw" / "CHV_dataset"
PROCESSED = ROOT / "processed"
SPLIT_FILES = {"train": "train.txt", "val": "valid.txt", "test": "test.txt"}


def read_stems(list_path: Path) -> list[str]:
    return [Path(line.strip()).stem for line in list_path.read_text().splitlines() if line.strip()]


def main() -> None:
    classes = (ROOT / "classes.txt").read_text().splitlines()

    for split, split_file in SPLIT_FILES.items():
        stems = read_stems(RAW / "data split" / split_file)
        for stem in stems:
            image_src = RAW / "images" / f"{stem}.jpg"
            label_src = RAW / "annotations" / f"{stem}.txt"
            symlink_pair(image_src, label_src, PROCESSED / "images" / split, PROCESSED / "labels" / split)
        print(f"{split}: {len(stems)} images")

    write_classes(classes, PROCESSED / "classes.txt")
    write_dataset_yaml(
        PROCESSED / "dataset.yaml",
        PROCESSED,
        classes,
        {"train": "images/train", "val": "images/val", "test": "images/test"},
    )


if __name__ == "__main__":
    main()
