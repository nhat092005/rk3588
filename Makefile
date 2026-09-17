.PHONY: help sync check train export-npu benchmark-npu leaderboard tail prepare-data clean

help:
	@echo "make sync                              - uv sync (install/update .venv)"
	@echo "make check                             - verify torch/cuda/numpy/rknn import OK in .venv"
	@echo "make train CONFIG=<path>               - train a baseline, e.g. CONFIG=ai/automation/configs/sfchd_yolov8n_baseline.yaml"
	@echo "make export-npu RUN=<run_id>           - export a finished run to RKNN (Tier 1 baseline), e.g. RUN=2026-09-17_sfchd_yolov8n_baseline_100ep"
	@echo "make benchmark-npu RUN=<run_id> DEVICE=<ip:port> [CORE_MASK=AUTO] - measure real latency/mAP-drop on a board"
	@echo "make leaderboard DATASET=<name>        - print a dataset's leaderboard, e.g. DATASET=sfchd"
	@echo "make tail RUN=<run_id>                 - tail -f a training run's results.csv"
	@echo "make prepare-data DATASET=<name>       - regenerate data/<name>/processed/ from raw/, e.g. DATASET=sfchd"
	@echo "make clean                             - remove __pycache__ directories"

sync:
	uv sync

check:
	.venv/bin/python -c "import torch, numpy; print('torch', torch.__version__, 'cuda:', torch.cuda.is_available()); print('numpy', numpy.__version__); from rknn.api import RKNN; print('rknn.api.RKNN OK')"

train:
	.venv/bin/python -m ai.automation.run $(CONFIG)

export-npu:
	.venv/bin/python -m ai.automation.export_npu $(RUN)

benchmark-npu:
	.venv/bin/python -m ai.automation.benchmark_npu $(RUN) $(DEVICE) --core-mask $(or $(CORE_MASK),AUTO)

leaderboard:
	cat ai/automation/leaderboards/$(DATASET).csv

tail:
	tail -f ai/automation/runs/$(RUN)/results.csv

prepare-data:
	.venv/bin/python scripts/data/prepare_$(DATASET).py

clean:
	find . -type d -name __pycache__ -not -path "./3rdparty/*" -exec rm -rf {} +
