#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv}"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
  "$VENV_DIR/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"
else
  echo "Keine requirements.txt gefunden – installiere Standard-Abhängigkeiten"
  "$VENV_DIR/bin/pip" install PySide6 pyperclip openai pynput
fi

echo "Virtuelle Umgebung installiert. Aktiviere sie mit 'source $VENV_DIR/bin/activate'."
