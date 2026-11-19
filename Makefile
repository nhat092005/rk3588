# Entry point of the meta-repo. Run `make init` once after a plain `git clone`.
.PHONY: init sync check docs sysroot build-board sync-board sync-board-py setup-board check-board

include board.mk

# bash: check-board uses process substitution
SHELL := /bin/bash

BUILD_ARM := deploy/build-arm
STAGE     := $(BUILD_ARM)/stage
MAX_GLIBC ?= 2.35

RKNN_URL     := https://github.com/airockchip/rknn-toolkit2
RKNN_DIR     := 3rdparty/rknn-toolkit2
RKNN_TAG     := v2.3.2
RKNN_API_DIR := rknpu2/runtime/Linux/librknn_api/include
# Two of the 15 wheels: rknn-toolkit2 for the PC (Python 3.12), RKNN-Toolkit-Lite2 for the board (3.10).
RKNN_PC_WHEEL    := rknn-toolkit2/packages/x86_64/rknn_toolkit2-2.3.2-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
RKNN_BOARD_WHEEL := rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.3.2-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

VENV := .venv/bin

# rknn-toolkit2 is 2 GB, so it is cloned here, sparse (headers and two wheels, 40 MB), and not by
# `git submodule update`, which would check out all of it. The commit must equal the pin.
init:
	git submodule update --init common ai deploy docs
	@[ -e $(RKNN_DIR)/.git ] || git clone -q --filter=blob:none --sparse --depth 1 \
		--branch $(RKNN_TAG) $(RKNN_URL) $(RKNN_DIR)
	git -C $(RKNN_DIR) sparse-checkout set --no-cone \
		/$(RKNN_API_DIR)/ /$(RKNN_PC_WHEEL) /$(RKNN_BOARD_WHEEL)
	@git submodule status $(RKNN_DIR)

# One .venv for common and ai (uv workspace, see pyproject.toml). Run after make init.
sync:
	uv sync --all-packages

