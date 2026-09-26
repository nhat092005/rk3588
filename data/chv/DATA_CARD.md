# chv — Data Card

- **Full name:** CHV (Construction Human and Vest/helmet detection dataset)
- **Source:** paper "Fast Personal Protective Equipment Detection for Real Construction
  Sites Using Deep Learning Approaches" (Wang et al., 2021) —
  `docs/papers/07_ppe_detection/ppe_yolo_chv_2021wang.pdf`, summarized at
  `docs/outputs/07_ppe_detection/ppe_yolo_chv_2021wang.md`.
- **Source images:** selected (1,330 out of more than 10,000) from two open datasets,
  GDUT-HWD and SHWD — per the paper's Data Availability Statement (p.20). BAM Nuttall (UK)
  is an industry partner/co-author affiliation, not the image source.
- **License:** not stated in `raw/CHV_dataset/annotations/README.md` or in the paper as
  summarized — verify before using this beyond personal research.
- **Scale:** 1,330 images, **6 classes** (`classes.txt`, taken from
  `raw/CHV_dataset/annotations/README.md`): `person, vest, blue helmet, red helmet,
  white helmet, yellow helmet`. The paper reports **9,209** instances (p.7: *"CHV dataset
  contain 1330 images, and 9209 instances in total"*). Counting `raw/CHV_dataset/annotations/*.txt`
  per file also gives **9,209** — exact match, no discrepancy.
  Counting pitfall: 73 annotation files have no trailing newline, so `cat *.txt | wc -l`
  undercounts to 9,136. Count per file instead (e.g. `awk 'NF>0' *.txt | wc -l`).
  (An earlier version of this card compared 9,136 against "10,395" — both numbers were
  wrong: 10,395 does not appear in the paper.)
- **Object size:** per Figure 6 (p.8, images resized to 408×408), small (≤32²px) 2,562,
  medium 3,587, large 1,677 — small ≈ 33%, medium is the largest group. The paper only
  says small instances occupy "a large part" of the dataset.

## Split

`raw/CHV_dataset/data split/{train,valid,test}.txt` is the **author-provided split**
(1,064 / 133 / 133 images = 80/10/10, matching the paper's reported ratio).
`scripts/data/prepare_chv.py` uses it as-is, no re-splitting — `valid` is mapped to the
project's `val` directory name, no data is reassigned between splits.

## Cleanup

Junk removed from the original download (zip-extraction artifacts, no dataset value):
`__MACOSX/` and `.DS_Store`.
