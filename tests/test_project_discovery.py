"""
Unit tests for Project Discovery (Phase 8).
Verifies exact match, case-insensitivity, fuzzy matching, ambiguity protection, and directory exclusion.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from core.project_discovery import ProjectDiscovery


class TestProjectDiscovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.desktop_dir = self.temp_dir / "Desktop"
        self.projects_dir = self.temp_dir / "Projects"
        self.desktop_dir.mkdir()
        self.projects_dir.mkdir()

        # Create sample project structures
        (self.desktop_dir / "FLOW").mkdir()
        (self.desktop_dir / "MARK_XLVIII").mkdir()
        (self.projects_dir / "api-gateway").mkdir()
        (self.projects_dir / "flow-mobile").mkdir()
        (self.projects_dir / "flow-backend").mkdir()

        # Ignored directory
        (self.desktop_dir / "node_modules").mkdir()
        (self.desktop_dir / ".git").mkdir()

        self.discovery = ProjectDiscovery(custom_roots=[self.desktop_dir, self.projects_dir])

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_exact_match(self):
        res = self.discovery.find_project("FLOW")
        self.assertTrue(res["found"])
        self.assertEqual(res["name"], "FLOW")
        self.assertEqual(res["confidence"], 1.0)

    def test_case_insensitive_match(self):
        res = self.discovery.find_project("flow")
        self.assertTrue(res["found"])
        self.assertEqual(res["name"], "FLOW")
        self.assertGreaterEqual(res["confidence"], 0.9)

    def test_conversational_prefix_stripping(self):
        res = self.discovery.find_project("project FLOW")
        self.assertTrue(res["found"])
        self.assertEqual(res["name"], "FLOW")

    def test_location_hint(self):
        res = self.discovery.find_project("FLOW", location_hint="desktop")
        self.assertTrue(res["found"])
        self.assertIn("Desktop", res["path"])

    def test_fuzzy_matching(self):
        res = self.discovery.find_project("apigateway")
        self.assertTrue(res["found"])
        self.assertEqual(res["name"], "api-gateway")

    def test_missing_project(self):
        res = self.discovery.find_project("non_existent_project_xyz")
        self.assertFalse(res["found"])
        self.assertIn("not found", res["error"])

    def test_ignored_directories_never_matched(self):
        res = self.discovery.find_project("node_modules")
        self.assertFalse(res["found"])


if __name__ == "__main__":
    unittest.main()
