#!/bin/bash
# Double-click this file on macOS (or run it in a terminal on Linux).
cd "$(dirname "$0")"
PY=python3
command -v $PY >/dev/null 2>&1 || { echo "Python 3 is not installed. Get it from https://www.python.org/downloads/"; read -p "Press Enter to close"; exit 1; }
if ! $PY -c "import numpy, PIL, customtkinter" >/dev/null 2>&1; then
  echo "First run: installing the required packages..."
  $PY -m pip install -r requirements.txt || { echo "Install failed."; read -p "Press Enter to close"; exit 1; }
fi
$PY main.py || { echo "Something went wrong."; read -p "Press Enter to close"; exit 1; }
