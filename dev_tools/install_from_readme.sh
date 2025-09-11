#!/usr/bin/env bash
set -euo pipefail

# Recreate the environment as documented in README.md
# - Python 3.8.10
# - PyTorch 2.4.1 + torchvision 0.19.1 (CPU acceptable for CI)
# - requirements.txt

ENV_NAME=${1:-hpe}

if ! command -v conda >/dev/null 2>&1; then
  echo "[error] Conda is required for this installer (README uses conda)." >&2
  exit 1
fi

echo "[info] Creating env '${ENV_NAME}' with Python 3.8.10"
conda env remove -n "${ENV_NAME}" -y >/dev/null 2>&1 || true
conda create -n "${ENV_NAME}" python=3.8.10 -y

echo "[info] Activating env"
eval "$(conda shell.bash hook)"
conda activate "${ENV_NAME}"

echo "[info] Installing PyTorch and torchvision"
conda install pytorch==2.4.1 torchvision==0.19.1 -c pytorch -y

echo "[info] Installing requirements.txt"
conda install --file requirements.txt -y || pip install -r requirements.txt

if [ -x models/AlphaPose/build_extensions.sh ]; then
  echo "[info] Building AlphaPose extensions"
  bash models/AlphaPose/build_extensions.sh || python setup.py build_ext --inplace || true
else
  echo "[warn] AlphaPose build script not found; skipping build"
fi

echo "[ok] Environment '${ENV_NAME}' is ready"

