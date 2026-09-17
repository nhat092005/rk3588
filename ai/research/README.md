# research/

Experimental architecture workspace.

## Structure

- `notebooks/`: Exploratory analysis and ablations.
- `experiments/<name>/`:
  - `notes.md`: Hypothesis, rationale, and preliminary metrics.
  - `draft_model.py`: Draft model architecture.

All training must use `core/trainer.py`. Models that outperform baseline benchmarks graduate to `models/` with an official config in `automation/configs/`.
