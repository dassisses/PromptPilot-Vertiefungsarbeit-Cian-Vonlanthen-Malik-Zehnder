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
