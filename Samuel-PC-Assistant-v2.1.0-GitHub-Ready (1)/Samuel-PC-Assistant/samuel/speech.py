from __future__ import annotations

import platform
import queue
import re
import subprocess
import threading
import time
import wave
from difflib import SequenceMatcher
from io import BytesIO
from collections.abc import Callable


def extract_wake_command(transcript: str, wake_phrase: str, assistant_name: str) -> tuple[bool, str]:
    lowered = transcript.lower().strip()
    options = [wake_phrase.lower().strip()]
    for phrase in options:
        if lowered == phrase:
            return True, ""
        if lowered.startswith(phrase) and lowered[len(phrase):len(phrase) + 1] in {" ", ",", ".", "-", ":"}:
            return True, transcript.strip()[len(phrase):].lstrip(" ,.-:")
    # Speech recognizers commonly return "Sam" or "Samual" for Samuel. Accept a
    # close match only at the start, optionally after hey/okay/ok, to avoid waking
    # on an unrelated word later in a conversation.
    if assistant_name.lower().strip() not in wake_phrase.lower().split():
        return False, transcript.strip()
    matches = list(re.finditer(r"[A-Za-z0-9']+", transcript))
    if not matches:
        return False, transcript.strip()
    words = [match.group(0).lower() for match in matches]
    name = assistant_name.lower().strip()
    name_index = 1 if words[0] in {"hey", "okay", "ok"} and len(words) > 1 else 0
    heard_name = words[name_index]
    if heard_name.startswith(name) and heard_name != name:
        return False, transcript.strip()
    close_name = (
        heard_name == name
        or (len(name) >= 5 and heard_name == name[:3])
        or (len(heard_name) >= 4 and SequenceMatcher(None, heard_name, name).ratio() >= 0.72)
    )
    if close_name:
        end = matches[name_index].end()
        return True, transcript[end:].lstrip(" ,.-:")
    return False, transcript.strip()


