from __future__ import annotations

import platform
import tkinter as tk
from collections.abc import Callable


ORB_STYLES = {
    "off": ("#374151", "#111827", "OFF"),
    "calibrating": ("#3b82f6", "#172554", "WAIT"),
    "ready": ("#22c55e", "#052e16", "READY"),
    "listening": ("#22d3ee", "#083344", "HEARING"),
    "recognizing": ("#a855f7", "#3b0764", "THINK"),
    "thinking": ("#a855f7", "#3b0764", "THINK"),
    "speaking": ("#f59e0b", "#451a03", "SPEAK"),
    "error": ("#ef4444", "#450a0a", "ERROR"),
}


def orb_style(state: str) -> tuple[str, str, str]:
    return ORB_STYLES.get(state, ORB_STYLES["ready"])


class FloatingOrb:
    """Small always-on-top Siri-style voice indicator."""

    def __init__(self, root: tk.Misc, on_toggle: Callable[[], None], on_show: Callable[[], None]) -> None:
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg="#010203")
        if platform.system() == "Windows":
            self.window.attributes("-transparentcolor", "#010203")
        size = 112
        x = max(12, self.window.winfo_screenwidth() - size - 28)
        y = max(12, self.window.winfo_screenheight() - size - 90)
        self.window.geometry(f"{size}x{size}+{x}+{y}")
        self.canvas = tk.Canvas(self.window, width=size, height=size, bg="#010203", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.on_toggle = on_toggle
        self.on_show = on_show
        self.state = "ready"
        self.pulse = 0
        self._click_job: str | None = None
        self._ignore_next_release = False
        self._drag_origin: tuple[int, int, int, int] | None = None
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Double-Button-1>", self._double_click)
        self._animate()

    def set_state(self, state: str) -> None:
        self.state = state if state in ORB_STYLES else "ready"
        self._draw()

    def _draw(self) -> None:
        color, center, label = orb_style(self.state)
        self.canvas.delete("all")
        active = self.state in {"calibrating", "listening", "recognizing", "thinking", "speaking"}
        expansion = self.pulse if active else 0
        self.canvas.create_oval(8 - expansion, 8 - expansion, 104 + expansion, 104 + expansion, outline=color, width=2)
        self.canvas.create_oval(17, 17, 95, 95, fill=center, outline=color, width=5)
        self.canvas.create_oval(29, 29, 83, 83, fill=color, outline="")
        self.canvas.create_text(56, 53, text="S", fill="white", font=("Segoe UI", 22, "bold"))
        self.canvas.create_text(56, 76, text=label, fill="white", font=("Segoe UI", 7, "bold"))

    def _animate(self) -> None:
        self.pulse = (self.pulse + 1) % 7
        self._draw()
        self.window.after(90, self._animate)

    def _press(self, event: tk.Event) -> None:
        self._drag_origin = (event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y())

    def _drag(self, event: tk.Event) -> None:
        if not self._drag_origin:
            return
        start_x, start_y, window_x, window_y = self._drag_origin
        self.window.geometry(f"+{window_x + event.x_root - start_x}+{window_y + event.y_root - start_y}")

    def _release(self, event: tk.Event) -> None:
        if self._ignore_next_release:
            self._ignore_next_release = False
            self._drag_origin = None
            return
        if not self._drag_origin:
            return
        moved = abs(event.x_root - self._drag_origin[0]) + abs(event.y_root - self._drag_origin[1])
        self._drag_origin = None
        if moved < 8:
            self._click_job = self.window.after(230, self._single_click)

    def _single_click(self) -> None:
        self._click_job = None
        self.on_toggle()

    def _double_click(self, _event: tk.Event) -> None:
        if self._click_job:
            self.window.after_cancel(self._click_job)
            self._click_job = None
        self._ignore_next_release = True
        self.on_show()

    def destroy(self) -> None:
        self.window.destroy()
