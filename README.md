# rk3588

Meta-repo for the PPE detection on RK3588 project. It pins the sub-repos as submodules and holds the cross-repo pieces: the rules in `STANDARDS.md`, the uv workspace (`pyproject.toml`, `uv.lock`), board settings (`board.mk`), lint settings (`ruff.toml`) and `tools/`.

| Path | Repo | Role |
|---|---|---|
| `common/` | `rk3588-common` | Contracts shared by PC and board (package `rk3588_common`) |
| `ai/` | `rk3588-ai` | Train, export, evaluate, NPU analysis, experiments |
| `deploy/` | `rk3588-deploy` | C++ app and board-side code |
| `docs/` | `rk3588-docs` | Sphinx documentation |
| `3rdparty/rknn-toolkit2/` | `airockchip/rknn-toolkit2` at `v2.3.2` | `rknn_api.h` for the C++ code, rknn-toolkit2 (PC) and RKNN-Toolkit-Lite2 (board) wheels. Rockchip files are proprietary, so they are referenced, not copied |

`tmp/` is local scratch space and is not tracked.

Clone: `git clone https://github.com/nhat092005/rk3588`, then `make init` and `make sync`. A plain `--recurse-submodules` would also download all of rknn-toolkit2 (about 2 GB), `make init` takes only the headers and the two wheels (about 40 MB).
Update pins after a sub-repo moves: commit inside the sub-repo, push, then commit the new pointer here.

## Targets

| Command | Action |
|---|---|
| `make init` | Init submodules, fetch only the headers and two wheels of rknn-toolkit2 |
| `make sync` | Create or update `.venv` for `common` and `ai` from `uv.lock` (needs `uv`) |
| `make check` | Lint, format check, overlap check, path check, tests (see `STANDARDS.md`) |
| `make sysroot` | Copy the board's `/usr/include` and `/usr/lib` to `~/sysroots/orangepi5` (about 2 GB, incremental) |
| `make build-board` | Cross-compile `deploy/` for the board, fail if a binary needs glibc newer than the board (`MAX_GLIBC`, default 2.35) |
| `make sync-board` | Build, then copy binaries to `~/rk3588-deploy/bin/` and `common/python/` to `~/rk3588-deploy/common/python/` on the board |

Board address and directories are in `board.mk`, override with `BOARD=user@host`. Needs `g++-11-aarch64-linux-gnu` on the PC.