class SpeechEngine:
    """Low-latency microphone input and serialized, non-blocking speech output."""

    def __init__(self, state_callback: Callable[[str], None] | None = None,
                 transcriber: Callable[[bytes], str | None] | None = None) -> None:
        self._speech_queue: queue.Queue[str | None] = queue.Queue()
        self._speech_pending = threading.Event()
        self._closed = threading.Event()
        self.output_status = "starting"
        self._state_callback = state_callback
        self._transcriber = transcriber
        self.transcription_status = "Google fallback"
        self._noise_floor: float | None = None
        self._worker = threading.Thread(target=self._speech_worker, name="samuel-voice", daemon=True)
        self._worker.start()

    def speak(self, text: str) -> None:
        print(f"Samuel: {text}")
        if self._closed.is_set():
            return
        self._speech_pending.set()
        self._speech_queue.put(text)

    def _speech_worker(self) -> None:
        engine = None
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 185)
            engine.setProperty("volume", 1.0)
            voices = engine.getProperty("voices") or []
            preferred = next((voice for voice in voices if self._is_english_voice(voice)), None)
            if preferred:
                engine.setProperty("voice", preferred.id)
            self.output_status = "ready"
        except Exception as exc:
            print(f"Primary text-to-speech unavailable: {exc}")
            self.output_status = "system fallback"

        while not self._closed.is_set():
            text = self._speech_queue.get()
            if text is None:
                break
            try:
                self._emit_state("speaking")
                if engine is not None:
                    engine.say(text)
                    engine.runAndWait()
                else:
                    self._system_speak(text)
            except Exception as exc:
                print(f"Voice output error: {exc}")
                if engine is not None:
                    try:
                        engine = None
                        self._system_speak(text)
                        self.output_status = "system fallback"
                    except Exception as fallback_exc:
                        print(f"System voice fallback error: {fallback_exc}")
                        self.output_status = "failed"
                else:
                    self.output_status = "failed"
            finally:
                self._speech_queue.task_done()
                if self._speech_queue.empty():
                    self._speech_pending.clear()
                    self._emit_state("idle")

    @staticmethod
    def _is_english_voice(voice: object) -> bool:
        details = " ".join([
            str(getattr(voice, "name", "")), str(getattr(voice, "id", "")),
            " ".join(str(item) for item in getattr(voice, "languages", []) or []),
        ]).lower()
        return any(marker in details for marker in ("english", "en-", "en_", "zira", "david", "samantha"))

    @staticmethod
    def _system_speak(text: str) -> None:
        if platform.system() == "Windows":
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$voice.Rate = 1; $voice.Volume = 100; $voice.Speak($args[0])"
            )
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script, text],
                capture_output=True, text=True, timeout=45, check=False,
            )
        elif platform.system() == "Darwin":
            result = subprocess.run(["say", "-r", "185", text], capture_output=True, text=True, timeout=45, check=False)
        else:
            raise OSError("No system speech engine is available.")
        if result.returncode != 0:
            raise OSError(result.stderr.strip() or "System speech failed.")

    def listen(self) -> str:
        try:
            import numpy as np
            import sounddevice as sd
            import speech_recognition as sr
        except ImportError:
            self.speak("Microphone support is not installed. Run the setup command in the README.")
            return "/text"

        wait_deadline = time.monotonic() + 20
        while self._speech_pending.is_set() and time.monotonic() < wait_deadline:
            time.sleep(0.05)

        recognizer = sr.Recognizer()
        sample_rate = 16000
        try:
            sd.check_input_settings(samplerate=sample_rate, channels=1, dtype="int16")
        except Exception:
            device = sd.query_devices(kind="input")
            sample_rate = int(device["default_samplerate"])
        print("Listening...")
        try:
            raw, self._noise_floor = self._record_phrase(
                sd, np, sample_rate, self._noise_floor, self._emit_state
            )
            if not raw:
                self._emit_state("idle")
                return ""
            self._emit_state("recognizing")
            if self._transcriber is not None:
                try:
                    transcript = self._transcriber(self._to_wav(raw, sample_rate))
                    if transcript:
                        self.transcription_status = "OpenAI enhanced"
                        return transcript.strip()
                except Exception as exc:
                    print(f"Enhanced transcription unavailable; using fallback: {exc}")
            audio = sr.AudioData(raw, sample_rate, 2)
            result = recognizer.recognize_google(audio, language="en-NG", show_all=True)
            self.transcription_status = "Google fallback"
            return self._best_transcript(result)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            self.speak("Speech recognition could not connect. Check your internet connection.")
            return "/text"
        except Exception as exc:
            print(f"Microphone error: {exc}")
            self.speak("I could not access the microphone. Check the operating system permission and selected input device.")
            return "/text"
        finally:
            if not self._speech_pending.is_set():
                self._emit_state("idle")

    @staticmethod
    def _record_phrase(sd: object, np: object, sample_rate: int, noise_floor: float | None = None,
                       state_callback: Callable[[str], None] | None = None) -> tuple[bytes, float]:
        """Record until speech ends instead of waiting a fixed seven seconds."""
        chunk_size = int(sample_rate * 0.10)
        calibration_chunks = 6 if noise_floor is None else 0
        start_timeout_chunks = 60
        silence_to_stop_chunks = 9
        maximum_phrase_chunks = 150
        pre_roll: list[object] = []
        phrase: list[object] = []
        noise_levels: list[float] = []
        started = False
        silent_chunks = 0

        if state_callback:
            state_callback("calibrating" if calibration_chunks else "ready")
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16", blocksize=chunk_size) as stream:
            for index in range(calibration_chunks + start_timeout_chunks + maximum_phrase_chunks):
                chunk, overflowed = stream.read(chunk_size)
                if overflowed:
                    print("Microphone input overflow; continuing.")
                mono = np.asarray(chunk, dtype=np.int16).reshape(-1)
                rms = float(np.sqrt(np.mean(mono.astype(np.float64) ** 2))) if mono.size else 0.0
                if index < calibration_chunks:
                    noise_levels.append(rms)
                    pre_roll.append(mono.copy())
                    if index == calibration_chunks - 1:
                        noise_floor = float(np.median(noise_levels)) if noise_levels else 0.0
                        if state_callback:
                            state_callback("ready")
                    continue
                active_noise_floor = noise_floor if noise_floor is not None else 0.0
                start_threshold = max(80.0, active_noise_floor * 1.65)
                continue_threshold = max(55.0, active_noise_floor * 1.28)
                voiced = rms >= (continue_threshold if started else start_threshold)
                if not started:
                    if rms < start_threshold:
                        active_noise_floor = active_noise_floor * 0.97 + rms * 0.03
                        noise_floor = active_noise_floor
                    pre_roll.append(mono.copy())
                    pre_roll = pre_roll[-15:]
                    if voiced:
                        started = True
                        phrase.extend(pre_roll)
                        if state_callback:
                            state_callback("listening")
                    elif index >= calibration_chunks + start_timeout_chunks:
                        return b"", active_noise_floor
                    continue
                phrase.append(mono.copy())
                silent_chunks = 0 if voiced else silent_chunks + 1
                if silent_chunks >= silence_to_stop_chunks or len(phrase) >= maximum_phrase_chunks:
                    break
        if not phrase:
            return b"", noise_floor or 0.0
        return np.concatenate(phrase).astype(np.int16).tobytes(), noise_floor or 0.0

    @staticmethod
    def _to_wav(raw: bytes, sample_rate: int) -> bytes:
        output = BytesIO()
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(raw)
        return output.getvalue()

    @staticmethod
    def _best_transcript(result: object) -> str:
        if isinstance(result, str):
            return result.strip()
        if not isinstance(result, dict):
            return ""
        alternatives = result.get("alternative", [])
        if not isinstance(alternatives, list):
            return ""
        candidates = [item for item in alternatives if isinstance(item, dict) and item.get("transcript")]
        if not candidates:
            return ""
        best_confidence = max(float(item.get("confidence", 0)) for item in candidates)
        plausible = [item for item in candidates if float(item.get("confidence", 0)) >= best_confidence - 0.12]
        return str(max(plausible, key=lambda item: len(str(item.get("transcript", ""))))["transcript"]).strip()

    def _emit_state(self, state: str) -> None:
        if self._state_callback:
            try:
                self._state_callback(state)
            except Exception:
                pass

    def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        self._speech_queue.put(None)
