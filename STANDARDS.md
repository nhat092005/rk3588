# Standards

Rules for every repo of the `rk3588` meta-repo. `make check` enforces the ones a tool can check.

## 1. Roles

| Repo | Responsibility | May import |
|---|---|---|
| `common` (rk3588-common) | Contracts shared by PC and board: model input/output (`model_io`), board telemetry (`board_env`), result provenance (`provenance`). Package `rk3588_common` | numpy, OpenCV (`opencv-python` on the PC, `opencv-python-headless` of the same version on the board), psutil. Nothing of this project |
| `ai` (rk3588-ai) | Datasets, training, export, evaluation, NPU and model measurement, including the research harness that runs on the board (`ai/ai/board/`) | `rk3588_common`, torch, ultralytics, rknn-toolkit2 |
| `deploy` (rk3588-deploy) | The product app (C++ `app/`, board-side `python/`) and the board environment (`sh/` setup, frequency lock, rknn_server, board requirements) | `rk3588_common` (Python). C++ is checked against `rk3588_common` outputs |
| `docs` (rk3588-docs) | Documentation site. Kept as is, pinned | - |
| root | Cross-repo work only: submodule pins, uv workspace, `board.mk`, board sync, this file | - |

The repo is chosen by responsibility, not by where the code runs. Data lives in the repo whose code produced it.

## 2. One home per thing

| Thing | Only home |
|---|---|
| Model I/O constants (`IMGSZ`, `CONF`, `IOU`, ...) and `PROTOCOL_VERSION` | `rk3588_common.model_io` |
| Board address, board directory, sysroot | `board.mk` |
| Paths of ai data and results | `ai/ai/paths.py` |
| Python dependencies and versions | member `pyproject.toml` + root `uv.lock` |
| Lint and format settings | root `ruff.toml` |

A public top-level name (function, class, constant) is defined in one repo only. `tools/check_overlap.py` fails otherwise. When two repos need the same logic, it moves to `common`. Do not copy it.

## 3. Naming

| Item | Rule | Example |
|---|---|---|
| Python module, function, variable | snake_case | `model_io.py`, `postprocess_raw` |
| Python constant | UPPER_CASE | `IMGSZ` |
| Python packages | `ai` (in rk3588-ai), `rk3588_common` | `from rk3588_common.model_io import preprocess` |
| C++ | `deploy/.clang-tidy` | - |
| Training run | `<dataset>_<model>_<N>ep_s<seed>` | `ppe5_yolov8n_baseline_100ep_s0` |
| Experiment directory | `experiments/<domain>/<topic>/<YYYYMMDD>_<slug>/` | `experiments/npu/latency/20261115_core-mask-sweep/` |
| Experiment id | `<topic>-<YYYYMMDD>-<slug>`, one row in `experiments/index.csv` | `latency-20261115-core-mask-sweep` |
| Dates in names | `YYYYMMDD` | `20261113` |

Old experiment codes (`g4`, `q2c`, `x1`, `e2b`, `a9`, ...) appear only in `ai/LEGACY.md`.

## 4. Configuration

| Kind | Where |
|---|---|
| Training and evaluation run | yaml in `ai/ai/automation/configs/` |
| Acceptance profile | yaml in `ai/ai/automation/profiles/` |
| Machine and board | Makefile variables (`board.mk`), overridable on the command line |
| Contract values (shapes, thresholds that define a protocol) | constants in code, at their single home |

No absolute paths in tracked files or in data manifests (`dataset.yaml`, symlinks). Paths are relative to the repo root.

## 5. Data flow

```text
data/<ds>/raw -> scripts/data/prepare_<ds>.py -> data/<ds>/processed (relative links)
  -> train -> experiments/runs/<run_id>/
  -> evaluate / export / bench -> JSON with provenance
  -> experiments/leaderboards/<ds>.csv, experiments/index.csv
  -> results/<ds>/ tables
```

Board results are copied back into the repo whose code produced them. Every result file carries the provenance of `rk3588_common.provenance`: `repos` (commit and dirty flag of each repo whose code ran), `created_at`, `run_id`, `tier`, `protocol_version`, `model_file`, `model_sha256`. The board has no git checkout, so board scripts receive the PC repo state as arguments.

## 6. Environment and commands

| Command | Action |
|---|---|
| `make init` | Submodules, sparse rknn-toolkit2 (headers and two wheels) |
| `make sync` | One `.venv` for `common` and `ai` from `uv.lock` |
| `make check` | ruff lint and format, overlap check, path check, tests of each repo |
| `make sync-board`, `make setup-board`, `make check-board` | Copy to `~/rk3588-board/` (meta-repo layout), build the board venv, run the board checks |

- PC Python 3.12. Board Python 3.10: `common/`, `ai/ai/board/` and `deploy/python/` must stay 3.10 compatible (ruff `per-file-target-version`).
- ai commands run from `ai/` (`../.venv/bin/python -m ai.<module>`). The ai project is not installed, `rk3588_common` is (editable).
- Exact pins where results depend on the version: torch, ultralytics, onnx, onnxslim, rknn-toolkit2.

## 7. Language

Identifiers, comments, READMEs and commit messages are in English. Research notes may be in Vietnamese.

## 8. Migration from legacy

The old repo is frozen at tag `legacy-final` (GitHub `nhat092005/rk3588-legacy`). It is never edited again.

- One piece per step: branch `migrate/<piece>` in the child repo, pull request reviewed by the owner, then the root pin is bumped.
- The commit body cites the source as `legacy-final:<path>`.
- A migration pull request only moves, renames, deduplicates and applies these standards. Output must stay identical, proven by tests against fixtures produced by the legacy code. Behavior changes come in a later, separate pull request.
- Lines of work not yet migrated (research, gates, camera app, demos) are migrated right before work on them resumes.
- Closed experiments stay in `legacy-final`. `ai/LEGACY.md` maps their codes to legacy paths.
