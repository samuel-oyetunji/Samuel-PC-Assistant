@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Samuel is not installed yet. Run setup_windows.bat first.
  pause
  exit /b 1
)
start "Samuel" .venv\Scripts\pythonw.exe desktop.py
