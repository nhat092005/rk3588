# css — Data Card

- **Full name:** Construction Site Safety (Roboflow, YOLOv5s export)
- **Source:** https://universe.roboflow.com/roboflow-universe-projects/construction-site-safety
  — published by a Roboflow user (not an academic paper).
- **License:** CC BY 4.0 (stated in `raw/css-data/README.dataset.txt`).
- **Original image sources** (per the README): frames extracted from YouTube videos
  (`watch?v=Dhxf5mm7g1g`, `watch?v=rYv9JZ2XBW4`) plus images merged from several other
  Roboflow projects: `personal-protective-equipment-combined-model`, `people-and-ladders`,
  `safety-vests`, `excavators-cwlh0`, `mit-indoor-scene-recognition` (null/negative
  images), `people-detection-general`, `construction-madness`.
- **Scale:** train 2,605 / valid 114 / test 82 images.
- **10 classes** (`classes.txt`, recovered from the original dataset owner's training
  config — not present in the README, see note below):
  `Hardhat, Mask, NO-Hardhat, NO-Mask, NO-Safety Vest, Person, Safety Cone, Safety Vest,
  machinery, vehicle`.

## Split

`raw/css-data/{train,valid,test}/` is the **fixed split Roboflow created at export
time**; `scripts/data/prepare_css.py` keeps it as-is, no re-splitting.

## Important note

`classes.txt` was **not part of the original download** — it was recovered from a
training config file (`ppe_data.yaml`, part of `results_yolov8n_100e/`, someone else's
training run output) that was deleted during cleanup because it wasn't reusable.
Fortunately the content was read and saved before deletion. Junk removed from the
original download: `source_files/` (demo videos/images, moved to `data/demo/`) and
`results_yolov8n_100e/` (training run output not reusable).
