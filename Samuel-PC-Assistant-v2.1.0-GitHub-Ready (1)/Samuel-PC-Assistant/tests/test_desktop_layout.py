import unittest

from samuel.layout import fitted_geometry


class DesktopLayoutTests(unittest.TestCase):
    def test_large_display_uses_preferred_centered_size(self):
        geometry, minimum_width, minimum_height = fitted_geometry(1920, 1080, 720, 680)
        self.assertEqual(geometry, "720x680+600+200")
        self.assertEqual((minimum_width, minimum_height), (560, 520))

    def test_small_display_fits_inside_safe_margin(self):
        geometry, minimum_width, minimum_height = fitted_geometry(1366, 768, 640, 680)
        self.assertEqual(geometry, "640x680+363+44")
        self.assertLessEqual(minimum_width, 640)
        self.assertLessEqual(minimum_height, 680)


if __name__ == "__main__":
    unittest.main()
