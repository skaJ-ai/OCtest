#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

echo "[setup] creating venv at $VENV_DIR"
if ! $PYTHON_BIN -m venv "$VENV_DIR"; then
  echo "[setup] python -m venv failed. trying virtualenv bootstrap..."
  TMP_GET_PIP="$(mktemp)"
  curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$TMP_GET_PIP"
  $PYTHON_BIN "$TMP_GET_PIP" --user --break-system-packages
  rm -f "$TMP_GET_PIP"
  $PYTHON_BIN -m pip install --user --break-system-packages virtualenv
  $PYTHON_BIN -m virtualenv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install \
  fastapi \
  uvicorn \
  requests \
  httpx \
  pydantic \
  pydantic-settings

# Keep backend requirements in sync as baseline
if [[ -f backend/requirements.txt ]]; then
  python -m pip install -r backend/requirements.txt
fi

pip freeze | sort > requirements.txt

echo "[setup] done"
echo "[setup] activate with: source $VENV_DIR/bin/activate"
