#!/bin/bash

set -e

echo "===> Aktivieren der virtuellen Umgebung…"
source .venv/bin/activate

echo "===> Abhängigkeiten installieren..."
pip install -r requirements.txt
pip install pyinstaller

echo "===> Entferne alte Builds..."
rm -rf build dist PromptPilot.app

echo "===> Starte PyInstaller..."
pyinstaller promptpilot.spec

echo "===> Kopiere Backend-Dateien..."
mkdir -p dist/PromptPilot.app/Contents/Resources/appdata

cp backend.py dist/PromptPilot.app/Contents/Resources/appdata/
cp presets.json dist/PromptPilot.app/Contents/Resources/appdata/
cp credentials.json dist/PromptPilot.app/Contents/Resources/appdata/
cp settings.json dist/PromptPilot.app/Contents/Resources/appdata/

echo "===> Fix: App icon + start script"
cp start.sh dist/PromptPilot.app/Contents/MacOS/start

chmod +x dist/PromptPilot.app/Contents/MacOS/start

echo "===> Fertig! App befindet sich unter:"
echo "dist/PromptPilot.app"
