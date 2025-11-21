#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv}"
PYTHON_BIN="$VENV_DIR/bin/python"
SPEC_FILE="$PROJECT_ROOT/promptpilot.spec"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"

log() { printf "[build] %s\n" "$*"; }

ensure_file() {
  local target="$1"
  local contents="$2"
  if [[ ! -f "$target" ]]; then
    printf '%s\n' "$contents" >"$target"
  fi
}

if [[ ! -x "$PYTHON_BIN" ]]; then
  log "Erzeuge virtuelle Umgebung im $VENV_DIR …"
  python3 -m venv "$VENV_DIR"
fi

log "Aktualisiere pip und installiere Abhängigkeiten …"
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null
"$PYTHON_BIN" -m pip install -r "$PROJECT_ROOT/requirements.txt" >/dev/null
"$PYTHON_BIN" -m pip install --upgrade pyinstaller >/dev/null

log "Stelle Default-Ressourcen bereit …"
ensure_file "$PROJECT_ROOT/presets.json" '[
  {
    "name": "Translation to Spanish",
    "prompt": "Uebersetze mir folgenden text auf spanisch: ",
    "api_type": "chatgpt",
    "provider": "OpenAI",
    "model": "gpt-3.5-turbo"
  }
]'
ensure_file "$PROJECT_ROOT/credentials.json" '[]'
ensure_file "$PROJECT_ROOT/settings.json" '{
  "theme": "dark",
  "show_shortcut": ""
}'

log "Räume alte Build-Artefakte auf …"
rm -rf "$DIST_DIR" "$BUILD_DIR"

log "Starte PyInstaller Build …"
"$PYTHON_BIN" -m PyInstaller "$SPEC_FILE" --clean --noconfirm

if [[ ! -d "$DIST_DIR" ]]; then
  echo "[build] ❌ Build fehlgeschlagen – dist/ wurde nicht erzeugt." >&2
  exit 1
fi

log "Build abgeschlossen. Die Anwendung liegt im dist/-Ordner bereit."
