from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
import json
import os
from pathlib import Path
import platform
import re
import subprocess


@dataclass(frozen=True)
class InstalledApp:
    name: str
    target: str
    kind: str


def _normalized(value: str) -> str:
    value = Path(value).stem.lower()
    value = re.sub(r"\b(?:app|application|desktop)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def choose_app(query: str, apps: list[InstalledApp]) -> InstalledApp | None:
    wanted = _normalized(query)
    if not wanted:
        return None
    ranked: list[tuple[float, int, InstalledApp]] = []
    for app in apps:
        candidate = _normalized(app.name)
        if not candidate:
            continue
        if candidate == wanted:
            score = 0.0
        elif re.search(rf"\b{re.escape(wanted)}\b", candidate):
            score = 5.0
        elif wanted in candidate or candidate in wanted:
            score = 12.0
        else:
            similarity = SequenceMatcher(None, wanted, candidate).ratio()
            if similarity < 0.72:
                continue
            score = 100.0 - similarity * 100.0
        ranked.append((score, len(candidate), app))
    return min(ranked, key=lambda item: (item[0], item[1]), default=(0, 0, None))[2]


def find_installed_app(query: str) -> InstalledApp | None:
    return choose_app(query, list(discover_installed_apps()))


@lru_cache(maxsize=1)
def discover_installed_apps() -> tuple[InstalledApp, ...]:
    if platform.system() == "Windows":
        return tuple(_discover_windows_apps())
    if platform.system() == "Darwin":
        return tuple(_discover_macos_apps())
    return ()


def _discover_windows_apps() -> list[InstalledApp]:
    apps: list[InstalledApp] = []
    roots = [
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
    ]
    for root in roots:
        if root.is_dir():
            apps.extend(InstalledApp(item.stem, str(item), "file") for item in root.rglob("*.lnk"))
    try:
        import winreg
        modes = (winreg.KEY_READ, winreg.KEY_READ | winreg.KEY_WOW64_32KEY, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for access in modes:
                try:
                    root_key = winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\App Paths", 0, access)
                except OSError:
                    continue
                with root_key:
                    index = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(root_key, index)
                            index += 1
                            with winreg.OpenKey(root_key, sub_name) as sub_key:
                                target = winreg.QueryValue(sub_key, None)
                            if target and Path(target).exists():
                                apps.append(InstalledApp(Path(sub_name).stem, target, "file"))
                        except OSError:
                            break
    except ImportError:
        pass
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            records = json.loads(result.stdout)
            if isinstance(records, dict):
                records = [records]
            for record in records:
                name, app_id = str(record.get("Name", "")).strip(), str(record.get("AppID", "")).strip()
                if name and app_id:
                    apps.append(InstalledApp(name, app_id, "store"))
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return _deduplicate(apps)


def _discover_macos_apps() -> list[InstalledApp]:
    apps: list[InstalledApp] = []
    for root in (Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications"):
        if root.is_dir():
            apps.extend(InstalledApp(item.stem, str(item), "mac_app") for item in root.glob("*.app"))
    return _deduplicate(apps)


def _deduplicate(apps: list[InstalledApp]) -> list[InstalledApp]:
    unique: dict[tuple[str, str], InstalledApp] = {}
    for app in apps:
        normalized_name = _normalized(app.name)
        if any(word in normalized_name.split() for word in ("uninstall", "uninstaller", "unins", "remove", "repair")):
            continue
        unique.setdefault((normalized_name, app.target.lower()), app)
    return list(unique.values())


def launch_installed_app(app: InstalledApp) -> None:
    if app.kind == "store":
        subprocess.Popen(["explorer.exe", rf"shell:AppsFolder\{app.target}"], shell=False)
    elif app.kind == "mac_app":
        subprocess.Popen(["open", "-a", app.target], shell=False)
    elif platform.system() == "Windows":
        os.startfile(app.target)  # type: ignore[attr-defined]
    else:
        subprocess.Popen([app.target], shell=False)
