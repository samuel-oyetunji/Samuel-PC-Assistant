from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
import uuid

from .secure_store import load_secret, save_secret
from dataclasses import dataclass


@dataclass
class ProposedAction:
    action: str
    target: str
    explanation: str


class AIBrain:
    """Natural-language planner. It proposes actions but never executes them."""

    ALLOWED_ACTIONS = {"open", "search", "point", "reply", "clarify"}

    def __init__(self, model: str | None = None) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") or self._saved_key()
        self.enabled = bool(self.api_key)
        self.model = model or os.getenv("SAMUEL_OPENAI_MODEL", "gpt-5.6")
        self.history: list[str] = []

    def plan(self, command: str) -> ProposedAction | None:
        if not self.enabled:
            return None
        recent = "\n".join(self.history[-6:])
        payload = {
            "model": self.model,
            "store": False,
            "instructions": (
                "You are the planning brain for a desktop assistant named Samuel. "
                "The host desktop app executes approved actions; your job is to propose exactly one safe action using the tool. "
                "Never claim an action happened merely because you proposed it. "
                "Use clarify when important information is missing. Never propose shell commands, "
                "password entry, deletion, purchases, financial activity, or bypassing security. "
                "For reply or clarify, target MUST be the complete natural-language sentence to speak. "
                "Never copy prompt labels such as local conversation, context, or user command into target."
            ),
            "input": f"CONTEXT (may be empty):\n{recent}\n\nACTUAL USER REQUEST:\n{command}",
            "tools": [{
                "type": "function",
                "name": "propose_action",
                "description": "Propose one allow-listed action for the local app to validate.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": sorted(self.ALLOWED_ACTIONS)},
                        "target": {"type": "string"},
                        "explanation": {"type": "string"},
                    },
                    "required": ["action", "target", "explanation"],
                    "additionalProperties": False,
                },
                "strict": True,
            }],
            "tool_choice": {"type": "function", "name": "propose_action"},
        }
        response = self._post_responses(payload)

        for item in response.get("output", []):
            if item.get("type") == "function_call" and item.get("name") == "propose_action":
                data = json.loads(item.get("arguments", "{}"))
                action = data.get("action", "")
                if action not in self.ALLOWED_ACTIONS:
                    return None
                proposal = ProposedAction(action, data.get("target", ""), data.get("explanation", ""))
                self.history.extend([f"User: {command}", f"Plan: {action} {proposal.target}"])
                return proposal
        return None

    @staticmethod
    def _saved_key() -> str | None:
        try:
            return load_secret()
        except Exception:
            return None

    def save_key(self, api_key: str) -> None:
        cleaned = api_key.strip()
        if not cleaned.startswith("sk-"):
            raise ValueError("That does not look like an OpenAI API key.")
        save_secret(cleaned)
        self.api_key = cleaned
        self.enabled = True

    def transcribe_audio(self, wav_bytes: bytes) -> str | None:
        """Transcribe one microphone turn; callers may safely fall back locally."""
        if not self.enabled or not self.api_key:
            return None
        boundary = f"samuel-{uuid.uuid4().hex}"
        fields = {
            "model": "gpt-4o-mini-transcribe",
            "language": "en",
            "response_format": "json",
            "prompt": "The wake word is Hey. Preserve the entire spoken request, including the opening Hey and all app names.",
        }
        parts: list[bytes] = []
        for name, value in fields.items():
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
            )
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="speech.wav"\r\n'
            'Content-Type: audio/wav\r\n\r\n'.encode() + wav_bytes + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        request = urllib.request.Request(
            "https://api.openai.com/v1/audio/transcriptions",
            data=b"".join(parts),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as result:
                return str(json.loads(result.read().decode("utf-8")).get("text", "")).strip() or None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI transcription returned HTTP {exc.code}: {detail[:200]}") from exc

    def locate_visual(self, image_bytes: bytes, target: str, width: int, height: int) -> dict | None:
        if not self.enabled:
            return None
        payload = {
            "model": self.model,
            "store": False,
            "instructions": "Locate the requested visible object. Return a tight bounding box in screenshot pixels. Never invent a location.",
            "input": [{"role": "user", "content": [
                {"type": "input_text", "text": f"Find: {target}. Screenshot size: {width}x{height}."},
                {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii"), "detail": "high"},
            ]}],
            "tools": [{
                "type": "function", "name": "report_location",
                "description": "Report whether the object was found and its bounding box.",
                "parameters": {"type": "object", "properties": {
                    "found": {"type": "boolean"}, "label": {"type": "string"},
                    "x": {"type": "integer", "minimum": 0}, "y": {"type": "integer", "minimum": 0},
                    "width": {"type": "integer", "minimum": 0}, "height": {"type": "integer", "minimum": 0},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                }, "required": ["found", "label", "x", "y", "width", "height", "confidence"], "additionalProperties": False},
                "strict": True,
            }],
            "tool_choice": {"type": "function", "name": "report_location"},
        }
        response = self._post_responses(payload)
        for item in response.get("output", []):
            if item.get("type") == "function_call" and item.get("name") == "report_location":
                data = json.loads(item.get("arguments", "{}"))
                if not data.get("found") or float(data.get("confidence", 0)) < 0.35:
                    return None
                x = max(0, min(width - 1, int(data.get("x", 0))))
                y = max(0, min(height - 1, int(data.get("y", 0))))
                box_width = max(0, min(width - x, int(data.get("width", 0))))
                box_height = max(0, min(height - y, int(data.get("height", 0))))
                if box_width == 0 or box_height == 0:
                    return None
                data.update({"x": x, "y": y, "width": box_width, "height": box_height})
                return data
        return None

    def describe_screen(self, image_bytes: bytes, request: str, width: int, height: int) -> str | None:
        """Describe an explicitly captured screen without requesting an upload from the user."""
        if not self.enabled:
            return None
        payload = {
            "model": self.model,
            "store": False,
            "instructions": (
                "You are viewing a screenshot explicitly captured by the user's desktop assistant. "
                "Describe what is visibly happening and answer the user's request directly. "
                "Do not ask the user to upload or share the screen. Do not infer passwords, hidden content, or identity."
            ),
            "input": [{"role": "user", "content": [
                {"type": "input_text", "text": f"Request: {request}. Screenshot size: {width}x{height}."},
                {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii"), "detail": "high"},
            ]}],
            "tools": [{
                "type": "function", "name": "report_screen_summary",
                "description": "Return a concise, useful description of the visible screen.",
                "parameters": {
                    "type": "object",
                    "properties": {"summary": {"type": "string"}},
                    "required": ["summary"], "additionalProperties": False,
                },
                "strict": True,
            }],
            "tool_choice": {"type": "function", "name": "report_screen_summary"},
        }
        response = self._post_responses(payload)
        for item in response.get("output", []):
            if item.get("type") == "function_call" and item.get("name") == "report_screen_summary":
                summary = str(json.loads(item.get("arguments", "{}")).get("summary", "")).strip()
                return summary or None
        return None

    def _post_responses(self, payload: dict) -> dict:
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses", data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as result:
                return json.loads(result.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API returned HTTP {exc.code}: {detail[:300]}") from exc
