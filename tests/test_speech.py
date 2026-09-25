import unittest

import numpy as np

from samuel.speech import SpeechEngine, extract_wake_command


class FakeStream:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.read_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size):
        self.read_count += 1
        return next(self.chunks), False


class FakeSoundDevice:
    def __init__(self, chunks):
        self.stream = FakeStream(chunks)

    def InputStream(self, **_kwargs):
        return self.stream


class SpeechTests(unittest.TestCase):
    def test_complete_wake_command_is_preserved(self):
        woke, command = extract_wake_command("Hey, how are you?", "hey", "Samuel")
        self.assertTrue(woke)
        self.assertEqual(command, "how are you?")

    def test_bare_hey_wakes_without_assistant_name(self):
        woke, command = extract_wake_command("Hey open Chrome", "hey", "Samuel")
        self.assertTrue(woke)
        self.assertEqual(command, "open Chrome")

    def test_assistant_name_alone_can_wake(self):
        woke, command = extract_wake_command("Samuel open VLC", "hey", "Samuel")
        self.assertFalse(woke)
        self.assertEqual(command, "Samuel open VLC")

    def test_similar_word_does_not_wake(self):
        woke, _command = extract_wake_command("Samuelson is here", "hey samuel", "Samuel")
        self.assertFalse(woke)

    def test_common_wake_name_mishearing_is_accepted(self):
        woke, command = extract_wake_command("Hey Samual how are you", "hey samuel", "Samuel")
        self.assertTrue(woke)
        self.assertEqual(command, "how are you")

    def test_short_name_variant_is_accepted_only_at_start(self):
        woke, command = extract_wake_command("Hey Sam open VLC", "hey samuel", "Samuel")
        self.assertTrue(woke)
        self.assertEqual(command, "open VLC")
        self.assertFalse(extract_wake_command("Tell Sam to open VLC", "hey samuel", "Samuel")[0])

    def test_recording_stops_after_speech_and_silence(self):
        silence = np.zeros(1600, dtype=np.int16)
        voice = np.full(1600, 2000, dtype=np.int16)
        device = FakeSoundDevice([silence] * 6 + [silence] * 2 + [voice] * 3 + [silence] * 9)
        raw, noise_floor = SpeechEngine._record_phrase(device, np, 16000)
        self.assertTrue(raw)
        self.assertEqual(noise_floor, 0)
        self.assertEqual(device.stream.read_count, 20)

    def test_recording_times_out_when_nobody_speaks(self):
        silence = np.zeros(1600, dtype=np.int16)
        device = FakeSoundDevice([silence] * 80)
        raw, _noise_floor = SpeechEngine._record_phrase(device, np, 16000)
        self.assertEqual(raw, b"")
        self.assertLessEqual(device.stream.read_count, 68)

    def test_english_voice_detection(self):
        voice = type("Voice", (), {"name": "Microsoft Zira Desktop", "id": "zira", "languages": ["en-US"]})()
        self.assertTrue(SpeechEngine._is_english_voice(voice))

    def test_complete_transcript_is_selected(self):
        result = {"alternative": [
            {"transcript": "you", "confidence": 0.70},
            {"transcript": "hey Samuel how are you", "confidence": 0.91},
        ]}
        self.assertEqual(SpeechEngine._best_transcript(result), "hey Samuel how are you")

    def test_long_complete_alternative_wins_when_confidence_is_close(self):
        result = {"alternative": [
            {"transcript": "you", "confidence": 0.93},
            {"transcript": "hey Samuel how are you", "confidence": 0.86},
        ]}
        self.assertEqual(SpeechEngine._best_transcript(result), "hey Samuel how are you")

    def test_cached_noise_floor_skips_recalibration(self):
        silence = np.zeros(1600, dtype=np.int16)
        voice = np.full(1600, 1000, dtype=np.int16)
        states = []
        device = FakeSoundDevice([silence] * 2 + [voice] * 2 + [silence] * 9)
        raw, noise_floor = SpeechEngine._record_phrase(device, np, 16000, 40.0, states.append)
        self.assertTrue(raw)
        self.assertLess(noise_floor, 40.0)
        self.assertGreater(noise_floor, 30.0)
        self.assertEqual(states[0], "ready")
        self.assertIn("listening", states)

    def test_pcm_is_wrapped_as_valid_wav(self):
        raw = np.array([1, -1, 200, -200], dtype=np.int16).tobytes()
        wav = SpeechEngine._to_wav(raw, 16000)
        self.assertEqual(wav[:4], b"RIFF")
        self.assertIn(b"WAVE", wav[:16])


if __name__ == "__main__":
    unittest.main()
