#!/usr/bin/env bash
# Setup the centralized Python virtual environment and install requirements
# Usage: ./scripts/setup_env.sh [--no-verify]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
REQ_FILE="$ROOT_DIR/requirements.txt"
VERIFY_SCRIPT="$ROOT_DIR/scripts/verify_env.py"

NO_VERIFY=false
if [[ "${1:-}" == "--no-verify" ]]; then
  NO_VERIFY=true
fi

echo "[setup_env] root: $ROOT_DIR"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "ERROR: requirements.txt not found at $REQ_FILE"
  exit 2
fi


if [[ ! -d "$VENV_DIR" ]]; then
  echo "[setup_env] Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "[setup_env] Activating venv..."
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "[setup_env] Upgrading pip and installing wheel/build deps"
pip install --upgrade pip setuptools wheel

echo "[setup_env] Installing packages from requirements.txt (this may take a while)"
pip install -r "$REQ_FILE"

if [[ "$NO_VERIFY" = false ]]; then
  if [[ -f "$VERIFY_SCRIPT" ]]; then
    echo "[setup_env] Running verify script to check imports"
    python3 "$VERIFY_SCRIPT" || {
      echo "[setup_env] verify script failed -- some imports missing or failed. See output above." >&2
      exit 3
    }
  else
    echo "[setup_env] verify script not found at $VERIFY_SCRIPT; skipping verification"
  fi
fi

echo "[setup_env] Success. To activate the venv in your shell run:"
echo "  source $VENV_DIR/bin/activate"

echo "[setup_env] If you want to skip verification next time: ./scripts/setup_env.sh --no-verify"

exit 0
