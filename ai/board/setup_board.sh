#!/usr/bin/env bash
# Create the tier-2 venv on the board (no sudo). Run on the board from the repo root:
#   bash ai/board/setup_board.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m venv .venv-board
.venv-board/bin/pip install --upgrade pip
.venv-board/bin/pip install -r ai/board/requirements.txt
.venv-board/bin/python -c "import numpy, cv2, onnxruntime, psutil, yaml; from rknnlite.api import RKNNLite; print('numpy', numpy.__version__, 'cv2', cv2.__version__, 'onnxruntime', onnxruntime.__version__, 'RKNNLite OK')"
