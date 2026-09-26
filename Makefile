# Board & hardware
BOARD        ?= minhnhat@100.67.251.37
BOARD_REPO   ?= rk3588
BOARD_IMAGES ?= data/sfchd_5class/processed/images/test
DEVICE       ?= 100.67.251.37:5555
CORE_MASK    ?= AUTO

# Paths & logtee
comma   := ,
RUN_DIR  = ai/automation/runs/$(RUN)
LOGTEE   = .venv/bin/python scripts/logtee.py
# Ultralytics must not pip-install into .venv (it silently changed onnx/onnxslim before); only make sync changes it
export YOLO_AUTOINSTALL = False

# Board exec & PC git provenance
BOARD_PY   = cd $(BOARD_REPO) && .venv-board/bin/python -m
GIT_COMMIT = $(shell git rev-parse HEAD)
GIT_DIRTY  = $(if $(shell git status --porcelain ai/ scripts/),true,false)
BOARD_PROV = --run-id $(RUN) --git-commit $(GIT_COMMIT) --git-dirty $(GIT_DIRTY)

# Demo
DEMO_BACKEND    = $(or $(BACKEND),pt)
DEMO_TAG        = $(if $(filter rknn,$(DEMO_BACKEND)),rknn_$(PREC),$(DEMO_BACKEND)_fp32)
DEMO_BOARD_ARGS = $(if $(filter rknn,$(DEMO_BACKEND)),--board $(BOARD) --board-repo $(BOARD_REPO))

# Environment and setup
.PHONY: help sync check
help:
	@echo "Usage: make <target> [OPTIONS]"
	@echo ""
	@echo "Phases (Guide section 8; skip finished steps, end with make tables):"
	@echo "  make phase2 DATASET=<ds>               - train baselines (seed 42) + crosscheck"
	@echo "  make phase3 DATASET=<ds>               - export FP16/INT8, complexity, evaluate ONNX/RKNN"
	@echo "  make phase4 DATASET=<ds>               - tier 1, tier 2, CPU, throughput, GPU reference (needs LOCK)"
	@echo "  make phase10 DATASET=<ds> [MODELS=a,b] - seeds 43, 44 for key models (default yolov8n_baseline)"
	@echo ""
	@echo "Environment & Setup:"
	@echo "  make sync                              - uv sync (install/update .venv)"
	@echo "  make check                             - verify torch/cuda/numpy/rknn import OK in .venv"
	@echo ""
	@echo "Training & Evaluation:"
	@echo "  make train CONFIG=<path> [SEED=<n>]    - train + protocol v1 eval + leaderboard, e.g. CONFIG=ai/automation/configs/sfchd_5class_yolov8n_baseline.yaml SEED=43"
	@echo "  make evaluate RUN=<id> BACKEND=pt|onnx|rknn [PREC=fp16|int8]"
	@echo "                                         - protocol v1 AI Quality (rknn runs on the board via DEVICE)"
	@echo "  make golden-test                       - evaluator must reproduce ai/automation/golden/evaluator_v1.json"
	@echo "  make golden-update                     - rewrite the golden file (only when the protocol version changes)"
	@echo "  make test-parsers                      - eval_perf parsers vs real RKNN 2.3.2 output (tests/fixtures/)"
	@echo "  make crosscheck [WEIGHTS=<pt>]         - evaluator vs Ultralytics model.val() on the same weights"
	@echo ""
	@echo "Model Export & Tier 1 Benchmark:"
	@echo "  make export-npu RUN=<id> PREC=fp16|int8 - export to RKNN + FP32 ONNX, build log -> runs/<id>/logs/export_<prec>_*.log"
	@echo "  make complexity RUN=<id>                - Params/GFLOPs/MACs/file sizes -> runs/<id>/complexity.json"
	@echo "  make bench-gpu RUN=<id>                 - PC GPU reference latency (Table H) -> runs/<id>/bench/gpu_pt_fp32.json"
	@echo "  make tables DATASET=<name>              - build all tables from result files -> results/<name>/ (exit 1 on inconsistency)"
	@echo "  make benchmark-npu RUN=<id> PREC=<p> [CORE_MASK=AUTO]"
	@echo "                                          - tier 1: eval_perf/eval_memory from the PC"
	@echo ""
	@echo "Board Operations & Tier 2 Benchmark:"
	@echo "  make board-sync                        - copy ai/board code and the test images to the board"
	@echo "  make board-setup                       - create .venv-board on the board (no sudo)"
	@echo "  make bench-board RUN=<id> PREC=<p> [CORE_MASK=AUTO]"
	@echo "                                          - tier 2 on the board: pre/NPU/post/E2E, RAM, CPU, temp"
	@echo "  make bench-board-cpu RUN=<id> [THREADS=4]"
	@echo "                                          - tier 2 on the board CPU with ONNX Runtime (FP32)"
	@echo "  make bench-board-throughput RUN=<id> PREC=<p> CORE_MASKS=CORE_0,CORE_1,CORE_2"
	@echo "                                          - multi-context throughput"
	@echo ""
	@echo "Demo (videos and images, outputs under data/demo/outputs/):"
	@echo "  make demo-video RUN=<id> SRC=<video> [BACKEND=pt|onnx|rknn] [PREC=fp16|int8]"
	@echo "                                          - detect once -> predict.mp4 -> track.mp4 -> compare"
	@echo "  make demo-images RUN=<id> [SRC=data/demo/images] [BACKEND=pt|onnx|rknn] [PREC=fp16|int8]"
	@echo "                                          - detect once -> predict/<name>.jpg per image"
	@echo "  make demo-compare A=<path> B=<path> [OUT=<path>]"
	@echo "                                          - side by side; video/compare.py if A ends .mp4, else image/compare.py"
	@echo "                                          - BACKEND=rknn needs make board-sync first (copies ai/board/detect_video.py, detect_images.py)"
	@echo ""
	@echo "Data & Utilities:"
	@echo "  make leaderboard DATASET=<name>        - print a dataset's leaderboard, e.g. DATASET=sfchd_5class"
	@echo "  make tail RUN=<run_id>                 - tail -f a training run's results.csv"
	@echo "  make prepare-data DATASET=<name>       - regenerate data/<name>/processed/ from raw/, e.g. DATASET=sfchd"
	@echo "  make archive [DATASET=<name>] [OUT=<path>]"
	@echo "                                          - archive untracked weights and datasets to zip"
	@echo "  make restore [ARCHIVE=<path>]"    
	@echo "                                          - restore weights and datasets from zip"
	@echo "  make clean                              - remove __pycache__ directories"
	@echo ""

