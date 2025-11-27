#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv}"
PYTHON_BIN="$VENV_DIR/bin/python"
SPEC_FILE="$PROJECT_ROOT/promptpilot.spec"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
ICON_PNG="$PROJECT_ROOT/promtpilot_icon.png"
ICON_ICNS="$PROJECT_ROOT/icon.icns"

log() { printf "[build] %s\n" "$*"; }

ensure_file() {
  local target="$1"
  local contents="$2"
  if [[ ! -f "$target" ]]; then
    printf '%s\n' "$contents" >"$target"
  fi
}

ensure_icon() {
  if [[ -f "$ICON_ICNS" ]]; then
    log "Verwende vorhandenes Icon: $ICON_ICNS"
    return 0
  fi

  if [[ ! -f "$ICON_PNG" ]]; then
    log "⚠️  Kein Icon gefunden ($ICON_PNG) – Bundle nutzt Standard-Icon."
    return 0
  fi

  if [[ "$OSTYPE" != darwin* ]]; then
    log "Hinweis: Icon-Konvertierung zu .icns wird nur unter macOS ausgeführt (OSTYPE=$OSTYPE)."
    return 0
  fi

  if ! command -v sips >/dev/null || ! command -v iconutil >/dev/null; then
    log "⚠️  sips/iconutil nicht verfügbar – kann icon.icns nicht erzeugen."
    return 0
  fi

  log "Erzeuge icon.icns aus $ICON_PNG …"
  tmp_iconset="$(mktemp -d)"
  for size in 16 32 64 128 256 512; do
    sips -z "$size" "$size" "$ICON_PNG" --out "$tmp_iconset/icon_${size}x${size}.png" >/dev/null
    sips -z $((size * 2)) $((size * 2)) "$ICON_PNG" --out "$tmp_iconset/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns -o "$ICON_ICNS" "$tmp_iconset" >/dev/null
  rm -rf "$tmp_iconset"
  log "icon.icns erzeugt: $ICON_ICNS"
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
ensure_icon

log "Räume alte Build-Artefakte auf …"
rm -rf "$DIST_DIR" "$BUILD_DIR"

log "Wechsle ins Projektverzeichnis …"
cd "$PROJECT_ROOT"

log "Starte PyInstaller Build …"
"$PYTHON_BIN" -m PyInstaller "$SPEC_FILE" --clean --noconfirm

if [[ ! -d "$DIST_DIR" ]]; then
  echo "[build] ❌ Build fehlgeschlagen – dist/ wurde nicht erzeugt." >&2
  exit 1
fi

log "Build abgeschlossen. Die Anwendung liegt im dist/-Ordner bereit."
