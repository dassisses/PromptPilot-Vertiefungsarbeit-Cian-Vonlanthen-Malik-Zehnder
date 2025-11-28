# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = os.getcwd()
ICONS_DIR = os.path.join(PROJECT_ROOT, "resources", "icons")
APP_ICON_PNG = os.path.join(ICONS_DIR, "promtpilot_icon_app.png")

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
        (os.path.join(ICONS_DIR, 'promtpilot_icon_tray.png'), os.path.join('resources', 'icons')),
        (os.path.join(ICONS_DIR, 'promtpilot_icon_app.png'), os.path.join('resources', 'icons')),
        (os.path.join(ICONS_DIR, 'icon.icns'), os.path.join('resources', 'icons')),
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
    [],
    exclude_binaries=True,
    name="PromptPilot",
    console=False,
    debug=False,
    strip=False,
    upx=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="PromptPilot",
)

app = BUNDLE(
    coll,
    name="PromptPilot.app",
    icon=(
        os.path.join(ICONS_DIR, 'icon.icns')
        if os.path.exists(os.path.join(ICONS_DIR, 'icon.icns'))
        else (APP_ICON_PNG if os.path.exists(APP_ICON_PNG) else None)
    ),
    bundle_identifier="com.promptpilot.app"
)
