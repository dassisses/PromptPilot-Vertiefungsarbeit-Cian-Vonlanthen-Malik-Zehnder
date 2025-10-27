#!/bin/zsh

# this Script is for installing dependencies for the Python Project
# Check if pip3 is installed
if ! command -v pip3 &>/dev/null; then
  echo "Error: pip3 is not installed. Please install pip3 and rerun this script."
  exit 1
fi

# List of dependencies to install
dependencies=(
  requests
  pyperclip
  PySide6
)

for dep in "${dependencies[@]}"; do
  if ! python3 -c "import $dep" &>/dev/null; then
    pip3 install "$dep"
  else
    echo "$dep is already installed"
  fi
done