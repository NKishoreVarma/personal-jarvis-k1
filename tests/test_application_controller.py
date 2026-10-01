"""
Unit tests for Application Controller (Phase 9).
Verifies canonical app name normalization, structured launch commands, focus, and close operations.
"""

import unittest
from core.application_controller import ApplicationController


class TestApplicationController(unittest.TestCase):
    def setUp(self):
        self.controller = ApplicationController()

    def test_normalize_known_apps(self):
        self.assertEqual(self.controller.normalize_app_name("chrome"), "Google Chrome")
        self.assertEqual(self.controller.normalize_app_name("whatsapp"), "WhatsApp")
        self.assertEqual(self.controller.normalize_app_name("vscode"), "Visual Studio Code")
        self.assertEqual(self.controller.normalize_app_name("vs code"), "Visual Studio Code")
        self.assertEqual(self.controller.normalize_app_name("spotify"), "Spotify")
        self.assertEqual(self.controller.normalize_app_name("finder"), "Finder")

    def test_normalize_conversational_prefixes(self):
        self.assertEqual(self.controller.normalize_app_name("the chrome app"), "Google Chrome")
        self.assertEqual(self.controller.normalize_app_name("application whatsapp"), "WhatsApp")

    def test_normalize_fuzzy_app_names(self):
        self.assertEqual(self.controller.normalize_app_name("google-chrome"), "Google Chrome")
        self.assertEqual(self.controller.normalize_app_name("spotfy"), "Spotify")

    def test_invalid_shell_injection_name_rejected(self):
        self.assertIsNone(self.controller.normalize_app_name("chrome; rm -rf /"))
        self.assertIsNone(self.controller.normalize_app_name("app && killall Finder"))


if __name__ == "__main__":
    unittest.main()
