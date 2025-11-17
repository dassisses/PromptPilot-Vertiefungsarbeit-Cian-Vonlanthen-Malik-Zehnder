#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd )"

# Resource directory mit backend, presets etc.
export PYTHONPATH="$DIR/../Resources/resources"

# Starte das echte PyInstaller-Binary
exec "$DIR/PromptPilot"
