# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
RESOURCE_TARGET = 'resources/resources'

def _resource(path):
    return os.path.join(PROJECT_ROOT, path)

pyside6_hidden = collect_submodules('PySide6')
pynput_hidden = collect_submodules('pynput')
extra_hidden = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'pynput.keyboard',
    'pynput.mouse',
    'Quartz',
]

hiddenimports = sorted(set(pyside6_hidden + pynput_hidden + extra_hidden))

datas = [
    (_resource('presets.json'), RESOURCE_TARGET),
    (_resource('credentials.json'), RESOURCE_TARGET),
    (_resource('settings.json'), RESOURCE_TARGET),
    (_resource('backend.py'), RESOURCE_TARGET),
]

a = Analysis(
    ['frontend.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
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
    [],
    exclude_binaries=True,
    name='PromptPilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PromptPilot'
)
app = BUNDLE(
    coll,
    name='PromptPilot.app',
    icon=None,
    bundle_identifier='ch.promptpilot.app'
)
