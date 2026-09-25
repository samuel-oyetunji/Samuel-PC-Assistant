#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it from https://www.python.org/downloads/macos/"
  read -r -p "Press Enter to close..."
  exit 1
fi
python3 -m venv .venv
.venv/bin/python -m pip install --timeout 120 --retries 10 --upgrade pip
.venv/bin/python -m pip install --timeout 120 --retries 10 -r requirements.txt
echo "Installation completed. Open start_samuel.command."
read -r -p "Press Enter to close..."
