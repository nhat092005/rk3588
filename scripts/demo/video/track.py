"""Render detections.npz as track.mp4: ByteTrack IDs with a smoothing/voting/hold display layer.

The tracker (ultralytics BYTETracker) sees every detection of the frame (det_conf and above); the
display layer then smooths each track's box (mean of the last --smooth boxes), votes its class
(majority of the last --vote classes), only draws a track after --min-hits matched frames, and keeps
drawing its last box for up to --hold frames after the tracker stops returning it.

Usage: python scripts/demo/video/track.py --detections <npz> [--conf 0.25] [--track-buffer 30]
       [--match-thresh 0.8] [--min-hits 3] [--smooth 5] [--vote 15] [--hold 5] [--out out.mp4]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, deque
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
from ultralytics.trackers.byte_tracker import BYTETracker

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import REPO_ROOT, VideoWriter, draw, header, load_json, load_npz  # noqa: E402


class Detections:
    """Tiny Results-like adapter so numpy detections can feed ultralytics.BYTETracker."""

    def __init__(self, xyxy: np.ndarray, conf: np.ndarray, cls: np.ndarray):
        self.xyxy = xyxy
        self.conf = conf
        self.cls = cls

    @property
    def xywh(self) -> np.ndarray:
        x1, y1, x2, y2 = self.xyxy[:, 0], self.xyxy[:, 1], self.xyxy[:, 2], self.xyxy[:, 3]
        w, h = x2 - x1, y2 - y1
        return np.stack([x1 + w / 2, y1 + h / 2, w, h], axis=1)

    def __len__(self) -> int:
        return len(self.xyxy)

    def __getitem__(self, key) -> "Detections":
        return Detections(self.xyxy[key], self.conf[key], self.cls[key])


class TrackDisplay:
    """Per-track smoothing (mean box), class voting (majority), hit-count gate, and hold-after-loss."""

    def __init__(self, smooth: int, vote: int, min_hits: int, hold: int):
        self.smooth, self.vote, self.min_hits, self.hold = smooth, vote, min_hits, hold
        self.boxes: dict[int, deque] = {}
        self.classes: dict[int, deque] = {}
        self.hits: dict[int, int] = {}
        self.last_seen: dict[int, int] = {}
        self.last_box: dict[int, np.ndarray] = {}
        self.last_cls: dict[int, int] = {}
        self.unique_ids_drawn: set[int] = set()

    def update(self, frame_idx: int, rows: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[int]]:
        for x1, y1, x2, y2, tid, _score, cls, _idx in rows:
            tid = int(tid)
            self.boxes.setdefault(tid, deque(maxlen=self.smooth)).append([x1, y1, x2, y2])
            self.classes.setdefault(tid, deque(maxlen=self.vote)).append(int(cls))
            self.hits[tid] = self.hits.get(tid, 0) + 1
            self.last_seen[tid] = frame_idx
            self.last_box[tid] = np.mean(self.boxes[tid], axis=0)
            self.last_cls[tid] = Counter(self.classes[tid]).most_common(1)[0][0]

        for tid in [t for t in self.last_box if frame_idx - self.last_seen[t] > self.hold]:
            del self.boxes[tid], self.classes[tid], self.hits[tid]
            del self.last_seen[tid], self.last_box[tid], self.last_cls[tid]

        draw_boxes, draw_cls, draw_ids = [], [], []
        for tid, box in self.last_box.items():
            if self.hits[tid] < self.min_hits:
                continue
            draw_boxes.append(box)
            draw_cls.append(self.last_cls[tid])
            draw_ids.append(tid)
            self.unique_ids_drawn.add(tid)
        boxes = np.array(draw_boxes, dtype=np.float32) if draw_boxes else np.zeros((0, 4), dtype=np.float32)
        return boxes, np.array(draw_cls, dtype=np.int32), draw_ids


def count_changes(counts: list[int]) -> dict:
    changes = sum(1 for a, b in zip(counts, counts[1:]) if a != b)
    fraction = changes / (len(counts) - 1) if len(counts) > 1 else 0.0
    return {"count": changes, "fraction": round(fraction, 4)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detections", required=True, type=Path)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--track-buffer", type=int, default=30)
    parser.add_argument("--match-thresh", type=float, default=0.8)
    parser.add_argument("--min-hits", type=int, default=3)
    parser.add_argument("--smooth", type=int, default=5)
    parser.add_argument("--vote", type=int, default=15)
    parser.add_argument("--hold", type=int, default=5)
    parser.add_argument("--out")
    args = parser.parse_args()

    meta = load_json(args.detections.with_suffix(".json"))
    det = load_npz(args.detections)
    names = meta["names"]
    n_frames = meta["frames"]

    source = REPO_ROOT / meta["source"]
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {source}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path = Path(args.out) if args.out else args.detections.parent / "track.mp4"
    writer = VideoWriter(out_path, width, height, fps)

    tracker = BYTETracker(SimpleNamespace(
        track_high_thresh=args.conf, track_low_thresh=0.1, new_track_thresh=args.conf,
        track_buffer=args.track_buffer, match_thresh=args.match_thresh, fuse_score=True,
    ))
    display = TrackDisplay(args.smooth, args.vote, args.min_hits, args.hold)

    raw_counts, track_counts = [], []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        m = det["idx"] == i
        dets = Detections(det["boxes"][m], det["conf"][m], det["cls"][m])
        raw_counts.append(int((det["conf"][m] >= args.conf).sum()))

        rows = tracker.update(dets)
        boxes, cls, ids = display.update(i, rows)
        track_counts.append(len(ids))

        labels = [f"{names[c]} #{tid}" for c, tid in zip(cls, ids)]
        draw(frame, boxes, cls, labels)
        header(frame, f"{meta['run_id']} | {meta['tag']} | track | frame {i + 1}/{n_frames}")
        writer.write(frame)
        i += 1
    cap.release()
    writer.close()
    if i != n_frames:
        raise ValueError(f"{source}: decoded {i} frames, detections.json says {n_frames}")

    raw_stats, track_stats = count_changes(raw_counts), count_changes(track_counts)
    stats_path = out_path.with_name("track_stats.json")
    stats_path.write_text(json.dumps({
        "run_id": meta["run_id"], "tag": meta["tag"], "conf": args.conf, "track_buffer": args.track_buffer,
        "match_thresh": args.match_thresh, "min_hits": args.min_hits, "smooth": args.smooth, "vote": args.vote,
        "hold": args.hold, "frames": n_frames, "raw_count_changes": raw_stats, "track_count_changes": track_stats,
        "unique_ids_drawn": len(display.unique_ids_drawn),
    }, indent=2) + "\n")

    print(out_path)
    print(f"raw_count_changes fraction: {raw_stats['fraction']}")
    print(f"track_count_changes fraction: {track_stats['fraction']}")


if __name__ == "__main__":
    main()
