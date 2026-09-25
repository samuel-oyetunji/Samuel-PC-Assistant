#!/bin/bash
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Run setup_macos.command first."
  read -r -p "Press Enter to close..."
  exit 1
fi
.venv/bin/python desktop.py
