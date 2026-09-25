from __future__ import annotations

import os
import platform
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path


def prepare_display() -> None:
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def apply_native_theme(root) -> None:
    from tkinter import ttk
    style = ttk.Style(root)
    preferred = "vista" if platform.system() == "Windows" else "aqua"
    if preferred in style.theme_names():
        style.theme_use(preferred)


def startup_enabled() -> bool:
    return _startup_path().exists()


def set_startup(enabled: bool) -> None:
    target = _startup_path()
    if not enabled:
        if target.exists():
            target.unlink()
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    project = Path(__file__).resolve().parent.parent
    if platform.system() == "Windows":
        target.write_text(f'@echo off\nstart "" "{project / "start_samuel.bat"}"\n', encoding="utf-8")
    elif platform.system() == "Darwin":
        python = project / ".venv" / "bin" / "python"
        data = {
            "Label": "com.samuelpc.assistant",
            "ProgramArguments": [str(python), str(project / "desktop.py")],
            "RunAtLoad": True,
            "WorkingDirectory": str(project),
            "StandardOutPath": str(project / "samuel-startup.log"),
            "StandardErrorPath": str(project / "samuel-startup.log"),
        }
        with target.open("wb") as handle:
            plistlib.dump(data, handle)


def open_permissions() -> None:
    system = platform.system()
    if system == "Windows":
        os.startfile("ms-settings:privacy-microphone")  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"])


def crash_log_path() -> Path:
    system = platform.system()
    if system == "Windows":
        root = Path(os.getenv("LOCALAPPDATA", Path.home()))
    elif system == "Darwin":
        root = Path.home() / "Library" / "Logs"
    else:
        root = Path(os.getenv("XDG_STATE_HOME", tempfile.gettempdir()))
    path = root / "SamuelPC" / "samuel-crash.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _startup_path() -> Path:
    if platform.system() == "Windows":
        return Path(os.getenv("APPDATA", Path.home())) / "Microsoft/Windows/Start Menu/Programs/Startup/Samuel Assistant.bat"
    return Path.home() / "Library/LaunchAgents/com.samuelpc.assistant.plist"
