from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Settings:
    assistant_name: str = "Samuel"
    wake_phrase: str = "hey"
    model: str = "gpt-5.6"
    confirm_ai_actions: bool = True


def config_path() -> Path:
    if platform.system() == "Windows":
        root = Path(os.getenv("APPDATA", Path.home()))
    else:
        root = Path.home() / "Library" / "Application Support"
    return root / "SamuelPC" / "settings.json"


def load_settings() -> Settings:
    path = config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        allowed = {key: value for key, value in data.items() if key in Settings.__dataclass_fields__}
        settings = Settings(**allowed)
        # Migrate only Samuel's former factory default; never overwrite a
        # wake phrase the user deliberately customized.
        if settings.wake_phrase.strip().lower() == "hey samuel":
            settings.wake_phrase = "hey"
            try:
                save_settings(settings)
            except OSError:
                pass
        return settings
    except (OSError, ValueError, TypeError):
        return Settings()


def save_settings(settings: Settings) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
