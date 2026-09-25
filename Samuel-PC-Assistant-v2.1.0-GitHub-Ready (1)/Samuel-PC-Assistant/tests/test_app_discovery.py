import unittest
from unittest.mock import patch

from samuel import app_discovery
from samuel.app_discovery import InstalledApp, choose_app
from samuel.commands import CommandHandler


class AppDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.apps = [
            InstalledApp("VLC media player", "C:/Start/VLC.lnk", "file"),
            InstalledApp("Visual Studio Code", "C:/Start/VSCode.lnk", "file"),
            InstalledApp("Spotify", "Spotify.App", "store"),
        ]

    def test_short_name_finds_vlc(self):
        self.assertEqual(choose_app("vlc", self.apps).name, "VLC media player")

    def test_typo_finds_spotify(self):
        self.assertEqual(choose_app("spotfy", self.apps).name, "Spotify")

    def test_unrelated_name_is_rejected(self):
        self.assertIsNone(choose_app("definitely not installed", self.apps))

    def test_uninstaller_entries_are_excluded(self):
        cleaned = app_discovery._deduplicate([
            InstalledApp("Uninstall VLC", "C:/VLC/uninstall.exe", "file"),
            InstalledApp("VLC media player", "C:/VLC/vlc.exe", "file"),
        ])
        self.assertEqual([item.name for item in cleaned], ["VLC media player"])

    @patch("samuel.app_discovery.platform.system", return_value="Windows")
    def test_windows_file_launch_uses_resolved_target(self, _system):
        app = InstalledApp("VLC", "C:/Start/VLC.lnk", "file")
        with patch("samuel.app_discovery.os.startfile", create=True) as startfile:
            app_discovery.launch_installed_app(app)
        startfile.assert_called_once_with("C:/Start/VLC.lnk")

    @patch("samuel.app_discovery.subprocess.Popen")
    def test_store_launch_uses_apps_folder_identifier(self, popen):
        app = InstalledApp("Spotify", "SpotifyAB.SpotifyMusic_xyz!Spotify", "store")
        app_discovery.launch_installed_app(app)
        popen.assert_called_once_with(
            ["explorer.exe", r"shell:AppsFolder\SpotifyAB.SpotifyMusic_xyz!Spotify"], shell=False
        )

    @patch("samuel.commands.launch_installed_app")
    @patch("samuel.commands.find_installed_app")
    def test_open_vlc_launches_discovered_app(self, finder, launcher):
        app = self.apps[0]
        finder.return_value = app
        spoken = []
        CommandHandler(spoken.append).handle("ok open vlc")
        finder.assert_called_once_with("vlc")
        launcher.assert_called_once_with(app)
        self.assertEqual(spoken[-1], "Opening VLC media player.")


if __name__ == "__main__":
    unittest.main()
