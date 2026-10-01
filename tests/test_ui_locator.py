"""
Unit tests for UI Locator (Phase 9).
Verifies multi-stage UI element discovery: exact match, label substring, fuzzy matching, and ambiguity handling.
"""

import unittest
from unittest.mock import MagicMock
from core.ui_locator import UILocator


class TestUILocator(unittest.TestCase):
    def setUp(self):
        self.mock_observer = MagicMock()
        self.mock_controller = MagicMock()
        self.mock_controller.normalize_app_name.side_effect = lambda n: n
        self.locator = UILocator(observer=self.mock_observer, controller=self.mock_controller)

    def test_locate_exact_match(self):
        self.mock_observer.get_ui_elements.return_value = [
            {"role": "AXButton", "title": "New Chat", "label": "New Chat", "enabled": True},
            {"role": "AXStaticText", "title": "John Doe", "label": "John Doe", "enabled": True},
        ]

        res = self.locator.locate_element("WhatsApp", "New Chat")
        self.assertTrue(res["found"])
        self.assertEqual(res["strategy"], "accessibility_exact")
        self.assertEqual(res["confidence"], 1.0)

    def test_locate_substring_match(self):
        self.mock_observer.get_ui_elements.return_value = [
            {"role": "AXStaticText", "title": "John Doe (Online)", "label": "John Doe (Online)", "enabled": True},
        ]

        res = self.locator.locate_element("WhatsApp", "John Doe")
        self.assertTrue(res["found"])
        self.assertEqual(res["strategy"], "accessibility_substring")

    def test_locate_ambiguous_matches(self):
        self.mock_observer.get_ui_elements.return_value = [
            {"role": "AXStaticText", "title": "John Smith", "label": "John Smith", "enabled": True},
            {"role": "AXStaticText", "title": "John Doe", "label": "John Doe", "enabled": True},
        ]

        res = self.locator.locate_element("WhatsApp", "John")
        self.assertFalse(res["found"])
        self.assertTrue(res["ambiguous"])
        self.assertEqual(len(res["candidates"]), 2)


if __name__ == "__main__":
    unittest.main()
