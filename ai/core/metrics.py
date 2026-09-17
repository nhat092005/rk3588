"""Manual mAP/precision/recall computation.

NOT NEEDED YET: the current pipeline (YOLOv8n via ultralytics) already gets
metrics for free from the library's train()/val() API (see core/trainer.py).
This module is only needed once an architecture in research/ stops going
through ultralytics' train API (e.g. a custom forward pass), at which point
mAP must be computed manually to stay comparable in the same leaderboard.
"""
