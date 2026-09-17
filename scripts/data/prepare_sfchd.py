"""data/sfchd/raw/ -> data/sfchd/processed/

raw/ has no author-provided split, so this script creates one: random
80/10/10 train/val/test, seeded for reproducibility. Re-running this
script always produces the same split.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import symlink_pair, write_classes, write_dataset_yaml

ROOT = Path(__file__).resolve().parents[2] / "data" / "sfchd"
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"
SEED = 42
RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}


def main() -> None:
    classes = (RAW / "classes.txt").read_text().splitlines()
    stems = sorted(p.stem for p in (RAW / "images").glob("*.jpg"))

    rng = random.Random(SEED)
    rng.shuffle(stems)
    n_train = int(len(stems) * RATIOS["train"])
    n_val = int(len(stems) * RATIOS["val"])
    split_stems = {
        "train": stems[:n_train],
        "val": stems[n_train : n_train + n_val],
        "test": stems[n_train + n_val :],
    }

    for split, split_list in split_stems.items():
        for stem in split_list:
            image_src = RAW / "images" / f"{stem}.jpg"
            label_src = RAW / "labels" / f"{stem}.txt"
            symlink_pair(image_src, label_src, PROCESSED / "images" / split, PROCESSED / "labels" / split)
        print(f"{split}: {len(split_list)} anh")

    write_classes(classes, PROCESSED / "classes.txt")
    write_dataset_yaml(
        PROCESSED / "dataset.yaml",
        PROCESSED,
        classes,
        {"train": "images/train", "val": "images/val", "test": "images/test"},
    )


if __name__ == "__main__":
    main()
