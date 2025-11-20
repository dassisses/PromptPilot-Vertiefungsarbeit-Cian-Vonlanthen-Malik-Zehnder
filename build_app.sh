#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------------------
# KONFIGURATION
# --------------------------------------------------------

PROJECT_ROOT="/Users/taavoci1/PycharmProjects/VA/PromptPilot-Vertiefungsarbeit-Cian-Vonlanthen-Malik-Zehnder"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
SPEC_FILE="$PROJECT_ROOT/promptpilot.spec"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"
APP_NAME="PromptPilot.app"
APP_PATH="$DIST_DIR/$APP_NAME"
DESKTOP_PATH="$HOME/Desktop"
ICON_FILE="$PROJECT_ROOT/icon.icns"
MAIN_SCRIPT="$PROJECT_ROOT/frontend.py"

# --------------------------------------------------------
# GRUNDPRÜFUNGEN
# --------------------------------------------------------

if [[ ! -d "$PROJECT_ROOT" ]]; then
  echo "❌ Projektverzeichnis nicht gefunden: $PROJECT_ROOT" >&2
  exit 1
fi

if [[ ! -f "$MAIN_SCRIPT" ]]; then
  echo "❌ Startskript frontend.py nicht gefunden: $MAIN_SCRIPT" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "❌ Python-Binary nicht gefunden: $PYTHON_BIN" >&2
  exit 1
fi

cd "$PROJECT_ROOT"

echo "🔧 Aktiviere virtuelle Umgebung…"
# shellcheck disable=SC1091
source "$PROJECT_ROOT/.venv/bin/activate"

echo "🔧 Aktualisiere pip & installiere PyInstaller…"
/usr/bin/env python3 -m pip install --upgrade pip
/usr/bin/env python3 -m pip install pyinstaller
/usr/bin/env python3 -m pip install PySide6 pynput pyobjc-framework-Quartz

# --------------------------------------------------------
# SPEC-DATEI AUTOMATISCH ERZEUGEN (KORREKT!)
# --------------------------------------------------------

echo "🔧 Erzeuge korrekte promptpilot.spec …"

cat <<'SPEC' > "$SPEC_FILE"
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = os.getcwd()

VENV_PATH = os.path.join(PROJECT_ROOT, '.venv')
PY_MAJOR = sys.version_info.major
PY_MINOR = sys.version_info.minor
SITE_PACKAGES = os.path.join(VENV_PATH, 'lib', f'python{PY_MAJOR}.{PY_MINOR}', 'site-packages')

pathex = [PROJECT_ROOT]
if os.path.isdir(SITE_PACKAGES):
    pathex.append(SITE_PACKAGES)

hiddenimports = []
for pkg in ("PySide6", "Quartz", "pynput"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

block_cipher = None

a = Analysis(
    ['frontend.py'],
    pathex=pathex,
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'presets.json'), '.'),
        (os.path.join(PROJECT_ROOT, 'settings.json'), '.'),
        (os.path.join(PROJECT_ROOT, 'credentials.json'), '.'),
        (os.path.join(PROJECT_ROOT, 'promtpilot_icon.png'), 'resources'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PromptPilot",
    console=False,
    debug=False,
    strip=False,
    upx=True,
)

app = BUNDLE(
    exe,
    name="PromptPilot.app",
    icon=os.path.join(PROJECT_ROOT, 'icon.icns') if os.path.exists(os.path.join(PROJECT_ROOT, 'icon.icns')) else None,
    bundle_identifier="com.promptpilot.app"
)
SPEC

# --------------------------------------------------------
# BUILD
# --------------------------------------------------------

echo "🧹 Lösche alte Build-Ordner…"
rm -rf "$BUILD_DIR" "$DIST_DIR"

echo "🏗 Starte PyInstaller Build…"
/usr/bin/env python3 -m PyInstaller "$SPEC_FILE" --clean --noconfirm

if [[ ! -d "$APP_PATH" ]]; then
  echo "❌ Build fehlgeschlagen – $APP_PATH wurde nicht erstellt." >&2
  exit 1
fi

# --------------------------------------------------------
# APP AUF DEN DESKTOP KOPIEREN
# --------------------------------------------------------

echo "📦 Kopiere .app auf Desktop…"
mkdir -p "$DESKTOP_PATH"
DESKTOP_APP="$DESKTOP_PATH/$APP_NAME"
rm -rf "$DESKTOP_APP"
cp -R "$APP_PATH" "$DESKTOP_PATH/"

if [[ ! -d "$DESKTOP_APP" ]]; then
  echo "❌ Fehler beim Kopieren nach $DESKTOP_APP" >&2
  exit 1
fi

echo "🎉 Build erfolgreich – neue PromptPilot.app wurde auf den Desktop kopiert!"
