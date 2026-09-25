from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import webbrowser
from difflib import get_close_matches
from collections.abc import Callable
from urllib.parse import quote_plus

from .brain import AIBrain, ProposedAction
from .app_discovery import find_installed_app, launch_installed_app


WEBSITES = {
    "facebook": "https://www.facebook.com",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
}

WINDOWS_APPS = {
    "notepad": "notepad",
    "calculator": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "command prompt": "cmd",
    "settings": "ms-settings:",
    "chatgpt": "chatgpt:",
}

MAC_APPS = {
    "chrome": "Google Chrome",
    "notepad": "TextEdit",
    "calculator": "Calculator",
    "file explorer": "Finder",
    "explorer": "Finder",
    "settings": "System Settings",
    "command prompt": "Terminal",
    "chatgpt": "ChatGPT",
}

APP_ALIASES = {
    "google chrome": "chrome",
    "chrome browser": "chrome",
    "windows settings": "settings",
    "files": "file explorer",
    "chat gpt": "chatgpt",
    "chat gpt app": "chatgpt",
    "chatgpt app": "chatgpt",
}

YES_WORDS = {"yes", "y", "yes please", "sure", "sure please", "okay", "ok", "do it", "open it", "okay open", "ok open", "continue", "proceed"}
NO_WORDS = {"no", "n", "nope", "nvm", "cancel", "never mind", "nevermind", "stop"}


