# shel5k — Data Card

- **Full name:** SHEL5K (Safety HELmet dataset with 5K images)
- **Source:** paper "SHEL5K: An Extended Dataset and Benchmarking for Safety Helmet
  Detection" (Otgonbold et al., 2022) —
  `docs/papers/07_ppe_detection/shel5k_helmet_2022otgonbold.pdf`, summarized at
  `docs/outputs/07_ppe_detection/shel5k_helmet_2022otgonbold.md`.
- **Source images:** re-labeled from Kaggle's "Hard Hat Detection" (SHD) dataset
  (`kaggle.com/andrewmvd/hard-hat-detection`), which itself has only 3 classes and is
  incompletely labeled.
- **Download:** Mendeley Data, DOI `10.17632/9rcv8mm682.4` (version 4, latest,
  published 2022-02-14), `https://data.mendeley.com/datasets/9rcv8mm682`.
- **License:** CC BY 4.0 (confirmed via Mendeley's public API metadata for this
  dataset).
- **Scale:** 5,000 images, **6 classes** (`classes.txt`): `helmet, head,
  head_with_helmet, person_with_helmet, person_no_helmet, face`. Raw annotations total
  75,578 labeled objects — matches the paper exactly.
- **Data quality note:** 8 of the 75,578 raw objects are labeled `person`, a stray
  label from the original 3-class SHD scheme that was not converted to the new 6-class
  taxonomy (not one of the 6 official classes). `scripts/data/prepare_shel5k.py` drops
  these 8 objects during VOC-to-YOLO conversion rather than guessing which of
  `person_with_helmet`/`person_no_helmet` they should map to — processed labels total
  75,570 objects.

## Download reliability warning

Mendeley's web UI "Download All" zip button served **stale/incorrect content**: the
downloaded zip's `images/`+`annotations/` matched the original 3-class SHD dataset
(3 classes, ~25K objects), not the 6-class SHEL5K described on the same page. This was
caught by diffing a sample annotation's object count against the page's own stated
scale. The fix: fetch each of the 10,000 files individually via Mendeley's public API
(`https://data.mendeley.com/public-api/datasets/9rcv8mm682` for the file list, then
each file's `content_details.download_url`) — confirmed correct (6 classes, 75,578
labels, matches the paper). If re-downloading this dataset in the future, verify class
count in a sample annotation before trusting the zip.

## Format

Raw annotations are **Pascal VOC XML** (`raw/annotations/*.xml`), not YOLO txt like the
other datasets in this project. `scripts/data/prepare_shel5k.py` converts VOC bounding
boxes to normalized YOLO format when generating `processed/labels/`.

## Split

Mendeley ships no train/val/test split (flat `images/`+`annotations/` only). The paper
itself uses an 80:20 (4,000 train : 1,000 test) split with no val set.
`scripts/data/prepare_shel5k.py` instead generates an 80/10/10 random split (seed=42),
matching this project's convention for datasets with no author-provided split (see
`sfchd`'s `DATA_CARD.md`) — not directly comparable to the paper's reported numbers.
