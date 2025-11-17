#!/usr/bin/env bash
set -euo pipefail

APP_NAME="PromptPilot.app"
SPEC_FILE="promptpilot.spec"
BUILD_DIR="build"
DIST_DIR="dist"
APP_PATH="$DIST_DIR/$APP_NAME"
RESOURCES_DIR="$APP_PATH/Contents/Resources/resources"
MACOS_DIR="$APP_PATH/Contents/MacOS"

printf '===> Cleaning previous build artifacts...\n'
rm -rf "$BUILD_DIR" "$DIST_DIR"

printf '===> Running PyInstaller with %s...\n' "$SPEC_FILE"
pyinstaller "$SPEC_FILE"

printf '===> Preparing resource directory...\n'
mkdir -p "$RESOURCES_DIR"

for resource in presets.json credentials.json settings.json backend.py; do
    printf '     -> Installing %s into app resources...\n' "$resource"
    cp "$resource" "$RESOURCES_DIR/"
done

printf '===> Installing custom start launcher...\n'
install -m 755 start "$MACOS_DIR/start"

printf '===> Applying custom Info.plist...\n'
cp Info.plist "$APP_PATH/Contents/Info.plist"

printf '===> Final app available at: %s\n' "$APP_PATH"
