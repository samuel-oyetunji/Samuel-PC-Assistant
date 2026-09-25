import unittest

from samuel.orb import ORB_STYLES, orb_style


class OrbTests(unittest.TestCase):
    def test_every_voice_state_has_a_visual_style(self):
        for state in ("off", "calibrating", "ready", "listening", "recognizing", "thinking", "speaking", "error"):
            self.assertIn(state, ORB_STYLES)
            self.assertEqual(len(orb_style(state)), 3)

    def test_unknown_state_falls_back_to_ready(self):
        self.assertEqual(orb_style("unknown"), ORB_STYLES["ready"])


if __name__ == "__main__":
    unittest.main()
