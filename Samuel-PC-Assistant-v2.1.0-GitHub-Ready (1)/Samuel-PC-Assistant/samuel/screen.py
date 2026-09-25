from __future__ import annotations

from dataclasses import dataclass
import platform
import subprocess
import io
import ctypes
import time

from PIL import ImageGrab


@dataclass
class ScreenTarget:
    name: str
    left: int
    top: int
    right: int
    bottom: int


def capture_primary_screen(max_dimension: int = 1600) -> tuple[bytes, int, int, float, float]:
    image = ImageGrab.grab().convert("RGB")
    original_width, original_height = image.size
    ratio = min(1.0, max_dimension / max(original_width, original_height))
    if ratio < 1.0:
        image = image.resize((round(original_width * ratio), round(original_height * ratio)))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82, optimize=True)
    sent_width, sent_height = image.size
    return buffer.getvalue(), sent_width, sent_height, original_width / sent_width, original_height / sent_height


def find_screen_element(query: str) -> ScreenTarget | None:
    """Find a visible OS accessibility element by name."""
    if platform.system() == "Darwin":
        return _find_macos_element(query)
    if platform.system() != "Windows":
        return None
    from pywinauto import Desktop

    aliases = {"bin": "recycle bin", "trash": "recycle bin", "rubbish bin": "recycle bin"}
    wanted = aliases.get(query.lower().strip(), query.lower().strip())
    matches = []
    for element in Desktop(backend="uia").windows():
        try:
            candidates = [element, *element.descendants()]
        except Exception:
            candidates = [element]
        for candidate in candidates:
            try:
                name = candidate.window_text().strip()
                if name and wanted in name.lower() and candidate.is_visible():
                    rect = candidate.rectangle()
                    matches.append(ScreenTarget(name, rect.left, rect.top, rect.right, rect.bottom))
            except Exception:
                continue
    return min(matches, key=lambda item: (item.right - item.left) * (item.bottom - item.top), default=None)


def double_click_target(target: ScreenTarget) -> None:
    """Double-click the center of a previously located visible target."""
    x = round((target.left + target.right) / 2)
    y = round((target.top + target.bottom) / 2)
    system = platform.system()
    if system == "Windows":
        user32 = ctypes.windll.user32
        if not user32.SetCursorPos(x, y):
            raise OSError("Windows could not move the pointer to the target.")
        for _ in range(2):
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.12)
        return
    if system == "Darwin":
        from Quartz import CGEventCreateMouseEvent, CGEventPost, kCGEventLeftMouseDown, kCGEventLeftMouseUp
        from Quartz import kCGHIDEventTap, kCGMouseButtonLeft
        for click_count in (1, 2):
            down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (x, y), kCGMouseButtonLeft)
            up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (x, y), kCGMouseButtonLeft)
            from Quartz import CGEventSetIntegerValueField, kCGMouseEventClickState
            CGEventSetIntegerValueField(down, kCGMouseEventClickState, click_count)
            CGEventSetIntegerValueField(up, kCGMouseEventClickState, click_count)
            CGEventPost(kCGHIDEventTap, down)
            CGEventPost(kCGHIDEventTap, up)
            time.sleep(0.12)
        return
    raise OSError("Visual opening is supported only on Windows and macOS.")


def click_target(target: ScreenTarget) -> None:
    """Single-click the center of a previously verified target."""
    x = round((target.left + target.right) / 2)
    y = round((target.top + target.bottom) / 2)
    system = platform.system()
    if system == "Windows":
        user32 = ctypes.windll.user32
        if not user32.SetCursorPos(x, y):
            raise OSError("Windows could not move the pointer to the target.")
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        return
    if system == "Darwin":
        from Quartz import CGEventCreateMouseEvent, CGEventPost, kCGEventLeftMouseDown, kCGEventLeftMouseUp
        from Quartz import kCGHIDEventTap, kCGMouseButtonLeft
        for event_type in (kCGEventLeftMouseDown, kCGEventLeftMouseUp):
            event = CGEventCreateMouseEvent(None, event_type, (x, y), kCGMouseButtonLeft)
            CGEventPost(kCGHIDEventTap, event)
        return
    raise OSError("Screen clicking is supported only on Windows and macOS.")


def type_text_and_enter(text: str) -> None:
    """Type into the already focused, verified field and submit it."""
    if platform.system() == "Windows":
        from pywinauto.keyboard import send_keys
        escaped = re_escape_send_keys(text)
        send_keys(escaped, with_spaces=True, with_tabs=False, with_newlines=False, pause=0.02)
        send_keys("{ENTER}")
        return
    if platform.system() == "Darwin":
        script = 'on run argv\ntell application "System Events"\nkeystroke (item 1 of argv)\nkey code 36\nend tell\nend run'
        result = subprocess.run(["osascript", "-e", script, text], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise OSError(result.stderr.strip() or "macOS could not type into the field.")
        return
    raise OSError("Keyboard automation is supported only on Windows and macOS.")


def close_active_window() -> None:
    if platform.system() == "Windows":
        from pywinauto.keyboard import send_keys
        send_keys("%{F4}")
        return
    if platform.system() == "Darwin":
        script = 'tell application "System Events" to keystroke "w" using command down'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise OSError(result.stderr.strip() or "macOS could not close the active window.")
        return
    raise OSError("Window closing is supported only on Windows and macOS.")


def re_escape_send_keys(text: str) -> str:
    """Escape pywinauto send_keys metacharacters so user text stays literal."""
    escaped = text.replace("{", "{{}").replace("}", "{}}")
    for character in "+^%~()[]":
        escaped = escaped.replace(character, "{" + character + "}")
    return escaped


def _find_macos_element(query: str) -> ScreenTarget | None:
    aliases = {"bin": "Trash", "recycle bin": "Trash", "rubbish bin": "Trash"}
    wanted = aliases.get(query.lower().strip(), query)
    script = r'''
on run argv
  set wanted to item 1 of argv
  tell application "System Events"
    set candidates to every application process whose frontmost is true
    try
      set end of candidates to application process "Dock"
    end try
    try
      set end of candidates to application process "Finder"
    end try
    repeat with proc in candidates
      try
        repeat with elem in entire contents of proc
          try
            set elemName to name of elem as text
            if elemName contains wanted then
              set elemPos to position of elem
              set elemSize to size of elem
              return elemName & "|" & (item 1 of elemPos) & "|" & (item 2 of elemPos) & "|" & (item 1 of elemSize) & "|" & (item 2 of elemSize)
            end if
          end try
        end repeat
      end try
    end repeat
  end tell
  return ""
end run
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script, wanted], capture_output=True, text=True, timeout=8, check=False
        ).stdout.strip()
        if not result:
            return None
        name, x, y, width, height = result.split("|", 4)
        left, top = int(x), int(y)
        return ScreenTarget(name, left, top, left + int(width), top + int(height))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
