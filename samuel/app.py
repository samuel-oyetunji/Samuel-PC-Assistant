from __future__ import annotations

import os
import sys

from .commands import CommandHandler
from .brain import AIBrain
from .speech import SpeechEngine


class SamuelAssistant:
    def __init__(self) -> None:
        brain = AIBrain()
        self.speech = SpeechEngine(transcriber=brain.transcribe_audio)
        self.commands = CommandHandler(self.speech.speak, brain=brain)

    def run(self) -> None:
        print("\nSAMUEL PC ASSISTANT v0.3")
        print("Say 'Hey' or type a command.")
        print("Type /voice for microphone mode, /text for keyboard mode, /quit to exit.\n")
        self.speech.speak("Samuel is online.")

        mode = os.getenv("SAMUEL_INPUT_MODE", "text").lower()
        while True:
            try:
                if mode == "voice":
                    command = self.speech.listen()
                    if command:
                        print(f"You: {command}")
                else:
                    command = input("You: ").strip()

                if not command:
                    continue
                lowered = command.lower()
                if lowered == "/voice":
                    mode = "voice"
                    self.speech.speak("Microphone mode enabled.")
                    continue
                if lowered == "/text":
                    mode = "text"
                    self.speech.speak("Keyboard mode enabled.")
                    continue
                if lowered in {"/quit", "quit", "exit", "goodbye samuel"}:
                    self.speech.speak("Goodbye, Samuel.")
                    return

                command = self._remove_wake_phrase(command)
                if command:
                    self.commands.handle(command)
            except (KeyboardInterrupt, EOFError):
                print()
                self.speech.close()
                return
            except Exception as exc:
                print(f"Error: {exc}", file=sys.stderr)
                self.speech.speak("Something went wrong. Check the error shown on screen.")

    @staticmethod
    def _remove_wake_phrase(command: str) -> str:
        lowered = command.lower().strip()
        for phrase in ("hey",):
            if lowered.startswith(phrase):
                return command[len(phrase):].lstrip(" ,.-")
        return command
