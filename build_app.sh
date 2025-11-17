#!/bin/bash
set -euo pipefail

EXPECTED_PROJECT_ROOT="/Users/taavoci1/PycharmProjects/Promtpilot/PromptPilot-Vertiefungsarbeit-Cian-Vonlanthen-Malik-Zehnder"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
if [[ "$PROJECT_ROOT" != "$EXPECTED_PROJECT_ROOT" ]]; then
  echo "[WARN] Skript befindet sich in $PROJECT_ROOT, erwartet wurde $EXPECTED_PROJECT_ROOT. Es wird der tatsächliche Speicherort verwendet." >&2
fi

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "[ERROR] Virtuelle Umgebung wurde nicht gefunden: $VENV_PYTHON" >&2
  exit 1
fi

START_SCRIPT="$PROJECT_ROOT/start.sh"
cat > "$START_SCRIPT" <<STARTSCRIPT
#!/bin/bash
set -euo pipefail
PROJECT_ROOT="$PROJECT_ROOT"
VENV_DIR="\$PROJECT_ROOT/.venv"
source "\$VENV_DIR/bin/activate"
cd "\$PROJECT_ROOT"
exec "\$VENV_DIR/bin/python" "\$PROJECT_ROOT/frontend.py"
STARTSCRIPT
chmod +x "$START_SCRIPT"

APP_NAME="PromptPilot"
APP_BUNDLE="$PROJECT_ROOT/${APP_NAME}.app"
if [[ -d "$APP_BUNDLE" ]]; then
  rm -rf "$APP_BUNDLE"
fi

CONTENTS_DIR="$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

INFO_PLIST="$CONTENTS_DIR/Info.plist"
cat > "$INFO_PLIST" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>PromptPilot</string>
    <key>CFBundleDisplayName</key>
    <string>PromptPilot</string>
    <key>CFBundleExecutable</key>
    <string>wrapper</string>
    <key>CFBundleIdentifier</key>
    <string>com.promptpilot.app</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

WRAPPER_SCRIPT="$MACOS_DIR/wrapper"
COMMAND="cd \"$PROJECT_ROOT\" && ./start.sh"
ESCAPED_COMMAND=$(printf '%s' "$COMMAND" | /usr/bin/env python3 - <<'PY'
import json, sys
print(json.dumps(sys.stdin.read()))
PY
)
cat > "$WRAPPER_SCRIPT" <<WRAPPER
#!/bin/bash
set -euo pipefail
PROJECT_ROOT="$PROJECT_ROOT"
START_SCRIPT="\$PROJECT_ROOT/start.sh"
if [[ ! -x "\$START_SCRIPT" ]]; then
  chmod +x "\$START_SCRIPT"
fi
osascript <<'APPLESCRIPT'
tell application "Terminal"
    activate
    do script $ESCAPED_COMMAND
end tell
APPLESCRIPT
WRAPPER
chmod +x "$WRAPPER_SCRIPT"

ICON_FILE="$RESOURCES_DIR/icon.icns"
if [[ ! -f "$ICON_FILE" ]]; then
  TMP_ICONSET="$(mktemp -d)"
  PNG_FILE="$TMP_ICONSET/icon.png"
  base64 <<'ICONDATA' > "$PNG_FILE"
iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABP0lEQVR4nO3WsQ2AMAwF0e7/0z117BBSYhgYZl9KgJKdn6mWB2wASH8S5AgwYMGDBgwIABAwb8viYwA9VPdTzqvlTn88Nuvj0KBRAgsIiqCigQwQERUQojtBW3gAwQQLLCZCdK3OwHkwuQnhdkM0YwAEBBBgZHTpnhAbocg/Rz8ARJgQgIUTAkA0tWAxBCAAQQE88eNAAgQIECBAgQIDBPwB4DVlzp0jswVgI8y9AyAIUAgAEIIABFsknyZwAAGPH6OfjSgyQ2S5Lsf4A5zgQgIEDB9r1AD4NJt8U3f72CBBAgAABAgQI8P8AxJn3nnhhVn8AAAAASUVORK5CYII=
ICONDATA
  iconutil -c icns -o "$ICON_FILE" "$TMP_ICONSET" >/dev/null 2>&1 || cp "$PNG_FILE" "$ICON_FILE"
  rm -rf "$TMP_ICONSET"
fi

USER_HOME="/Users/taavoci1"
DESKTOP_DIR="$USER_HOME/Desktop"
mkdir -p "$DESKTOP_DIR"
DESKTOP_APP="$DESKTOP_DIR/PromptPilot.app"
if [[ -d "$DESKTOP_APP" ]]; then
  rm -rf "$DESKTOP_APP"
fi
cp -R "$APP_BUNDLE" "$DESKTOP_APP"

chmod +x "$START_SCRIPT" "$WRAPPER_SCRIPT"

echo "Build erfolgreich — bitte die neue PromptPilot.app in Bedienungshilfen freigeben."
