# Entry point of the meta-repo. Run `make init` once after a plain `git clone`.
.PHONY: init

RKNN_API_DIR := rknpu2/runtime/Linux/librknn_api/include

# rknn-toolkit2 is about 2 GB: fetch only the commit tree without file contents, then check out the runtime headers.
init:
	git submodule update --init common ai deploy docs
	git submodule update --init --filter=blob:none 3rdparty/rknn-toolkit2
	git -C 3rdparty/rknn-toolkit2 sparse-checkout set $(RKNN_API_DIR)
