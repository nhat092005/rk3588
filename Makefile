# Entry point of the meta-repo. Run `make init` once after a plain `git clone`.
.PHONY: init

RKNN_URL     := https://github.com/airockchip/rknn-toolkit2
RKNN_DIR     := 3rdparty/rknn-toolkit2
RKNN_TAG     := v2.3.2
RKNN_API_DIR := rknpu2/runtime/Linux/librknn_api/include

# rknn-toolkit2 is about 2 GB. `git submodule update` would check out all of it before any sparse rule applies,
# so the first clone is done here (blobless + sparse, about 600 KB). The commit must equal the pin of the submodule.
init:
	git submodule update --init common ai deploy docs
	@[ -e $(RKNN_DIR)/.git ] || git clone -q --filter=blob:none --sparse --depth 1 --branch $(RKNN_TAG) $(RKNN_URL) $(RKNN_DIR)
	git -C $(RKNN_DIR) sparse-checkout set $(RKNN_API_DIR)
	@git submodule status $(RKNN_DIR)
