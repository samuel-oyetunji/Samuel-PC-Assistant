import unittest

from samuel.settings import Settings
from samuel.platform_support import crash_log_path


class SettingsTests(unittest.TestCase):
    def test_safe_defaults(self):
        settings = Settings()
        self.assertEqual(settings.assistant_name, "Samuel")
        self.assertEqual(settings.wake_phrase, "hey")
        self.assertTrue(settings.confirm_ai_actions)

    def test_crash_log_has_a_filename(self):
        self.assertEqual(crash_log_path().name, "samuel-crash.log")


if __name__ == "__main__":
    unittest.main()
