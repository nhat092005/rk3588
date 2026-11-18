# Entry point of the meta-repo. Run `make init` once after a plain `git clone`.
.PHONY: init sync check docs sysroot build-board sync-board sync-board-py setup-board check-board

include board.mk

# bash: check-board uses process substitution
SHELL := /bin/bash

BUILD_ARM   := deploy/build-arm
MAX_GLIBC   ?= 2.35

RKNN_URL     := https://github.com/airockchip/rknn-toolkit2
RKNN_DIR     := 3rdparty/rknn-toolkit2
RKNN_TAG     := v2.3.2
RKNN_API_DIR := rknpu2/runtime/Linux/librknn_api/include
# Only these two of the 15 wheels (269 MB) are needed: PC rknn-toolkit2 (Python 3.12) and board RKNN-Toolkit-Lite2 (3.10)
RKNN_PC_WHEEL    := rknn-toolkit2/packages/x86_64/rknn_toolkit2-2.3.2-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
RKNN_BOARD_WHEEL := rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.3.2-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

VENV := .venv/bin

BOARD_BINARIES := app/rk3588_deploy probes/device/probe_link probes/device/probe_infer probes/device/probe_camera probes/device/probe_dmabuf probes/stage/probe_letterbox probes/stage/probe_jpeg probes/stage/probe_overlay probes/stage/probe_h265 probes/pipeline/probe_threads probes/pipeline/probe_output probes/pipeline/probe_disk_write probes/stage/probe_tracker test/logger/test_logger test/dmabuf/test_dmabuf test/rga/test_letterbox_layout test/rga/test_box_mapper test/rga/test_rga_letterbox test/npu/test_npu_infer test/postproc/test_postprocess test/tracker/test_tracker test/rule/test_violation_rule test/rga/test_rga_snapshot test/rga/test_rga_overlay test/rga/test_rga_labels test/label/test_label_text test/jpeg/test_jpeg_encoder test/video/test_video_encoder test/video/test_hevc_nal test/options/test_app_options test/stats/test_stage_stats test/os/test_mailbox test/clip/test_clip_recorder test/store/test_violation_retention test/record/test_packet_queue test/record/test_segment_writer test/record/test_recording_retention test/store/test_volume test/store/test_violation_store

# rknn-toolkit2 is about 2 GB. `git submodule update` would check out all of it before any sparse rule applies,
# so the first clone is done here (blobless + sparse: headers and two wheels, about 40 MB). The commit must equal the pin.
init:
	git submodule update --init common ai deploy docs
	@[ -e $(RKNN_DIR)/.git ] || git clone -q --filter=blob:none --sparse --depth 1 --branch $(RKNN_TAG) $(RKNN_URL) $(RKNN_DIR)
	git -C $(RKNN_DIR) sparse-checkout set --no-cone /$(RKNN_API_DIR)/ /$(RKNN_PC_WHEEL) /$(RKNN_BOARD_WHEEL)
	@git submodule status $(RKNN_DIR)

# One .venv for common and ai (uv workspace, see pyproject.toml). Run after make init.
sync:
	uv sync --all-packages

