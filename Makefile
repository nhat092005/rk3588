# Entry point of the meta-repo. Run `make init` once after a plain `git clone`.
.PHONY: init sysroot build-board sync-board

# Board access and locations. Override on the CLI, for example: make sysroot BOARD=user@host
BOARD       ?= minhnhat@192.168.137.49
BOARD_DIR   ?= rk3588-deploy
SYSROOT     ?= $(HOME)/sysroots/orangepi5
BUILD_ARM   := deploy/build-arm
MAX_GLIBC   ?= 2.35

RKNN_URL     := https://github.com/airockchip/rknn-toolkit2
RKNN_DIR     := 3rdparty/rknn-toolkit2
RKNN_TAG     := v2.3.2
RKNN_API_DIR := rknpu2/runtime/Linux/librknn_api/include

BOARD_BINARIES := app/rk3588_deploy probes/probe_link probes/probe_infer test/test_logger

# rknn-toolkit2 is about 2 GB. `git submodule update` would check out all of it before any sparse rule applies,
# so the first clone is done here (blobless + sparse, about 600 KB). The commit must equal the pin of the submodule.
init:
	git submodule update --init common ai deploy docs
	@[ -e $(RKNN_DIR)/.git ] || git clone -q --filter=blob:none --sparse --depth 1 --branch $(RKNN_TAG) $(RKNN_URL) $(RKNN_DIR)
	git -C $(RKNN_DIR) sparse-checkout set $(RKNN_API_DIR)
	@git submodule status $(RKNN_DIR)

# Copy the board's headers and libs to the PC (about 2 GB, incremental). Redo after a board OS or librknnrt change.
sysroot:
	mkdir -p $(SYSROOT)/usr
	ln -sfn usr/lib $(SYSROOT)/lib
	rsync -a --info=stats1 --exclude='libLLVM*' --exclude='dri/' --exclude='python3*' --exclude='firmware/' --exclude='modules/' \
		--exclude='libgallium*' --exclude='gstreamer*' --exclude='systemd/' --exclude='udev/' --exclude='samba/' --exclude='cups/' \
		$(BOARD):/usr/include $(BOARD):/usr/lib $(SYSROOT)/usr/

# Cross-compile deploy/ for the board, then fail if any binary needs a glibc newer than the board has.
build-board:
	cmake -S deploy -B $(BUILD_ARM) -DCMAKE_TOOLCHAIN_FILE=$(CURDIR)/deploy/cmake/aarch64-toolchain.cmake \
		-DCMAKE_BUILD_TYPE=Release -DBUILD_PROBES=ON -DRK3588_SYSROOT=$(SYSROOT)
	cmake --build $(BUILD_ARM)
	@for bin in $(BOARD_BINARIES); do \
		needed=$$(aarch64-linux-gnu-objdump -T $(BUILD_ARM)/$$bin | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -V | tail -1); \
		highest=$$(printf '%s\n%s\n' "$$needed" "$(MAX_GLIBC)" | sort -V | tail -1); \
		echo "$$bin needs GLIBC_$$needed (board has $(MAX_GLIBC))"; \
		[ "$$highest" = "$(MAX_GLIBC)" ] || { echo "ERROR: $$bin needs a newer glibc than the board"; exit 1; }; \
	done

# Copy binaries and shared Python to ~/$(BOARD_DIR) on the board. Separate from the legacy ~/rk3588.
sync-board: build-board
	ssh $(BOARD) 'mkdir -p $(BOARD_DIR)/bin $(BOARD_DIR)/common'
	rsync -a $(addprefix $(BUILD_ARM)/,$(BOARD_BINARIES)) $(BOARD):$(BOARD_DIR)/bin/
	rsync -a --delete common/python/ $(BOARD):$(BOARD_DIR)/common/python/
