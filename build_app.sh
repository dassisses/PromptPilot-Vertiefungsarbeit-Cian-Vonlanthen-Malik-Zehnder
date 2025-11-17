#!/usr/bin/env bash
set -euo pipefail

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

if [[ ! -d "$PROJECT_ROOT" ]]; then
  echo "Projektverzeichnis nicht gefunden: $PROJECT_ROOT" >&2
  exit 1
fi

if [[ ! -f "$MAIN_SCRIPT" ]]; then
  echo "Startskript nicht gefunden: $MAIN_SCRIPT" >&2
  exit 1
fi

cd "$PROJECT_ROOT"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python-Binary nicht gefunden: $PYTHON_BIN" >&2
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller

if [[ ! -f "$SPEC_FILE" ]]; then
  cat <<'SPEC' > "$SPEC_FILE"
# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_submodules

project_root = os.path.abspath(os.path.dirname(__file__))
venv_path = os.path.join(project_root, '.venv')
python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
site_packages = os.path.join(venv_path, 'lib', python_version, 'site-packages')
pathex = [project_root]
if os.path.isdir(site_packages):
    pathex.append(site_packages)

hiddenimports = []
for pkg in ('PySide6', 'Quartz', 'pynput'):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

block_cipher = None
icon_file = os.path.join(project_root, 'icon.icns')

a = Analysis(
    ['frontend.py'],
    pathex=pathex,
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PromptPilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
app = BUNDLE(
    exe,
    name='PromptPilot.app',
    icon=icon_file if os.path.exists(icon_file) else None,
    bundle_identifier='com.promptpilot.app',
)
SPEC
fi

rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

pyinstaller promptpilot.spec --clean --noconfirm

if [[ ! -d "$APP_PATH" ]]; then
  echo "Build fehlgeschlagen – $APP_PATH wurde nicht erstellt." >&2
  exit 1
fi

mkdir -p "$DESKTOP_PATH"
DESKTOP_APP="$DESKTOP_PATH/$APP_NAME"
rm -rf "$DESKTOP_APP"
cp -R "$APP_PATH" "$DESKTOP_PATH/"

if [[ ! -d "$DESKTOP_APP" ]]; then
  echo "Fehler beim Kopieren nach $DESKTOP_APP" >&2
  exit 1
fi

echo "Build erfolgreich – neue PromptPilot.app wurde auf den Desktop kopiert."