# Gate of STANDARDS.md: lint, format, shellcheck, one home per name, no absolute or legacy paths, tests of each repo.
# shellcheck: uv tool install shellcheck-py (config deploy/.shellcheckrc).
check:
	$(VENV)/ruff check common ai deploy tools
	$(VENV)/ruff format --check common ai deploy tools
	shellcheck deploy/sh/*/*.sh
	$(VENV)/python tools/check_overlap.py
	@for r in . common ai deploy; do \
		git -C $$r grep -nI -e '/home/' -e '\.\./rk3588-legacy' -- . ':!Makefile' ':!docs' ':!3rdparty' \
		&& { echo "ERROR: absolute or legacy path in tracked files of $$r"; exit 1; }; \
	done; true
	@for r in common ai; do (cd $$r && ../$(VENV)/python -m pytest -q tests) || [ $$? -eq 5 ] || exit 1; done

# Copy the board's headers and libs to the PC (about 2 GB, incremental). Redo after a board OS or librknnrt change.
sysroot:
	mkdir -p $(SYSROOT)/usr
	ln -sfn usr/lib $(SYSROOT)/lib
	rsync -a --info=stats1 --exclude='libLLVM*' --exclude='dri/' --exclude='python3*' --exclude='firmware/' --exclude='modules/' \
		--exclude='libgallium*' --exclude='gstreamer*' --exclude='systemd/' --exclude='udev/' --exclude='samba/' --exclude='cups/' \
		$(BOARD):/usr/include $(BOARD):/usr/lib $(SYSROOT)/usr/

# Cross-compile deploy/ for the board, then fail if any binary needs a glibc newer than the board has.
build-board:
	$(MAKE) -C deploy build BUILD_DIR=build-arm BUILD_TYPE=Release CMAKE_ARGS=-DRK3588_SYSROOT=$(SYSROOT)
	@for bin in $(BOARD_BINARIES); do \
		needed=$$(aarch64-linux-gnu-objdump -T $(BUILD_ARM)/$$bin | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -V | tail -1); \
		highest=$$(printf '%s\n%s\n' "$$needed" "$(MAX_GLIBC)" | sort -V | tail -1); \
		echo "$$bin needs GLIBC_$$needed (board has $(MAX_GLIBC))"; \
		[ "$$highest" = "$(MAX_GLIBC)" ] || { echo "ERROR: $$bin needs a newer glibc than the board"; exit 1; }; \
	done

# Fill ~/$(BOARD_DIR) on the board with the meta-repo layout. sync-board-py: everything but the binaries
# (deploy/sh, deploy/python, deploy/tools, deploy/requirements-board.txt, common/python, common/tests, ai/ai/board, the
# RKNN-Toolkit-Lite2 wheel). sync-board: that plus the cross-built deploy/bin. Separate from the legacy ~/rk3588.
RSYNC := rsync -a --delete --exclude __pycache__ --exclude '*.egg-info' --exclude .gitkeep
sync-board-py:
	ssh $(BOARD) 'mkdir -p $(BOARD_DIR)/deploy $(BOARD_DIR)/common $(BOARD_DIR)/ai/ai $(BOARD_DIR)/$(RKNN_DIR)/$(dir $(RKNN_BOARD_WHEEL))'
	$(RSYNC) deploy/sh/ $(BOARD):$(BOARD_DIR)/deploy/sh/
	$(RSYNC) deploy/python/ $(BOARD):$(BOARD_DIR)/deploy/python/
	$(RSYNC) deploy/tools/ $(BOARD):$(BOARD_DIR)/deploy/tools/
	rsync -a deploy/requirements-board.txt $(BOARD):$(BOARD_DIR)/deploy/
	$(RSYNC) common/python/ $(BOARD):$(BOARD_DIR)/common/python/
	$(RSYNC) common/tests/ $(BOARD):$(BOARD_DIR)/common/tests/
	rsync -a ai/ai/__init__.py $(BOARD):$(BOARD_DIR)/ai/ai/
	$(RSYNC) ai/ai/board/ $(BOARD):$(BOARD_DIR)/ai/ai/board/
	rsync -a $(RKNN_DIR)/$(RKNN_BOARD_WHEEL) $(BOARD):$(BOARD_DIR)/$(RKNN_DIR)/$(RKNN_BOARD_WHEEL)

sync-board: build-board sync-board-py
	ssh $(BOARD) 'mkdir -p $(BOARD_DIR)/deploy/bin'
	rsync -a $(BUILD_ARM)/app/rk3588_deploy $(BOARD):$(BOARD_DIR)/deploy/bin/
	cd $(BUILD_ARM) && rsync -aR $(filter-out app/%,$(BOARD_BINARIES)) $(BOARD):$(BOARD_DIR)/deploy/bin/

# Create or update the board venv ~/$(BOARD_DIR)/.venv (no sudo, needs internet on the board). Run after sync-board.
setup-board:
	ssh $(BOARD) 'bash $(BOARD_DIR)/deploy/sh/env/setup_board.sh'

# On the board: installed lock_freq.sh has the code of deploy/sh/env/lock_freq.sh, rk3588_common tests pass, C++ tests pass.
# Run sync-board first. BOARD_MODEL is the .rknn of test_npu_infer (skipped when the file does not exist).
BOARD_MODEL ?= ~/$(BOARD_DIR)/rknn/best-rk3588.rknn
check-board:
	@diff <(grep -v '^\s*#' deploy/sh/env/lock_freq.sh) <(ssh $(BOARD) "grep -v '^\s*#' /usr/local/sbin/lock_freq.sh") \
		&& echo "lock_freq.sh: installed code equals deploy/sh/env/lock_freq.sh" \
		|| { echo "ERROR: /usr/local/sbin/lock_freq.sh differs, reinstall it with sudo"; exit 1; }
	ssh $(BOARD) 'cd $(BOARD_DIR)/common && ../.venv/bin/python -m pytest -q -p no:cacheprovider tests'
	ssh $(BOARD) 'bash $(BOARD_DIR)/deploy/sh/env/run_tests.sh $(BOARD_MODEL)'

# Build and serve Sphinx docs at http://localhost:8000 (bootstraps docs/.venv on first run).
docs: docs/.venv/bin/sphinx-build
	$(MAKE) -C docs check
	docs/.venv/bin/python -m http.server -d docs/_build/html 8000

docs/.venv/bin/sphinx-build: docs/requirements.txt
	uv venv docs/.venv
	uv pip install --python docs/.venv/bin/python -r docs/requirements.txt
	@touch $@