class CommandHandler:
    def __init__(self, speak: Callable[[str], None], point_to: Callable[[str], None] | None = None,
                 brain: AIBrain | None = None, need_ai: Callable[[], None] | None = None,
                 open_visual: Callable[[str], None] | None = None,
                 analyze_screen: Callable[[str], None] | None = None,
                 close_window: Callable[[], None] | None = None,
                 message_app: Callable[[str, str], None] | None = None) -> None:
        self.speak = speak
        self.point_to = point_to
        self.brain = brain
        self.need_ai = need_ai
        self.open_visual = open_visual
        self.analyze_screen = analyze_screen
        self.close_window = close_window
        self.message_app = message_app
        self.pending: tuple[str, str] | None = None

    def handle(self, raw_command: str) -> None:
        command = self._correct_common_typos(raw_command.lower().strip().strip("?!.,"))

        if self.pending:
            if self._starts_new_request(command):
                self.pending = None
            elif self._handle_pending(command):
                return

        if command in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
            self.speak("Hi! How can I help you?")
            return

        if command in {"can you see my screen", "do you see my screen", "are you seeing my screen"}:
            self.speak("I do not continuously watch your screen. I only capture it after an explicit command like point to something.")
            return

        if self._is_screen_analysis_request(command):
            if self.analyze_screen:
                self.analyze_screen(raw_command)
            else:
                self.speak("Screen analysis is available only in the desktop app, not the debug console.")
            return

        message_pattern = (
            r"open\s+(?:the\s+)?(?:chat\s*gpt)(?:\s+(?:desktop\s+)?app)?\s+and\s+"
            r"(?:send|type)\s+(?:it\s+)?(?:a\s+)?message(?:\s+(?:saying|that says))?\s+(.+)"
        )
        message_match = re.fullmatch(message_pattern, command, flags=re.IGNORECASE)
        if message_match:
            raw_match = re.fullmatch(message_pattern, raw_command.strip().strip("?!.,"), flags=re.IGNORECASE)
            message = (raw_match or message_match).group(1).strip()
            if not self.message_app:
                self.speak("Typing into ChatGPT is available only in the desktop app.")
                return
            self.pending = ("confirm_message_app", f"chatgpt|{message}")
            self.speak(f'I will open ChatGPT, focus its message box, type "{message}", and press Enter. Should I continue?')
            return

        if re.fullmatch(r"close\s+(?:this|the|current|active)\s+window(?:\s+now)?", command):
            if not self.close_window:
                self.speak("Closing the active window is available only in the desktop app.")
                return
            self.pending = ("confirm_close_window", "active")
            self.speak("I will close the currently active window. Should I continue?")
            return

        point_match = re.fullmatch(r"(?:point (?:to|at)|show me|highlight|where is)\s+(.+)", command)
        if point_match:
            target = re.sub(r"\s+(?:on|from)\s+(?:(?:my|the)\s+)?screen$", "", point_match.group(1)).strip()
            if self.point_to:
                self.point_to(target)
            else:
                self.speak("I cannot display a screen highlight in this debug console. Close it and start Samuel with start_samuel.bat on Windows or start_samuel.command on macOS.")
            return

        visual_open_match = re.fullmatch(
            r"(?:open|double[ -]?click|launch)\s+(?:the\s+)?(.+?)(?:\s+(?:on|from)\s+(?:(?:my|the)\s+)?screen)?",
            command,
        )
        if visual_open_match and (
            re.search(r"\b(?:on|from)\s+(?:(?:my|the)\s+)?screen$", command)
            or command.startswith(("double click ", "double-click "))
        ):
            target = self._clean_visual_target(visual_open_match.group(1))
            if not self.open_visual:
                self.speak("Opening a visible screen item is only available in the desktop app, not the debug console.")
                return
            self.pending = ("confirm_visual_open", target)
            self.speak(f"I will locate {target} on your screen and double-click it. Should I continue?")
            return

        open_match = re.fullmatch(r"(?:(?:please|okay|ok)\s+)?(?:open|launch|start|go to)\s+(.+)", command)
        if open_match:
            self._open(open_match.group(1).strip())
            return

        search_match = re.fullmatch(r"(?:search (?:google )?for|google)\s+(.+)", command)
        if search_match:
            self._search(search_match.group(1))
            return

        if command in {"what can you do", "help", "show commands"}:
            self.speak("I can discover and open installed apps, open websites, control visible screen items, and search Google.")
            print("Examples: open Chrome | go to Facebook | search Google for Python tutorials")
            return

        if re.search(r"\b(text|message|call)\b", command):
            self.speak("Messaging and calling are not enabled yet. We will add contacts and confirmation first.")
            return

        if self.brain and self.brain.enabled:
            try:
                proposal = self.brain.plan(raw_command)
                if proposal:
                    self._propose_ai_action(proposal)
                    return
            except Exception as exc:
                print(f"AI planning error: {exc}")
                self.speak("My AI brain could not connect, so I did not perform anything.")
                return

        if self.need_ai:
            self.speak("That request needs my AI brain, but no OpenAI API key is connected.")
            self.need_ai()
            return
        self.speak("I did not understand that. Add an OpenAI API key to use flexible AI commands.")

    @staticmethod
    def _correct_common_typos(command: str) -> str:
        replacements = {
            "scrren": "screen", "sreen": "screen", "scren": "screen",
            "capturm": "capture", "captur": "capture", "ehat": "what",
            "edxplaine": "explain", "explaine": "explain", "analyse": "analyze", "ia": "i",
        }
        command = re.sub(r"\bscr+e*n\b", "screen", command)
        command = " ".join(replacements.get(word, word) for word in command.split())
        words = command.split()
        if not words:
            return command
        polite = get_close_matches(words[0], ["please"], n=1, cutoff=0.72)
        if polite:
            words[0] = "please"
        verbs = ["open", "launch", "start", "google", "search", "highlight"]
        offset = 1 if words[0] in {"please", "pls"} else 0
        if offset < len(words):
            match = get_close_matches(words[offset], verbs, n=1, cutoff=0.72)
            if match:
                words[offset] = match[0]
        corrected = " ".join(words)
        open_match = re.fullmatch(r"(?:(?:please|okay|ok)\s+)?(?:open|launch|start|go to)\s+(.+)", corrected)
        if open_match:
            target = open_match.group(1).strip()
            known = sorted(set(WEBSITES) | set(WINDOWS_APPS) | set(MAC_APPS) | set(APP_ALIASES))
            close = get_close_matches(target, known, n=1, cutoff=0.72)
            if close:
                corrected = corrected[: corrected.rfind(target)] + close[0]
        return corrected

    def _propose_ai_action(self, proposal: ProposedAction) -> None:
        if proposal.action in {"reply", "clarify"}:
            blocked_labels = {"local conversation", "recent local conversation", "user command", "context"}
            reply = proposal.target.strip()
            if not reply or reply.lower() in blocked_labels:
                self.speak("I understood that as a conversation request, but the AI returned an invalid reply. Please try again.")
                return
            self.speak(reply)
            return
        if proposal.action == "point" and not self.point_to:
            self.speak("I cannot display a screen highlight in this debug console. Close it and start Samuel with start_samuel.bat on Windows or start_samuel.command on macOS.")
            return
        payload = f"{proposal.action}|{proposal.target}"
        self.pending = ("confirm_ai_action", payload)
        self.speak(f"I understand. {proposal.explanation} Should I continue?")

    def _open(self, target: str) -> None:
        target = re.sub(r"\b(?:the|my)\b", "", target.lower()).strip()
        explicit_app = bool(re.search(r"\b(?:desktop\s+)?(?:app|application)$", target))
        target = re.sub(r"\s+(?:desktop\s+)?(?:app|application)$", "", target).strip()
        target = APP_ALIASES.get(target, target)
        if target in WEBSITES:
            if explicit_app:
                self._open_windows_app(target)
                return
            if target in {"facebook", "whatsapp", "instagram", "chatgpt"}:
                self.pending = ("app_or_website", target)
                self.speak(f"Should I open the {target} app or website?")
                return
            self._open_website(target)
            return

        if target == "chrome" or target in WINDOWS_APPS:
            self._open_windows_app(target)
            return

        if target.startswith(("http://", "https://")):
            webbrowser.open(target)
            self.speak("Opening the website.")
            return

        installed = find_installed_app(target)
        if installed:
            try:
                launch_installed_app(installed)
                self.speak(f"Opening {installed.name}.")
            except OSError:
                self.speak(f"I found {installed.name}, but the operating system could not open it.")
            return

        self.speak(f"I could not find an installed app named {target}. Should I search Google for it?")
        self.pending = ("confirm_search", target)

    def _open_windows_app(self, name: str) -> None:
        if platform.system() == "Darwin":
            app_name = MAC_APPS.get(name, name)
            try:
                subprocess.Popen(["open", "-a", app_name], shell=False)
                self.speak(f"Opening {app_name}.")
            except OSError:
                self.speak(f"I could not find {app_name} on this Mac.")
            return
        command = self._find_chrome() if name == "chrome" else WINDOWS_APPS.get(name, name)
        try:
            if command is None:
                raise FileNotFoundError(name)
            if command.endswith(":"):
                os.startfile(command)  # type: ignore[attr-defined]
            else:
                subprocess.Popen([command], shell=False)
            self.speak(f"Opening {name}.")
        except (FileNotFoundError, OSError):
            self.speak(f"I could not find the {name} app. Should I open it as a website instead?")
            if name in WEBSITES:
                self.pending = ("confirm_website", name)
            elif name == "chrome":
                self.pending = ("confirm_url", "https://www.google.com")

    def _handle_pending(self, command: str) -> bool:
        kind, value = self.pending
        clean = re.sub(r"\b(?:please|it|the)\b", "", command).strip(" ,.-")

        if self._is_no(command):
            self.pending = None
            self.speak("Cancelled.")
            return True

        if kind == "app_or_website":
            if "website" in command:
                self.pending = None
                self._open_website(value)
                return True
            if "app" in command:
                self.pending = None
                self._open_windows_app(value)
                return True
            self.speak("Please say app or website.")
            return True

        if self._is_yes(command) or self._is_yes(clean):
            self.pending = None
            if kind == "confirm_search":
                self._search(value)
            elif kind == "confirm_website":
                self._open_website(value)
            elif kind == "confirm_url":
                webbrowser.open(value)
                self.speak("Opening it in your default browser.")
            elif kind == "confirm_ai_action":
                action, target = value.split("|", 1)
                if action == "open":
                    self._open(target)
                elif action == "search":
                    self._search(target)
                elif action == "point":
                    if self.point_to:
                        self.point_to(target)
                    else:
                        self.speak("I cannot display a screen highlight in this debug console. Close it and start Samuel with start_samuel.bat on Windows or start_samuel.command on macOS.")
            elif kind == "confirm_visual_open":
                if self.open_visual:
                    self.open_visual(value)
                else:
                    self.speak("Opening a visible screen item is only available in the desktop app.")
            elif kind == "confirm_close_window":
                if self.close_window:
                    self.close_window()
                else:
                    self.speak("Closing the active window is available only in the desktop app.")
            elif kind == "confirm_message_app":
                app, message = value.split("|", 1)
                if self.message_app:
                    self.message_app(app, message)
                else:
                    self.speak("Typing into an app is available only in the desktop app.")
            return True

        self.speak("Please say yes or no.")
        return True

    @staticmethod
    def _is_yes(command: str) -> bool:
        command = command.strip(" ,.-")
        return command in YES_WORDS or bool(re.fullmatch(
            r"(?:yes|yeah|yep|okay|ok|sure)(?:\s+(?:please|continue|proceed|do it|do it now|go ahead|open it|now))*",
            command,
        ))

    @staticmethod
    def _is_no(command: str) -> bool:
        command = command.strip(" ,.-")
        return command in NO_WORDS or bool(re.fullmatch(r"(?:no|nope)(?:\s+thanks)?", command))

    @staticmethod
    def _clean_visual_target(target: str) -> str:
        return re.sub(r"\s+", " ", target).strip()

    @staticmethod
    def _starts_new_request(command: str) -> bool:
        if command in YES_WORDS or command in NO_WORDS or command in {"app", "website"}:
            return False
        return bool(re.match(
            r"^(?:please\s+|okay\s+|ok\s+)?(?:open|launch|start|go to|point|show|highlight|"
            r"search|google|analyze|check|capture|describe|close|double[ -]?click|what am i doing)\b",
            command,
        ))

    @staticmethod
    def _is_screen_analysis_request(command: str) -> bool:
        patterns = (
            r"^(?:analyze|analysis|describe|check)\s+(?:my\s+|the\s+)?screen(?:\s+yourself)?$",
            r"^capture(?:\s+(?:my|the))?\s+screen\s+and\s+(?:tell|explain).*(?:see|doing)$",
            r"^capture\s+and\s+(?:tell|explain)\s+me\s+what\s+you\s+see$",
            r"^what\s+(?:am\s+i|i\s+am)\s+doing(?:\s+explain\s+it)?$",
        )
        return any(re.search(pattern, command) for pattern in patterns)

    def _open_website(self, name: str) -> None:
        webbrowser.open(WEBSITES[name])
        self.speak(f"Opening {name} website.")

    @staticmethod
    def _find_chrome() -> str | None:
        located = shutil.which("chrome") or shutil.which("chrome.exe")
        if located:
            return located
        candidates = [
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        return next((path for path in candidates if path and os.path.isfile(path)), None)

    def _search(self, query: str) -> None:
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
        self.speak(f"Searching Google for {query}.")
