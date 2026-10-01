"""
Unit tests for Project Profiler (Phase 8).
Verifies framework detection for Vite, Next.js, FastAPI, Flask, Docker, and shell injection protection.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from core.project_profiler import ProjectProfiler


class TestProjectProfiler(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.profiler = ProjectProfiler()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_profile_vite_node_project(self):
        proj = self.temp_dir / "vite_app"
        proj.mkdir()
        pkg = {
            "name": "vite_app",
            "scripts": {"dev": "vite", "build": "vite build"},
            "dependencies": {"vite": "^5.0.0"},
        }
        with open(proj / "package.json", "w") as f:
            json.dump(pkg, f)

        res = self.profiler.profile_project(str(proj))
        self.assertTrue(res["success"])
        self.assertEqual(res["project_type"], "vite")
        self.assertEqual(res["recommended_command"], ["npm", "run", "dev"])
        self.assertEqual(res["port_hint"], 5173)

    def test_profile_nextjs_project(self):
        proj = self.temp_dir / "next_app"
        proj.mkdir()
        pkg = {
            "name": "next_app",
            "scripts": {"dev": "next dev", "build": "next build"},
            "dependencies": {"next": "14.0.0", "react": "18.2.0"},
        }
        with open(proj / "package.json", "w") as f:
            json.dump(pkg, f)

        res = self.profiler.profile_project(str(proj))
        self.assertTrue(res["success"])
        self.assertEqual(res["project_type"], "nextjs")
        self.assertEqual(res["recommended_command"], ["npm", "run", "dev"])
        self.assertEqual(res["port_hint"], 3000)

    def test_profile_fastapi_python_project(self):
        proj = self.temp_dir / "fastapi_app"
        proj.mkdir()
        with open(proj / "main.py", "w") as f:
            f.write("from fastapi import FastAPI\napp = FastAPI()\n")

        res = self.profiler.profile_project(str(proj))
        self.assertTrue(res["success"])
        self.assertEqual(res["project_type"], "fastapi")
        self.assertIn("uvicorn", res["recommended_command"])

    def test_profile_flask_project(self):
        proj = self.temp_dir / "flask_app"
        proj.mkdir()
        with open(proj / "app.py", "w") as f:
            f.write("from flask import Flask\napp = Flask(__name__)\n")

        res = self.profiler.profile_project(str(proj))
        self.assertTrue(res["success"])
        self.assertEqual(res["project_type"], "flask")

    def test_profile_docker_project(self):
        proj = self.temp_dir / "docker_app"
        proj.mkdir()
        with open(proj / "docker-compose.yml", "w") as f:
            f.write("version: '3'\nservices:\n  web:\n    image: nginx\n")

        res = self.profiler.profile_project(str(proj))
        self.assertTrue(res["success"])
        self.assertEqual(res["project_type"], "docker")
        self.assertEqual(res["recommended_command"], ["docker", "compose", "up"])

    def test_shell_injection_attempt_rejected(self):
        with self.assertRaises(ValueError):
            self.profiler._validate_command(["npm", "run", "dev; rm -rf /"])

        with self.assertRaises(ValueError):
            self.profiler._validate_command(["python", "main.py && echo pwned"])


if __name__ == "__main__":
    unittest.main()
