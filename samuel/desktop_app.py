from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import webbrowser
import platform
import sys
import traceback
import os
import subprocess
import time

from PIL import Image, ImageDraw
import pystray

from .commands import CommandHandler
from .brain import AIBrain
from .screen import (
    ScreenTarget, capture_primary_screen, click_target, close_active_window,
    double_click_target, find_screen_element, type_text_and_enter,
)
from .speech import SpeechEngine, extract_wake_command
from .settings import load_settings, save_settings
from .secure_store import delete_secret
from .platform_support import apply_native_theme, crash_log_path, open_permissions, prepare_display, set_startup, startup_enabled
from .layout import fitted_geometry
from .orb import FloatingOrb


class DesktopSamuel:
    def __init__(self) -> None:
        prepare_display()
        self.settings = load_settings()
        self.root = tk.Tk()
        apply_native_theme(self.root)
        self.root.title(f"{self.settings.assistant_name} PC Assistant")
        self._size_window(self.root, 720, 680)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.listening = threading.Event()
        self.closing = threading.Event()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.brain = AIBrain(self.settings.model)
        self.speech = SpeechEngine(
            lambda state: self.events.put(("voice_state", state)), self.brain.transcribe_audio
        )
        self.follow_up_until = 0.0
        self._previous_voice_state = "idle"
        self.handler = CommandHandler(
            self.say, self.point_to, self.brain, self.request_ai_setup,
            self.open_screen_item, self.analyze_current_screen,
            self.close_current_window, self.send_message_to_app
        )
        self.status = tk.StringVar(value="OFF — microphone disabled")
        self._build_ui()
        self.orb = FloatingOrb(self.root, self.toggle, self.show)
        self.listening.set()
        self.status.set(f"ON — say {self.settings.wake_phrase.title()}")
        self.toggle_button.config(text="TURN OFF")
        self.orb.set_state("calibrating")
        self._write_log("Background listening started. Single-click the orb to turn it off; double-click it to open this dashboard.")
        if not self.brain.enabled:
            self._write_log("AI brain OFF: an unknown command will offer setup options")
        self.tray = self._build_tray()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=28)
        frame.pack(fill="both", expand=True)
        self.name_label = ttk.Label(frame, text=self.settings.assistant_name.upper(), font=("Segoe UI", 28, "bold"))
        self.name_label.pack()
        ttk.Label(frame, textvariable=self.status, font=("Segoe UI", 11)).pack(pady=(4, 14))
        self.toggle_button = ttk.Button(frame, text="TURN ON", command=self.toggle)
        self.toggle_button.pack(ipadx=35, ipady=12)
        ttk.Label(frame, text="Type a command", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(16, 4))
        command_row = ttk.Frame(frame)
        command_row.pack(fill="x")
        self.command_entry = ttk.Entry(command_row)
        self.command_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.command_entry.bind("<Return>", self._submit_text)
        ttk.Button(command_row, text="SEND", command=self._submit_text).pack(side="left", padx=(8, 0), ipady=5)
        tools_row = ttk.Frame(frame)
        tools_row.pack(fill="x", pady=(10, 0))
        ttk.Button(tools_row, text="SETTINGS", command=self._show_settings).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(tools_row, text="DIAGNOSTICS", command=self._show_diagnostics).pack(side="left", expand=True, fill="x", padx=(4, 0))
        ttk.Label(frame, text="Activity", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(18, 4))
        self.log = tk.Text(frame, height=12, state="disabled", wrap="word", padx=10, pady=10)
        self.log.pack(fill="both", expand=True)
        ttk.Label(frame, text="Closing this window keeps Samuel in the system tray.").pack(pady=(8, 0))

    def _build_tray(self) -> pystray.Icon:
        image = Image.new("RGB", (64, 64), "#111827")
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill="#22c55e")
        draw.text((23, 18), "S", fill="white")
        menu = pystray.Menu(
            pystray.MenuItem("Show Samuel", lambda: self.root.after(0, self.show)),
            pystray.MenuItem("Turn on/off", lambda: self.root.after(0, self.toggle)),
            pystray.MenuItem("Exit", lambda: self.root.after(0, self.exit)),
        )
        return pystray.Icon("Samuel", image, "Samuel PC Assistant", menu)

    def run(self) -> None:
        threading.Thread(target=self.tray.run, daemon=True).start()
        threading.Thread(target=self._voice_loop, daemon=True).start()
        self.root.after(100, self._drain_events)
        self.root.after(150, self.hide)
        self.root.mainloop()

    def toggle(self) -> None:
        if self.listening.is_set():
            self.listening.clear()
            self.status.set("OFF — microphone disabled")
            self.toggle_button.config(text="TURN ON")
            self.orb.set_state("off")
            self._write_log("Listening turned off")
        else:
            self.listening.set()
            self.status.set(f"ON — say {self.settings.wake_phrase.title()}")
            self.toggle_button.config(text="TURN OFF")
            self.orb.set_state("ready")
            self._write_log("Listening turned on")

    def _submit_text(self, _event: object = None) -> None:
        command = self.command_entry.get().strip()
        if not command:
            return
        self.command_entry.delete(0, "end")
        self._write_log(f"You typed: {command}")
        self.orb.set_state("thinking")
        threading.Thread(target=self.handler.handle, args=(command,), daemon=True).start()

    def _voice_loop(self) -> None:
        while not self.closing.is_set():
            if not self.listening.wait(timeout=0.5):
                continue
            command = self.speech.listen()
            if not command or command.startswith("/"):
                continue
            self.events.put(("heard", command))

    def _drain_events(self) -> None:
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "heard":
                command = str(value)
                self._write_log(f"You: {command}")
                woke, command = extract_wake_command(
                    command, self.settings.wake_phrase, self.settings.assistant_name
                )
                in_follow_up = time.monotonic() < self.follow_up_until
                if command and (woke or self.handler.pending or in_follow_up):
                    self.orb.set_state("thinking")
                    threading.Thread(target=self.handler.handle, args=(command,), daemon=True).start()
                else:
                    if command and not woke:
                        self._write_log(
                            f'Ignored voice: "{command}" — wake phrase not detected. '
                            f'Say "{self.settings.wake_phrase}" first.'
                        )
                    self.orb.set_state("ready" if self.listening.is_set() else "off")
            elif kind == "point":
                self._show_highlight(value)
            elif kind == "log":
                self._write_log(str(value))
            elif kind == "ai_setup":
                self._show_ai_choices()
            elif kind == "voice_state":
                self._apply_voice_state(str(value))
        if not self.closing.is_set():
            self.root.after(100, self._drain_events)

    def say(self, text: str) -> None:
        self.events.put(("log", f"Samuel: {text}"))
        self.speech.speak(text)

    def point_to(self, query: str) -> None:
        self.say(f"Looking for {query} on your screen.")
        target = find_screen_element(query)
        if target:
            self.events.put(("point", target))
            self.say(f"I found {target.name}. I am highlighting it now.")
            return
        if not self.brain.enabled:
            self.say(f"I could not identify {query} locally. Connect an OpenAI API key for AI vision.")
            self.request_ai_setup()
            return
        self.say("AI screen analysis is active. I am capturing the primary screen now.")
        try:
            image, width, height, scale_x, scale_y = capture_primary_screen()
            location = self.brain.locate_visual(image, query, width, height)
            del image
            if not location:
                self.say(f"I could not confidently locate {query} on the screen.")
                return
            left, top = round(location["x"] * scale_x), round(location["y"] * scale_y)
            target = ScreenTarget(
                location["label"] or query, left, top,
                left + max(25, round(location["width"] * scale_x)),
                top + max(25, round(location["height"] * scale_y)),
            )
            self.events.put(("point", target))
            self.say(f"I found {target.name} with AI vision and highlighted it.")
        except Exception as exc:
            print(f"Vision error: {exc}")
            self.say("AI vision could not complete the screen analysis.")

    def open_screen_item(self, query: str) -> None:
        self.say(f"Looking for {query} on your screen before opening it.")
        target = find_screen_element(query)
        used_ai = False
        try:
            if not target:
                if not self.brain.enabled:
                    self.say(f"I could not identify {query} locally. Connect an OpenAI API key for AI vision.")
                    self.request_ai_setup()
                    return
                used_ai = True
                self.say("AI screen analysis is active. I am capturing the primary screen now.")
                image, width, height, scale_x, scale_y = capture_primary_screen()
                location = self.brain.locate_visual(image, query, width, height)
                del image
                if not location or float(location.get("confidence", 0)) < 0.70:
                    self.say(f"I could not confidently locate {query}, so I did not click anything.")
                    return
                left, top = round(location["x"] * scale_x), round(location["y"] * scale_y)
                target = ScreenTarget(
                    location["label"] or query, left, top,
                    left + max(25, round(location["width"] * scale_x)),
                    top + max(25, round(location["height"] * scale_y)),
                )
            double_click_target(target)
            self.events.put(("point", target))
            source = " with AI vision" if used_ai else ""
            self.say(f"I found {target.name}{source} and double-clicked it.")
        except Exception as exc:
            print(f"Visual open error: {exc}")
            self.say(f"I found {query}, but I could not safely double-click it.")

    def analyze_current_screen(self, request: str) -> None:
        if not self.brain.enabled:
            self.say("Screen description needs my AI brain. Connect an OpenAI API key first.")
            self.request_ai_setup()
            return
        self.say("AI screen analysis is active. I am capturing the primary screen now.")
        try:
            image, width, height, _scale_x, _scale_y = capture_primary_screen()
            summary = self.brain.describe_screen(image, request, width, height)
            del image
            if not summary:
                self.say("I captured the screen, but I could not produce a reliable description.")
                return
            self.say(summary)
        except Exception as exc:
            print(f"Screen description error: {exc}")
            self.say("I could not complete the screen description.")

    def close_current_window(self) -> None:
        self.say("Closing the active window now.")
        try:
            close_active_window()
        except Exception as exc:
            print(f"Close window error: {exc}")
            self.say("I could not close the active window.")

    def send_message_to_app(self, app: str, message: str) -> None:
        if app != "chatgpt":
            self.say(f"I do not have a verified message workflow for {app}.")
            return
        self.say("Opening ChatGPT and waiting for its message box.")
        try:
            if platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", "ChatGPT"], shell=False)
            elif platform.system() == "Windows":
                os.startfile("chatgpt:")  # type: ignore[attr-defined]
            else:
                raise OSError("Unsupported operating system.")
            time.sleep(2.5)
            target = None
            for query in ("Message ChatGPT", "Ask anything", "message", "prompt"):
                target = find_screen_element(query)
                if target:
                    break
            if not target:
                if not self.brain.enabled:
                    self.say("I opened ChatGPT but could not verify its message box locally, so I typed nothing.")
                    return
                self.say("I am using AI vision to verify the ChatGPT message box before typing.")
                image, width, height, scale_x, scale_y = capture_primary_screen()
                location = self.brain.locate_visual(image, "ChatGPT message input box", width, height)
                del image
                if not location or float(location.get("confidence", 0)) < 0.75:
                    self.say("I could not confidently verify the ChatGPT message box, so I typed nothing.")
                    return
                left, top = round(location["x"] * scale_x), round(location["y"] * scale_y)
                target = ScreenTarget(
                    location["label"] or "ChatGPT message box", left, top,
                    left + max(60, round(location["width"] * scale_x)),
                    top + max(30, round(location["height"] * scale_y)),
                )
            click_target(target)
            time.sleep(0.25)
            type_text_and_enter(message)
            self.say("Message sent to ChatGPT.")
        except Exception as exc:
            print(f"ChatGPT messaging error: {exc}")
            self.say("I could not safely send the message to ChatGPT.")

    def request_ai_setup(self) -> None:
        self.events.put(("ai_setup", None))

    def _show_ai_choices(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("AI key required")
        self._size_window(dialog, 600, 360)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        frame = ttk.Frame(dialog, padding=28)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="This command needs the AI brain", font=("Segoe UI", 14, "bold")).pack(pady=(0, 8))
        ttk.Label(
            frame,
            text="Connect your own OpenAI API key. API usage is billed to your OpenAI Platform account.",
            wraplength=520,
            justify="center",
        ).pack(pady=(0, 18))
        ttk.Button(frame, text="Never mind", command=dialog.destroy).pack(fill="x", pady=3)
        ttk.Button(frame, text="Add existing API key", command=lambda: (dialog.destroy(), self._ask_for_key())).pack(fill="x", pady=3)
        ttk.Button(frame, text="Create/fund account and add key", command=lambda: (dialog.destroy(), self._register_and_add())).pack(fill="x", pady=3)

    def _register_and_add(self) -> None:
        webbrowser.open("https://platform.openai.com/api-keys")
        webbrowser.open("https://platform.openai.com/settings/organization/billing/overview")
        messagebox.showinfo(
            "OpenAI setup",
            "1. Sign in or create an OpenAI Platform account.\n"
            "2. Add billing credit on the Billing page.\n"
            "3. Create a new secret key on the API Keys page.\n"
            "4. Copy the key, return here, and paste it in the next box.\n\n"
            "ChatGPT Plus and API billing are separate.",
        )
        self._ask_for_key()

    def _ask_for_key(self) -> None:
        key = simpledialog.askstring("Connect OpenAI", "Paste your OpenAI API key:", show="*", parent=self.root)
        if not key:
            return
        try:
            self.brain.save_key(key)
        except Exception as exc:
            messagebox.showerror("Key not saved", str(exc))
            return
        self._write_log("AI brain ON — key stored in the operating system credential vault")
        messagebox.showinfo("AI connected", "Samuel's AI brain is now enabled. You do not need to restart.")

    def _show_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Samuel settings")
        self._size_window(dialog, 640, 680)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        frame = ttk.Frame(dialog, padding=28)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Settings", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Personalize Samuel and manage desktop permissions.").pack(anchor="w", pady=(2, 18))
        name = tk.StringVar(value=self.settings.assistant_name)
        wake = tk.StringVar(value=self.settings.wake_phrase)
        model = tk.StringVar(value=self.settings.model)
        identity = ttk.LabelFrame(frame, text="Assistant", padding=16)
        identity.pack(fill="x", pady=(0, 14))
        for label, variable in (("Assistant name", name), ("Wake phrase", wake), ("OpenAI model", model)):
            ttk.Label(identity, text=label).pack(anchor="w")
            ttk.Entry(identity, textvariable=variable, font=("Segoe UI", 11)).pack(fill="x", ipady=5, pady=(3, 11))

        def apply() -> None:
            if not name.get().strip() or not wake.get().strip():
                messagebox.showerror("Invalid settings", "Name and wake phrase cannot be empty.", parent=dialog)
                return
            self.settings.assistant_name = name.get().strip()
            self.settings.wake_phrase = wake.get().strip().lower()
            self.settings.model = model.get().strip() or "gpt-5.6"
            save_settings(self.settings)
            self.brain.model = self.settings.model
            self.name_label.config(text=self.settings.assistant_name.upper())
            self.root.title(f"{self.settings.assistant_name} PC Assistant")
            dialog.destroy()
            self._write_log("Settings saved")

        ttk.Button(frame, text="SAVE SETTINGS", command=apply).pack(fill="x", ipady=7, pady=(0, 14))
        ai_group = ttk.LabelFrame(frame, text="AI connection", padding=12)
        ai_group.pack(fill="x", pady=(0, 12))
        ttk.Button(ai_group, text="ADD / REPLACE API KEY", command=lambda: (dialog.destroy(), self._ask_for_key())).pack(fill="x", ipady=4, pady=3)
        ttk.Button(ai_group, text="REMOVE API KEY", command=lambda: self._remove_api_key(dialog)).pack(fill="x", ipady=4, pady=3)
        system_group = ttk.LabelFrame(frame, text="System", padding=12)
        system_group.pack(fill="x")
        ttk.Button(system_group, text="OPEN OS PERMISSIONS", command=open_permissions).pack(fill="x", ipady=4, pady=3)
        ttk.Button(system_group, text="TEST VOICE", command=lambda: self.say("Voice test successful. Samuel can speak clearly.")).pack(fill="x", ipady=4, pady=3)
        startup_text = "DISABLE START AT LOGIN" if startup_enabled() else "ENABLE START AT LOGIN"
        ttk.Button(system_group, text=startup_text, command=lambda: self._toggle_startup(dialog)).pack(fill="x", ipady=4, pady=3)

    def _toggle_startup(self, dialog: tk.Toplevel) -> None:
        try:
            set_startup(not startup_enabled())
            messagebox.showinfo("Start at login", "Start-at-login setting updated.", parent=dialog)
        except Exception as exc:
            messagebox.showerror("Start at login", str(exc), parent=dialog)

    def _remove_api_key(self, dialog: tk.Toplevel) -> None:
        if not messagebox.askyesno("Remove API key", "Disconnect the saved OpenAI API key?", parent=dialog):
            return
        delete_secret()
        self.brain.api_key = None
        self.brain.enabled = False
        self._write_log("AI key removed; local command mode active")
        dialog.destroy()

    def _show_diagnostics(self) -> None:
        try:
            import sounddevice as sd
            devices = len(sd.query_devices())
            audio = f"Audio devices detected: {devices}"
        except Exception as exc:
            audio = f"Audio check failed: {exc}"
        report = (
            f"Samuel PC Assistant 2.1.0\n"
            f"Operating system: {platform.platform()}\n"
            f"Python: {sys.version.split()[0]}\n"
            f"AI brain: {'ON' if self.brain.enabled else 'OFF'}\n"
            f"Model: {self.brain.model}\n"
            f"Wake phrase: {self.settings.wake_phrase}\n"
            f"Speech output: {self.speech.output_status}\n"
            f"Voice recognition: {self.speech.transcription_status}\n"
            f"{audio}"
        )
        messagebox.showinfo("Diagnostics", report, parent=self.root)

    def _show_highlight(self, target: object) -> None:
        left, top = target.left, target.top
        width = max(50, target.right - target.left)
        height = max(50, target.bottom - target.top)
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-transparentcolor", "white")
        overlay.geometry(f"{width + 30}x{height + 30}+{max(0, left - 15)}+{max(0, top - 15)}")
        canvas = tk.Canvas(overlay, bg="white", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_oval(4, 4, width + 25, height + 25, outline="#ff2d2d", width=6)
        overlay.after(3500, overlay.destroy)

    def _write_log(self, text: str) -> None:
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _apply_voice_state(self, state: str) -> None:
        if state == "idle" and self._previous_voice_state == "speaking":
            self.follow_up_until = time.monotonic() + 12.0
        self._previous_voice_state = state
        if state == "idle":
            state = "ready" if self.listening.is_set() else "off"
        elif not self.listening.is_set() and state != "speaking":
            state = "off"
        self.orb.set_state(state)
        labels = {
            "off": "OFF — microphone disabled",
            "calibrating": "CALIBRATING — wait for READY",
            "ready": f"READY — say {self.settings.wake_phrase.title()}",
            "listening": "HEARING — speak naturally",
            "recognizing": "RECOGNIZING — processing your voice",
            "thinking": "THINKING",
            "speaking": "SPEAKING",
            "error": "VOICE ERROR — open Diagnostics",
        }
        self.status.set(labels.get(state, labels["ready"]))

    @staticmethod
    def _size_window(window: tk.Misc, preferred_width: int, preferred_height: int) -> None:
        window.update_idletasks()
        geometry, minimum_width, minimum_height = fitted_geometry(
            window.winfo_screenwidth(), window.winfo_screenheight(), preferred_width, preferred_height
        )
        window.geometry(geometry)
        window.minsize(minimum_width, minimum_height)

    def hide(self) -> None:
        self.root.withdraw()

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def exit(self) -> None:
        self.closing.set()
        self.listening.set()
        self.speech.close()
        self.orb.destroy()
        self.tray.stop()
        self.root.destroy()