sync:
	uv sync

check:
	.venv/bin/python -c "import torch, numpy; print('torch', torch.__version__, 'cuda:', torch.cuda.is_available()); print('numpy', numpy.__version__); from rknn.api import RKNN; print('rknn.api.RKNN OK')"

# Training and evaluation
.PHONY: train evaluate golden-test golden-update crosscheck test-parsers
train:
	$(eval RID := $(shell .venv/bin/python -m ai.automation.run $(CONFIG) $(if $(SEED),--seed $(SEED)) --print-run-id 2>/dev/null | tail -n 1))
	@test -n "$(RID)" || .venv/bin/python -m ai.automation.run $(CONFIG) $(if $(SEED),--seed $(SEED)) --print-run-id
	$(LOGTEE) ai/automation/runs/$(RID)/logs/train -- .venv/bin/python -m ai.automation.run $(CONFIG) $(if $(SEED),--seed $(SEED))

evaluate:
	$(LOGTEE) $(RUN_DIR)/logs/evaluate_$(BACKEND)$(if $(PREC),_$(PREC)) -- .venv/bin/python -m ai.automation.evaluate $(RUN) --backend $(BACKEND) $(if $(PREC),--precision $(PREC) --board $(BOARD) --board-repo $(BOARD_REPO))

golden-test:
	$(LOGTEE) ai/automation/golden/logs/golden_test -- .venv/bin/python -m ai.automation.check_evaluator golden

test-parsers:
	.venv/bin/python -m tests.test_parsers

golden-update:
	$(LOGTEE) ai/automation/golden/logs/golden_update -- .venv/bin/python -m ai.automation.check_evaluator golden --update

crosscheck:
	$(LOGTEE) $(if $(RUN),$(RUN_DIR)/logs/crosscheck,ai/automation/golden/logs/crosscheck) -- .venv/bin/python -m ai.automation.check_evaluator crosscheck $(if $(WEIGHTS),--weights $(WEIGHTS)) $(if $(RUN),--run-id $(RUN))

# Model export and tier 1 benchmark
.PHONY: export-npu complexity tables benchmark-npu bench-gpu
export-npu:
	RKNN_LOG_LEVEL=3 $(LOGTEE) $(RUN_DIR)/logs/export_$(PREC) -- .venv/bin/python -m ai.automation.export_npu $(RUN) --quantize $(if $(filter fp16,$(PREC)),16,8)

