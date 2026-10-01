"""
Unit tests for Window Manager (Phase 9).
Verifies window filtering, title matching, and structured focus actions.
"""

import unittest
from unittest.mock import MagicMock
from core.window_manager import WindowManager


class TestWindowManager(unittest.TestCase):
    def setUp(self):
        self.mock_controller = MagicMock()
        self.mock_controller.normalize_app_name.side_effect = lambda n: "Visual Studio Code" if "code" in n.lower() else n
        self.window_mgr = WindowManager(controller=self.mock_controller)

    def test_focus_window_with_title_match(self):
        # Mock list_windows
        self.window_mgr.list_windows = MagicMock(return_value=[
            {"app": "Visual Studio Code", "title": "FLOW — main.py", "index": 1},
            {"app": "Visual Studio Code", "title": "MARK XLVIII — orchestrator.py", "index": 2},
        ])

        res = self.window_mgr.focus_window("VS Code", title_query="FLOW")
        self.assertTrue(res["success"])
        self.assertEqual(res["window"], "FLOW — main.py")
        self.mock_controller.focus_application.assert_called_once_with("Visual Studio Code")


if __name__ == "__main__":
    unittest.main()
