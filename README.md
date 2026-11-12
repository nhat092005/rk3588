# rk3588

Meta-repo for the PPE detection on RK3588 project. It only pins the four sub-repos as submodules.

| Path | Repo | Role |
|---|---|---|
| `common/` | `rk3588-common` | Code shared by PC and board (numpy only) |
| `ai/` | `rk3588-ai` | Train, export, evaluate, NPU analysis, experiments |
| `deploy/` | `rk3588-deploy` | C++ app and board-side code |
| `docs/` | `rk3588-docs` | Sphinx documentation |

`tmp/` is local scratch space and is not tracked.

Clone: `git clone --recurse-submodules https://github.com/nhat092005/rk3588`.
Update pins after a sub-repo moves: commit inside the sub-repo, push, then commit the new pointer here.
