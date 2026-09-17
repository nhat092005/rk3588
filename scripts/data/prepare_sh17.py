"""data/sh17/raw/ -> data/sh17/processed/

raw/val_files.txt is the author-provided held-out set used to produce
the benchmark numbers in the SH17 paper (TABLE III calls it the "test"
set) -> mapped here to processed test, kept intact so results stay
comparable to the paper.

raw/train_files.txt has no author-provided train/val split, so this
script carves a val set out of it (90/10, seeded) for use during
training. Re-running this script always produces the same split.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import symlink_pair, write_classes, write_dataset_yaml

ROOT = Path(__file__).resolve().parents[2] / "data" / "sh17"
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"
SEED = 42
TRAIN_VAL_RATIO = {"train": 0.9, "val": 0.1}


def find_image(stem: str) -> Path:
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = RAW / "images" / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"no image found for stem {stem}")


def read_stems(list_path: Path) -> list[str]:
    return [Path(line.strip()).stem for line in list_path.read_text().splitlines() if line.strip()]


def write_split(split: str, stems: list[str]) -> None:
    for stem in stems:
        image_src = find_image(stem)
        label_src = RAW / "labels" / f"{stem}.txt"
        symlink_pair(image_src, label_src, PROCESSED / "images" / split, PROCESSED / "labels" / split)
    print(f"{split}: {len(stems)} anh")


def main() -> None:
    classes = (ROOT / "classes.txt").read_text().splitlines()

    trainval_stems = read_stems(RAW / "train_files.txt")
    rng = random.Random(SEED)
    rng.shuffle(trainval_stems)
    n_train = int(len(trainval_stems) * TRAIN_VAL_RATIO["train"])
    write_split("train", trainval_stems[:n_train])
    write_split("val", trainval_stems[n_train:])

    write_split("test", read_stems(RAW / "val_files.txt"))

    write_classes(classes, PROCESSED / "classes.txt")
    write_dataset_yaml(
        PROCESSED / "dataset.yaml",
        PROCESSED,
        classes,
        {"train": "images/train", "val": "images/val", "test": "images/test"},
    )


if __name__ == "__main__":
    main()
