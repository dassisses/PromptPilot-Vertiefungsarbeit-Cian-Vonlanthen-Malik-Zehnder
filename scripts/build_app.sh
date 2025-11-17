#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv}"
PYTHON_BIN="$VENV_DIR/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[build] Virtuelle Umgebung nicht gefunden – führe scripts/install.sh aus."
  exit 1
fi

ensure_file() {
  local target="$1"
  local contents="$2"
  if [[ ! -f "$target" ]]; then
    printf '%s\n' "$contents" > "$target"
  fi
}

ensure_file "$PROJECT_ROOT/presets.json" '[
  {
    "name": "Translation to Spanish",
    "prompt": "Uebersetze mir folgenden text auf spanisch: ",
    "api_type": "chatgpt"
  }
]'
ensure_file "$PROJECT_ROOT/credentials.json" '[]'
ensure_file "$PROJECT_ROOT/settings.json" '{
  "theme": "dark",
  "show_shortcut": ""
}'

"$PYTHON_BIN" -m pip install --upgrade pyinstaller >/dev/null

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name PromptPilot \
  --collect-submodules PySide6 \
  --hidden-import backend \
  "$PROJECT_ROOT/frontend.py"

echo "Build abgeschlossen. Das Bundle liegt im dist/-Ordner."