complexity:
	$(LOGTEE) $(RUN_DIR)/logs/complexity -- .venv/bin/python -m ai.automation.complexity $(RUN)

tables:
	.venv/bin/python -m ai.automation.tables $(DATASET)

bench-gpu:
	$(LOGTEE) $(RUN_DIR)/logs/bench_gpu -- .venv/bin/python -m ai.automation.bench_gpu $(RUN)

benchmark-npu:
	$(LOGTEE) $(RUN_DIR)/logs/tier1_$(PREC)_$(CORE_MASK) -- .venv/bin/python -m ai.automation.benchmark_npu $(RUN) $(DEVICE) --precision $(PREC) --core-mask $(CORE_MASK)

# Board operations and tier 2 benchmark
.PHONY: board-sync board-setup board-check bench-board bench-board-cpu bench-board-throughput phase2 phase3 phase4 phase10
board-sync:
	ssh $(BOARD) 'mkdir -p $(BOARD_REPO)/ai/board $(BOARD_REPO)/$(BOARD_IMAGES)'
	rsync -a --delete --exclude __pycache__ ai/board/ $(BOARD):$(BOARD_REPO)/ai/board/
	rsync -a ai/__init__.py $(BOARD):$(BOARD_REPO)/ai/
	rsync -aL --delete $(BOARD_IMAGES)/ $(BOARD):$(BOARD_REPO)/$(BOARD_IMAGES)/

board-check:
	.venv/bin/python -m ai.automation.board_check $(BOARD) $(DEVICE) $(if $(LOCK),--require-lock)

# Whole phases of Guide section 8 (skip finished steps, stop at the first error, end with make tables)
phase2 phase3 phase4 phase10:
	.venv/bin/python -m ai.automation.pipeline $@ --dataset $(DATASET) $(if $(MODELS),--models $(MODELS))

board-setup:
	ssh $(BOARD) 'cd $(BOARD_REPO) && bash ai/board/setup_board.sh'

