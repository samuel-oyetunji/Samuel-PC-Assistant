import json
import unittest
from unittest.mock import patch

from samuel.brain import AIBrain


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"text": "Hey open Chrome"}).encode()


class BrainVoiceTests(unittest.TestCase):
    @patch.object(AIBrain, "_saved_key", return_value=None)
    @patch("samuel.brain.urllib.request.urlopen", return_value=FakeResponse())
    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    def test_enhanced_transcription_uses_audio_endpoint(self, mocked_open, _saved_key):
        brain = AIBrain()
        transcript = brain.transcribe_audio(b"RIFF-fake-WAVE")
        self.assertEqual(transcript, "Hey open Chrome")
        request = mocked_open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/audio/transcriptions")
        self.assertIn(b'gpt-4o-mini-transcribe', request.data)
        self.assertIn(b'filename="speech.wav"', request.data)
        self.assertIn(b"RIFF-fake-WAVE", request.data)

    @patch.object(AIBrain, "_saved_key", return_value=None)
    @patch.dict("os.environ", {}, clear=True)
    def test_no_key_skips_paid_transcription(self, _saved_key):
        self.assertIsNone(AIBrain().transcribe_audio(b"RIFF"))


if __name__ == "__main__":
    unittest.main()
