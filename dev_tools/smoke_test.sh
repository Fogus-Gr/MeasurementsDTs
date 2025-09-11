#!/usr/bin/env bash
set -euo pipefail

# Smoke tests aligned with README environment.
# Usage: bash dev_tools/smoke_test.sh [device] [conda_env]

DEVICE=${1:-CPU}
ENV_NAME=${2:-hpe}

if command -v conda >/dev/null 2>&1; then
  echo "[info] Activating conda env '${ENV_NAME}'"
  eval "$(conda shell.bash hook)"
  conda activate "${ENV_NAME}" || {
    echo "[error] Conda env '${ENV_NAME}' not found. Run dev_tools/install_from_readme.sh" >&2
    exit 1
  }
else
  echo "[warn] Conda not found; proceeding with system Python. Ensure README deps are installed."
fi

echo "[info] Using device=${DEVICE}"

run() {
  echo "[run] $*"
  eval "$@"
}

# MoveNet on single image
run "python3 main.py --method movenet --device ${DEVICE} --input unit_tests/images/testImage.jpg --save_image"

# AlphaPose on images directory (expects models present)
if [ -d models/AlphaPose/pretrained_models ]; then
  run "python3 main.py --method alphapose --device ${DEVICE} --input unit_tests/images/ --json"
else
  echo "[skip] AlphaPose models not found; skipping AlphaPose smoke test"
fi

# EfficientHRNet1 on tiny gif/video
run "python3 main.py --method ae1 --device ${DEVICE} --input unit_tests/video/giphy.gif --save_video"

echo "[ok] Smoke tests completed"
