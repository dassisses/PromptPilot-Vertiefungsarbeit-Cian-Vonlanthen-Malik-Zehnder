#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv}"
PYTHON_BIN="$VENV_DIR/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
  if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
    "$VENV_DIR/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"
  fi
fi

source "$VENV_DIR/bin/activate"
cd "$PROJECT_ROOT"
exec "$PYTHON_BIN" "$PROJECT_ROOT/main.py"
