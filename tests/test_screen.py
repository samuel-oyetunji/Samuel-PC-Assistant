import unittest
from unittest.mock import Mock, patch
from types import ModuleType
import sys

from samuel import screen
from samuel.screen import ScreenTarget


class ScreenActionTests(unittest.TestCase):
    def test_send_keys_metacharacters_are_escaped(self):
        self.assertEqual(screen.re_escape_send_keys("50% + yes"), "50{%} {+} yes")

    def test_windows_close_uses_alt_f4(self):
        send_keys = Mock()
        package = ModuleType("pywinauto")
        keyboard = ModuleType("pywinauto.keyboard")
        keyboard.send_keys = send_keys
        with patch.object(screen.platform, "system", return_value="Windows"), \
             patch.dict(sys.modules, {"pywinauto": package, "pywinauto.keyboard": keyboard}):
            screen.close_active_window()
        send_keys.assert_called_once_with("%{F4}")

    def test_windows_double_click_uses_target_center(self):
        user32 = Mock()
        user32.SetCursorPos.return_value = 1
        fake_windll = Mock(user32=user32)
        target = ScreenTarget("Kali folder", 100, 200, 140, 260)
        with patch.object(screen.platform, "system", return_value="Windows"), \
             patch.object(screen.ctypes, "windll", fake_windll, create=True), \
             patch.object(screen.time, "sleep"):
            screen.double_click_target(target)
        user32.SetCursorPos.assert_called_once_with(120, 230)
        self.assertEqual(user32.mouse_event.call_count, 4)

    def test_unsupported_os_refuses_to_click(self):
        with patch.object(screen.platform, "system", return_value="Linux"):
            with self.assertRaises(OSError):
                screen.double_click_target(ScreenTarget("item", 0, 0, 10, 10))


if __name__ == "__main__":
    unittest.main()