bench-board:
	ssh $(BOARD) 'mkdir -p $(BOARD_REPO)/$(RUN_DIR)/weights $(BOARD_REPO)/$(RUN_DIR)/bench'
	rsync -a --relative $(RUN_DIR)/weights/./rknn_$(PREC)/*.rknn $(RUN_DIR)/weights/./rknn_$(PREC)/metadata.yaml $(BOARD):$(BOARD_REPO)/$(RUN_DIR)/weights/
	$(LOGTEE) $(RUN_DIR)/logs/tier2_$(PREC)_$(CORE_MASK) -- ssh $(BOARD) '$(BOARD_PY) ai.board.bench_npu --model $(RUN_DIR)/weights/rknn_$(PREC) --images $(BOARD_IMAGES) --core-mask $(CORE_MASK) --out $(RUN_DIR)/bench/tier2_$(PREC)_$(CORE_MASK).json $(BOARD_PROV)'
	mkdir -p $(RUN_DIR)/bench && scp $(BOARD):$(BOARD_REPO)/$(RUN_DIR)/bench/tier2_$(PREC)_$(CORE_MASK).json $(RUN_DIR)/bench/

bench-board-cpu:
	ssh $(BOARD) 'mkdir -p $(BOARD_REPO)/$(RUN_DIR)/weights $(BOARD_REPO)/$(RUN_DIR)/bench' && scp $(RUN_DIR)/weights/best.onnx $(BOARD):$(BOARD_REPO)/$(RUN_DIR)/weights/
	$(LOGTEE) $(RUN_DIR)/logs/tier2_cpu_onnx_t$(or $(THREADS),4) -- ssh $(BOARD) '$(BOARD_PY) ai.board.bench_cpu_onnx --model $(RUN_DIR)/weights/best.onnx --images $(BOARD_IMAGES) --threads $(or $(THREADS),4) --out $(RUN_DIR)/bench/tier2_cpu_onnx_t$(or $(THREADS),4).json $(BOARD_PROV)'
	mkdir -p $(RUN_DIR)/bench && scp $(BOARD):$(BOARD_REPO)/$(RUN_DIR)/bench/tier2_cpu_onnx_t$(or $(THREADS),4).json $(RUN_DIR)/bench/

bench-board-throughput:
	ssh $(BOARD) 'mkdir -p $(BOARD_REPO)/$(RUN_DIR)/weights $(BOARD_REPO)/$(RUN_DIR)/bench'
	rsync -a --relative $(RUN_DIR)/weights/./rknn_$(PREC)/*.rknn $(RUN_DIR)/weights/./rknn_$(PREC)/metadata.yaml $(BOARD):$(BOARD_REPO)/$(RUN_DIR)/weights/
	$(LOGTEE) $(RUN_DIR)/logs/throughput_$(PREC)_$(subst $(comma),-,$(CORE_MASKS)) -- ssh $(BOARD) '$(BOARD_PY) ai.board.bench_throughput --model $(RUN_DIR)/weights/rknn_$(PREC) --images $(BOARD_IMAGES) --core-masks $(CORE_MASKS) --out $(RUN_DIR)/bench/throughput_$(PREC)_$(subst $(comma),-,$(CORE_MASKS)).json $(BOARD_PROV)'
	mkdir -p $(RUN_DIR)/bench && scp $(BOARD):$(BOARD_REPO)/$(RUN_DIR)/bench/throughput_$(PREC)_$(subst $(comma),-,$(CORE_MASKS)).json $(RUN_DIR)/bench/

# Demo video/image toolkit
.PHONY: demo-video demo-images demo-compare
demo-video:
	$(eval VIDEO_OUT := data/demo/outputs/videos/$(basename $(notdir $(SRC)))/$(RUN)/$(DEMO_TAG))
	$(LOGTEE) $(RUN_DIR)/logs/demo_detect_$(basename $(notdir $(SRC)))_$(DEMO_TAG) -- .venv/bin/python scripts/demo/video/detect.py --run $(RUN) --source $(SRC) --backend $(DEMO_BACKEND) $(if $(PREC),--precision $(PREC)) $(DEMO_BOARD_ARGS)
	$(LOGTEE) $(RUN_DIR)/logs/demo_predict_$(basename $(notdir $(SRC)))_$(DEMO_TAG) -- .venv/bin/python scripts/demo/video/predict.py --detections $(VIDEO_OUT)/detections.npz
	$(LOGTEE) $(RUN_DIR)/logs/demo_track_$(basename $(notdir $(SRC)))_$(DEMO_TAG) -- .venv/bin/python scripts/demo/video/track.py --detections $(VIDEO_OUT)/detections.npz
	$(LOGTEE) $(RUN_DIR)/logs/demo_compare_$(basename $(notdir $(SRC)))_$(DEMO_TAG) -- .venv/bin/python scripts/demo/video/compare.py $(VIDEO_OUT)/predict.mp4 $(VIDEO_OUT)/track.mp4

demo-images:
	$(eval IMAGES_OUT := data/demo/outputs/images/$(RUN)/$(DEMO_TAG))
	$(LOGTEE) $(RUN_DIR)/logs/demo_detect_images_$(DEMO_TAG) -- .venv/bin/python scripts/demo/image/detect.py --run $(RUN) $(if $(SRC),--source $(SRC)) --backend $(DEMO_BACKEND) $(if $(PREC),--precision $(PREC)) $(DEMO_BOARD_ARGS)
	$(LOGTEE) $(RUN_DIR)/logs/demo_predict_images_$(DEMO_TAG) -- .venv/bin/python scripts/demo/image/predict.py --detections $(IMAGES_OUT)/detections.npz

demo-compare:
	$(eval DEMO_KIND := $(if $(filter %.mp4,$(A)),video,image))
	$(eval DEMO_OUTFLAG := $(if $(filter video,$(DEMO_KIND)),--out,--out-dir))
	$(LOGTEE) data/demo/outputs/logs/demo_compare -- .venv/bin/python scripts/demo/$(DEMO_KIND)/compare.py $(A) $(B) $(if $(OUT),$(DEMO_OUTFLAG) $(OUT))

# Data and utilities
.PHONY: leaderboard tail prepare-data archive restore clean
leaderboard:
	cat ai/automation/leaderboards/$(DATASET).csv

tail:
	tail -f ai/automation/runs/$(RUN)/results.csv

prepare-data:
	.venv/bin/python scripts/data/prepare_$(DATASET).py

archive:
	DATASET=$(DATASET) bash scripts/archive/archive.sh $(OUT)

restore:
	bash scripts/archive/restore.sh $(ARCHIVE)

clean:
	find . -type d -name __pycache__ -not -path "./3rdparty/*" -exec rm -rf {} +
