#!/bin/bash
set -euo pipefail

log() {
  printf '[build_app] %s\n' "$1"
}

EXPECTED_PROJECT_ROOT="/Users/taavoci1/PycharmProjects/Promtpilot/PromptPilot-Vertiefungsarbeit-Cian-Vonlanthen-Malik-Zehnder"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ "$PROJECT_ROOT" != "$EXPECTED_PROJECT_ROOT" ]]; then
  log "Warnung: Projektpfad ist $PROJECT_ROOT (erwartet $EXPECTED_PROJECT_ROOT). Es wird der aktuelle Pfad verwendet."
fi

VENV_DIR="$PROJECT_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  log "Fehler: Virtuelle Umgebung wurde nicht gefunden: $VENV_PYTHON"
  exit 1
fi

ensure_file() {
  local target="$1"
  local contents="$2"
  if [[ ! -f "$target" ]]; then
    log "Erstelle fehlende Datei $(basename "$target")"
    printf '%s\n' "$contents" > "$target"
  fi
}

log "Synchronisiere Standarddaten-Dateien"
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

START_SCRIPT="$PROJECT_ROOT/start.sh"
cat > "$START_SCRIPT" <<STARTSCRIPT
#!/bin/bash
set -euo pipefail
PROJECT_ROOT="$PROJECT_ROOT"
VENV_DIR="$PROJECT_ROOT/.venv"
source "$VENV_DIR/bin/activate"
cd "$PROJECT_ROOT"
exec "$VENV_DIR/bin/python" "$PROJECT_ROOT/frontend.py"
STARTSCRIPT
chmod +x "$START_SCRIPT"
log "start.sh aktualisiert"

log "Installiere/aktualisiere Build-Abhängigkeiten"
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null
"$VENV_PYTHON" -m pip install --upgrade pyinstaller PySide6 pyperclip openai pynput >/dev/null

ICON_PATH="$PROJECT_ROOT/icon.icns"
if [[ ! -f "$ICON_PATH" ]]; then
  log "Erzeuge Standard-App-Icon"
  TMP_DIR="$(mktemp -d)"
  BASE_PNG="$TMP_DIR/base.png"
  base64 --decode <<'ICONDATA' > "$BASE_PNG"
iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAACGUlEQVR4nO3WQQ3DMBQFQaT9D+wZiIbQnFFdoSK4lEw2g8zuPXJzQ27YmxLd7t7uvX0AABE7I99JfhdFwAAAIxDn1vsm3mevlNOM7cAQPH/f18+fPgwdepU/Pz88PDhQ3x8fPz9/bF3715cuXJl/Pr1i4sXL8bDhw9j2LBhbNmyJZ04cQLg8ePHMT4+jo0bN8b33nsPFi5ciDk5OYm/vz9Zs2YNQKNGjWLaNGls2bIlrrrqqvh77bXXfPnyBTz99NOYN28e8vPzk5CQkDVr1uDIkSOYPXs2QkNDE/Xv37948cIFPP/886hWrRqqVq2KcnNzcfbsWQwZMoTdu3dj0qRJ2L9/P9Vq1ciccMIJ2Lx5M9Rq1YpZs2aJRx99NHr27IlQK1aswJIlS+LAgQPYvXs3ad++PR4+fCguXboUCoUCeve5BwC8lRO4QV1QV1QV1QV1QV1QV9fkyZPo3bs38vPzk59++ilVqlShXbt2YfTo0Rg8eDBmz56NAQMG4MiRI1G5ciXS09Mxffp0cXFxQavVKj788EPE43E8f/58Jk+ejLS0NKxbtw5Tp04lPXv2RN26dXHgwAEpV64cvXv3RmZmJvbs2YPBgwfj8uXLMWvWLAwdOhSzZs1Cq1at2L17N4YMGYI4ODiI5uZmLFmyBFu2bMGUKVNIQkICu3btgr1796JixYrw448/4ocffsgnTpxgxowZGDRoEF27do0qVaqgtLQUffr0QY8ePcjJySHNmjVh4MCBKBQK2Lp1K4YOHYpff/0V7dq1Y926dRg6dCiioqJISEgAUN999x3jx4/HqlWr0LJlS1FQUACoSpUqVKlSJdLS0qBfv37Ys2cPvXv3xuzZs3HgwIFISkryzTff4L///gvu3r2LRo0aUVZWBgAuXryItm3bIr/++isqVaoElUpFr169sGfPHsTFxeG5555D9+7dMX/+/BQWFp6nzA4Ay7gDDC4HOQAAAAAASUVORK5CYII=
ICONDATA
  ICONSET="$TMP_DIR/PromptPilot.iconset"
  mkdir -p "$ICONSET"
  if command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
    for size in 16 32 64 128 256 512; do
      sips -z "$size" "$size" "$BASE_PNG" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
      double=$((size * 2))
      sips -z "$double" "$double" "$BASE_PNG" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
    done
    iconutil -c icns -o "$ICON_PATH" "$ICONSET" >/dev/null
  else
    log "iconutil oder sips nicht verfügbar – verwende PNG als Platzhalter"
    cp "$BASE_PNG" "$ICON_PATH"
  fi
  rm -rf "$TMP_DIR"
fi

ICON_ARGS=()
if [[ -f "$ICON_PATH" ]]; then
  ICON_ARGS=(--icon "$ICON_PATH")
fi

APP_NAME="PromptPilot"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
SPEC_FILE="$PROJECT_ROOT/${APP_NAME}.spec"
APP_BUNDLE="$DIST_DIR/${APP_NAME}.app"
rm -rf "$DIST_DIR" "$BUILD_DIR" "$SPEC_FILE"

ADD_DATA_ARGS=()
add_data() {
  local source="$1"
  local dest="$2"
  if [[ -e "$source" ]]; then
    ADD_DATA_ARGS+=(--add-data "$source:$dest")
  fi
}
add_data "$PROJECT_ROOT/presets.json" .
add_data "$PROJECT_ROOT/credentials.json" .
add_data "$PROJECT_ROOT/settings.json" .
add_data "$PROJECT_ROOT/start.sh" .

log "Starte PyInstaller"
"$VENV_PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --osx-bundle-identifier "com.promptpilot.app" \
  --hidden-import backend \
  --collect-submodules PySide6 \
  "${ICON_ARGS[@]}" \
  "${ADD_DATA_ARGS[@]}" \
  "$PROJECT_ROOT/frontend.py"

if [[ ! -d "$APP_BUNDLE" ]]; then
  log "Fehler: PyInstaller hat kein App-Bundle erzeugt"
  exit 1
fi

DESKTOP_ROOT="/Users/taavoci1"
if [[ ! -d "$DESKTOP_ROOT" ]]; then
  DESKTOP_ROOT="$HOME"
fi
DESKTOP_DIR="$DESKTOP_ROOT/Desktop"
mkdir -p "$DESKTOP_DIR"
DESKTOP_APP="$DESKTOP_DIR/${APP_NAME}.app"
rm -rf "$DESKTOP_APP"
cp -R "$APP_BUNDLE" "$DESKTOP_APP"

log "Build abgeschlossen: $DESKTOP_APP"
echo "Build erfolgreich — bitte die neue PromptPilot.app in Bedienungshilfen freigeben."
