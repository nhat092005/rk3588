"""Prepare SHEL5K dataset: converts Pascal VOC XML annotations to YOLO txt and
generates a random 80/10/10 train/val/test split (Mendeley ships no split)."""
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import write_classes, write_dataset_yaml

ROOT = Path(__file__).resolve().parents[2] / "data" / "shel5k"
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"
SEED = 42
RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}


def voc_to_yolo_lines(xml_path: Path, class_index: dict[str, int]) -> list[str]:
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    img_w = int(size.find("width").text)
    img_h = int(size.find("height").text)

    lines = []
    for obj in root.findall("object"):
        name = obj.find("name").text
        if name not in class_index:
            continue
        box = obj.find("bndbox")
        xmin = float(box.find("xmin").text)
        ymin = float(box.find("ymin").text)
        xmax = float(box.find("xmax").text)
        ymax = float(box.find("ymax").text)

        x_center = (xmin + xmax) / 2 / img_w
        y_center = (ymin + ymax) / 2 / img_h
        width = (xmax - xmin) / img_w
        height = (ymax - ymin) / img_h
        lines.append(f"{class_index[name]} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
    return lines


def main() -> None:
    classes = (ROOT / "classes.txt").read_text().splitlines()
    class_index = {name: i for i, name in enumerate(classes)}

    stems = sorted(p.stem for p in (RAW / "images").glob("*.png"))
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
        images_dst_dir = PROCESSED / "images" / split
        labels_dst_dir = PROCESSED / "labels" / split
        images_dst_dir.mkdir(parents=True, exist_ok=True)
        labels_dst_dir.mkdir(parents=True, exist_ok=True)
        for stem in split_list:
            image_src = RAW / "images" / f"{stem}.png"
            image_link = images_dst_dir / image_src.name
            if not image_link.exists():
                image_link.symlink_to(image_src.resolve())

            lines = voc_to_yolo_lines(RAW / "annotations" / f"{stem}.xml", class_index)
            (labels_dst_dir / f"{stem}.txt").write_text("\n".join(lines) + "\n" if lines else "")
        print(f"{split}: {len(split_list)} images")

    write_classes(classes, PROCESSED / "classes.txt")
    write_dataset_yaml(
        PROCESSED / "dataset.yaml",
        PROCESSED,
        classes,
        {"train": "images/train", "val": "images/val", "test": "images/test"},
    )


if __name__ == "__main__":
    main()