# Gate of STANDARDS.md: lint, format, shellcheck, one home per name, no absolute or legacy paths,
# tests of each repo. shellcheck: uv tool install shellcheck-py (config deploy/.shellcheckrc).
check:
	$(VENV)/ruff check common ai deploy tools
	$(VENV)/ruff format --check common ai deploy tools
	shellcheck deploy/sh/*/*.sh
	$(VENV)/python tools/check_overlap.py
	@for r in . common ai deploy; do \
		git -C $$r grep -nI -e '/home/' -e '\.\./rk3588-legacy' \
			-- . ':!Makefile' ':!docs' ':!3rdparty' \
		&& { echo "ERROR: absolute or legacy path in tracked files of $$r"; exit 1; }; \
	done; true
	@for r in common ai; do \
		(cd $$r && ../$(VENV)/python -m pytest -q tests) || [ $$? -eq 5 ] || exit 1; \
	done

# Copy the board's headers and libs to the PC (2 GB, incremental).
# Redo after a board OS or librknnrt change.
SYSROOT_SKIP := libLLVM* dri/ python3* firmware/ modules/ libgallium* gstreamer* systemd/ udev/ \
	samba/ cups/
sysroot:
	mkdir -p $(SYSROOT)/usr
	ln -sfn usr/lib $(SYSROOT)/lib
	rsync -a --info=stats1 $(foreach skip,$(SYSROOT_SKIP),--exclude='$(skip)') \
		$(BOARD):/usr/include $(BOARD):/usr/lib $(SYSROOT)/usr/

# Cross-compile deploy/ and install it to $(STAGE): what was built, with the layout of the board.
# Fail if a binary needs a newer glibc than the board has.
build-board:
	$(MAKE) -C deploy build BUILD_DIR=build-arm BUILD_TYPE=Release \
		CMAKE_ARGS=-DRK3588_SYSROOT=$(SYSROOT)
	rm -rf $(STAGE)
	cmake --install $(BUILD_ARM) --prefix $(STAGE) > /dev/null
	@for bin in $$(find $(STAGE)/bin -type f | sort); do \
		needed=$$(aarch64-linux-gnu-objdump -T $$bin | grep -o 'GLIBC_[0-9.]*' \
			| sed 's/GLIBC_//' | sort -V | tail -1); \
		highest=$$(printf '%s\n%s\n' "$$needed" "$(MAX_GLIBC)" | sort -V | tail -1); \
		name=$${bin#$(STAGE)/bin/}; \
		echo "$$name needs GLIBC_$$needed (board has $(MAX_GLIBC))"; \
		[ "$$highest" = "$(MAX_GLIBC)" ] \
			|| { echo "ERROR: $$name needs a newer glibc than the board"; exit 1; }; \
	done

# Fill ~/$(BOARD_DIR) on the board with the layout of the meta-repo (apart from the legacy ~/rk3588).
# sync-board-py: everything but the binaries (scripts, config and model, Python code, board wheel).
# sync-board: that, and the binaries of $(STAGE).
RSYNC := rsync -a --delete --exclude __pycache__ --exclude '*.egg-info' --exclude .gitkeep
sync-board-py:
	ssh $(BOARD) 'mkdir -p $(BOARD_DIR)/deploy $(BOARD_DIR)/common $(BOARD_DIR)/ai/ai \
		$(BOARD_DIR)/$(RKNN_DIR)/$(dir $(RKNN_BOARD_WHEEL))'
	$(RSYNC) deploy/sh/ $(BOARD):$(BOARD_DIR)/deploy/sh/
	$(RSYNC) deploy/python/ $(BOARD):$(BOARD_DIR)/deploy/python/
	$(RSYNC) deploy/tools/ $(BOARD):$(BOARD_DIR)/deploy/tools/
	$(RSYNC) deploy/resource/ $(BOARD):$(BOARD_DIR)/deploy/resource/
	rsync -a deploy/requirements-board.txt $(BOARD):$(BOARD_DIR)/deploy/
	$(RSYNC) common/python/ $(BOARD):$(BOARD_DIR)/common/python/
	$(RSYNC) common/tests/ $(BOARD):$(BOARD_DIR)/common/tests/
	rsync -a ai/ai/__init__.py $(BOARD):$(BOARD_DIR)/ai/ai/
	$(RSYNC) ai/ai/board/ $(BOARD):$(BOARD_DIR)/ai/ai/board/
	rsync -a $(RKNN_DIR)/$(RKNN_BOARD_WHEEL) $(BOARD):$(BOARD_DIR)/$(RKNN_DIR)/$(RKNN_BOARD_WHEEL)

sync-board: build-board sync-board-py
	ssh $(BOARD) 'mkdir -p $(BOARD_DIR)/deploy/bin'
	$(RSYNC) $(STAGE)/bin/ $(BOARD):$(BOARD_DIR)/deploy/bin/

# Create or update the board venv ~/$(BOARD_DIR)/.venv (no sudo, needs internet on the board).
# Run after sync-board.
setup-board:
	ssh $(BOARD) 'bash $(BOARD_DIR)/deploy/sh/env/setup_board.sh'

# On the board: lock_freq.sh matches deploy/sh/env/lock_freq.sh, the Python and C++ tests pass.
# Run sync-board first. BOARD_MODEL: the model of test_npu_infer, skipped when it is missing.
BOARD_MODEL ?= ~/$(BOARD_DIR)/deploy/resource/rknn/best-rk3588.rknn
check-board:
	@diff <(grep -v '^\s*#' deploy/sh/env/lock_freq.sh) \
		<(ssh $(BOARD) "grep -v '^\s*#' /usr/local/sbin/lock_freq.sh") \
		&& echo "lock_freq.sh: installed code equals deploy/sh/env/lock_freq.sh" \
		|| { echo "ERROR: /usr/local/sbin/lock_freq.sh differs, reinstall it with sudo"; exit 1; }
	ssh $(BOARD) 'cd $(BOARD_DIR)/common && \
		../.venv/bin/python -m pytest -q -p no:cacheprovider tests'
	ssh $(BOARD) 'bash $(BOARD_DIR)/deploy/sh/env/run_tests.sh $(BOARD_MODEL)'

# Build and serve Sphinx docs at http://localhost:8000 (bootstraps docs/.venv on first run).
docs: docs/.venv/bin/sphinx-build
	$(MAKE) -C docs check
	docs/.venv/bin/python -m http.server -d docs/_build/html 8000

docs/.venv/bin/sphinx-build: docs/requirements.txt
	uv venv docs/.venv
	uv pip install --python docs/.venv/bin/python -r docs/requirements.txt
	@touch $@
