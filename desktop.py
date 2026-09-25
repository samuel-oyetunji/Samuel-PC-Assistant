import sys
import traceback

from samuel.desktop_app import DesktopSamuel
from samuel.platform_support import crash_log_path


if __name__ == "__main__":
    try:
        DesktopSamuel().run()
    except Exception:
        crash_log_path().write_text(traceback.format_exc(), encoding="utf-8")
        raise
