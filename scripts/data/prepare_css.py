"""data/css/raw/ -> data/css/processed/

raw/css-data/{train,valid,test}/ is the split already fixed by Roboflow
when the dataset was exported. This script only reorganizes files into
that split, it never re-shuffles them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import symlink_pair, write_classes, write_dataset_yaml

ROOT = Path(__file__).resolve().parents[2] / "data" / "css"
RAW = ROOT / "raw" / "css-data"
PROCESSED = ROOT / "processed"
SPLIT_DIRS = {"train": "train", "val": "valid", "test": "test"}


def main() -> None:
    classes = (ROOT / "classes.txt").read_text().splitlines()

    for split, raw_dir_name in SPLIT_DIRS.items():
        images_src_dir = RAW / raw_dir_name / "images"
        labels_src_dir = RAW / raw_dir_name / "labels"
        count = 0
        for image_src in sorted(images_src_dir.glob("*.jpg")):
            label_src = labels_src_dir / f"{image_src.stem}.txt"
            symlink_pair(image_src, label_src, PROCESSED / "images" / split, PROCESSED / "labels" / split)
            count += 1
        print(f"{split}: {count} anh")

    write_classes(classes, PROCESSED / "classes.txt")
    write_dataset_yaml(
        PROCESSED / "dataset.yaml",
        PROCESSED,
        classes,
        {"train": "images/train", "val": "images/val", "test": "images/test"},
    )


if __name__ == "__main__":
    main()
