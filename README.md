# rk3588

Meta-repo for the PPE detection on RK3588 project. It only pins the four sub-repos as submodules.

| Path | Repo | Role |
|---|---|---|
| `common/` | `rk3588-common` | Code shared by PC and board (numpy only) |
| `ai/` | `rk3588-ai` | Train, export, evaluate, NPU analysis, experiments |
| `deploy/` | `rk3588-deploy` | C++ app and board-side code |
| `docs/` | `rk3588-docs` | Sphinx documentation |
| `3rdparty/rknn-toolkit2/` | `airockchip/rknn-toolkit2` at `v2.3.2` | `rknn_api.h` for the C++ code. Rockchip headers are proprietary, so they are referenced, not copied |

`tmp/` is local scratch space and is not tracked.

Clone: `git clone https://github.com/nhat092005/rk3588`, then `make init`. A plain `--recurse-submodules` would also download all of rknn-toolkit2 (about 2 GB), `make init` takes only `rknn_api.h` (about 600 KB).
Update pins after a sub-repo moves: commit inside the sub-repo, push, then commit the new pointer here.
