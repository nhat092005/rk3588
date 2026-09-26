# Autonomous Architecture Research Protocol

**Status: INACTIVE.** Requires baseline results in `automation/leaderboards/` before activation.

## Execution Loop

1. Read current best `map50` (eval set `sfchd_test`) from `automation/leaderboards/<dataset>.csv`.
2. Create or modify a draft architecture in `research/experiments/<name>/draft_model.py` and document hypothesis in `notes.md`.
3. Run evaluation via `python -m ai.automation.run` with a fixed epoch/time budget.
4. Compare `map50` (eval set `sfchd_test`) against the baseline and log decision in `notes.md`.
5. Repeat from step 2.

## Activation Prerequisites

- `core/trainer.py` verified functional via `automation/run.py`.
- At least one baseline run logged in `automation/leaderboards/<dataset>.csv`.
- Defined epoch/time budget per iteration.
