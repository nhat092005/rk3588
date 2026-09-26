"""Prepare SFCHD with the 5-class scope (drop blur_head/blur_clothes).

Reuses the 80/10/10 split of data/sfchd/processed/ and the class mapping of
prepare_sfchd_shel5k.py, so class indices match data/sfchd_shel5k/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_classes, write_dataset_yaml
from prepare_sfchd_shel5k import CLASSES, SPLITS, check_source_classes, merge_split

OUT = Path(__file__).resolve().parents[2] / "data" / "sfchd_5class" / "processed"


def main() -> None:
    check_source_classes("sfchd")

    for split in SPLITS:
        images_dst = OUT / "images" / split
        labels_dst = OUT / "labels" / split
        images_dst.mkdir(parents=True, exist_ok=True)
        labels_dst.mkdir(parents=True, exist_ok=True)
        print(f"{split}: {merge_split('sfchd', split, images_dst, labels_dst)} images")

    write_classes(CLASSES, OUT / "classes.txt")
    write_dataset_yaml(
        OUT / "dataset.yaml",
        OUT,
        CLASSES,
        {"train": "images/train", "val": "images/val", "test": "images/test"},
    )


if __name__ == "__main__":
    main()
