"""
Project Profiler for MARK XLVIII / JARVIS.
Safely inspects project files (package.json, pyproject.toml, Dockerfile, etc.)
and determines framework types, startup commands, and port verification strategies.
Enforces strict security against shell interpolation and command injection.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

DANGEROUS_SHELL_PATTERNS = re.compile(r"[;&|`$><]")


class ProjectProfiler:
    """
    Profiles project frameworks and determines safe, structured startup commands.
    """

    def profile_project(self, project_path: str) -> Dict[str, Any]:
        """
        Inspects project files at `project_path` and returns profiling metadata.
        """
        path = Path(project_path).resolve()
        if not path.exists() or not path.is_dir():
            return {
                "success": False,
                "error": f"Path '{project_path}' does not exist or is not a directory.",
            }

        # 1. Inspect Node / JavaScript / TypeScript projects (package.json)
        pkg_json_path = path / "package.json"
        if pkg_json_path.exists() and pkg_json_path.is_file():
            profile = self._profile_node(path, pkg_json_path)
            if profile:
                return profile

        # 2. Inspect Python projects (requirements.txt, pyproject.toml, manage.py, app.py, main.py)
        python_profile = self._profile_python(path)
        if python_profile:
            return python_profile

        # 3. Inspect Docker projects (docker-compose.yml, Dockerfile)
        docker_profile = self._profile_docker(path)
        if docker_profile:
            return docker_profile

        # 4. Inspect Go projects (go.mod)
        if (path / "go.mod").exists():
            return {
                "success": True,
                "project_type": "go",
                "framework": "go",
                "recommended_command": ["go", "run", "."],
                "verification_strategy": "detect_port_or_http",
                "port_hint": 8080,
            }

        # 5. Inspect Rust projects (Cargo.toml)
        if (path / "Cargo.toml").exists():
            return {
                "success": True,
                "project_type": "rust",
                "framework": "cargo",
                "recommended_command": ["cargo", "run"],
                "verification_strategy": "detect_port_or_http",
                "port_hint": 8080,
            }

        return {
            "success": False,
            "error": "No recognized project metadata or framework found in target directory.",
        }

    def _profile_node(self, root: Path, pkg_path: Path) -> Optional[Dict[str, Any]]:
        """Profile a Node.js ecosystem project."""
        try:
            with open(pkg_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except Exception:
            return None

        scripts: Dict[str, str] = data.get("scripts", {})
        dependencies: Dict[str, str] = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

        # Determine package manager
        pm = "npm"
        if (root / "pnpm-lock.yaml").exists():
            pm = "pnpm"
        elif (root / "yarn.lock").exists():
            pm = "yarn"
        elif (root / "bun.lockb").exists():
            pm = "bun"

        # Determine framework
        framework = "node"
        port_hint = 3000

        if "next" in dependencies:
            framework = "nextjs"
            port_hint = 3000
        elif "vite" in dependencies or any("vite" in s for s in scripts.values()):
            framework = "vite"
            port_hint = 5173
        elif "react-scripts" in dependencies:
            framework = "react"
            port_hint = 3000
        elif "express" in dependencies or "fastify" in dependencies:
            framework = "node_backend"
            port_hint = 3000

        # Determine command
        cmd: List[str] = []
        if "dev" in scripts:
            dev_val = scripts["dev"]
            if dev_val.startswith(sys.executable):
                rest = dev_val[len(sys.executable):].strip()
                import shlex
                cmd = [sys.executable] + (shlex.split(rest) if rest else [])
            elif dev_val.startswith("python") and " " in dev_val:
                import shlex
                cmd = shlex.split(dev_val)
            else:
                cmd = [pm, "run", "dev"] if pm == "npm" else [pm, "dev"]
        elif "start" in scripts:
            cmd = [pm, "start"]
        elif "serve" in scripts:
            cmd = [pm, "run", "serve"]
        else:
            main_file = data.get("main", "index.js")
            cmd = ["node", main_file]

        self._validate_command(cmd)

        return {
            "success": True,
            "project_type": framework,
            "framework": framework,
            "package_manager": pm,
            "recommended_command": cmd,
            "verification_strategy": "detect_port_or_http",
            "port_hint": port_hint,
        }

    def _profile_python(self, root: Path) -> Optional[Dict[str, Any]]:
        """Profile a Python project."""
        py_venv_bin = root / ".venv" / "bin" / "python"
        py_bin = str(py_venv_bin) if py_venv_bin.exists() else sys.executable

        # Check for Django
        if (root / "manage.py").exists():
            cmd = [py_bin, "manage.py", "runserver"]
            return {
                "success": True,
                "project_type": "django",
                "framework": "django",
                "recommended_command": cmd,
                "verification_strategy": "detect_port_or_http",
                "port_hint": 8000,
            }

        # Check for FastAPI / Uvicorn
        reqs_file = root / "requirements.txt"
        has_fastapi = False
        if reqs_file.exists():
            try:
                with open(reqs_file, "r", encoding="utf-8") as f:
                    req_text = f.read().lower()
                    if "fastapi" in req_text or "uvicorn" in req_text:
                        has_fastapi = True
            except Exception:
                pass

        main_py = root / "main.py"
        app_py = root / "app.py"

        if has_fastapi or (main_py.exists() and "fastapi" in main_py.read_text(errors="replace").lower()):
            cmd = [py_bin, "-m", "uvicorn", "main:app", "--reload"]
            return {
                "success": True,
                "project_type": "fastapi",
                "framework": "fastapi",
                "recommended_command": cmd,
                "verification_strategy": "detect_port_or_http",
                "port_hint": 8000,
            }

        # Check for Flask
        if app_py.exists():
            cmd = [py_bin, "app.py"]
            return {
                "success": True,
                "project_type": "flask",
                "framework": "flask",
                "recommended_command": cmd,
                "verification_strategy": "detect_port_or_http",
                "port_hint": 5000,
            }

        if main_py.exists():
            cmd = [py_bin, "main.py"]
            return {
                "success": True,
                "project_type": "python",
                "framework": "python_script",
                "recommended_command": cmd,
                "verification_strategy": "detect_port_or_http",
                "port_hint": 8000,
            }

        return None

    def _profile_docker(self, root: Path) -> Optional[Dict[str, Any]]:
        """Profile a Docker project."""
        if (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists():
            return {
                "success": True,
                "project_type": "docker",
                "framework": "docker-compose",
                "recommended_command": ["docker", "compose", "up"],
                "verification_strategy": "detect_port_or_http",
                "port_hint": 80,
            }
        return None

    def _validate_command(self, cmd: List[str]) -> None:
        """Enforces security rules against shell interpolation."""
        if not isinstance(cmd, list) or not cmd:
            raise ValueError("Command must be a non-empty list of string tokens.")
        for token in cmd:
            if not isinstance(token, str):
                raise ValueError("Command tokens must be strings.")
            if DANGEROUS_SHELL_PATTERNS.search(token):
                raise ValueError(f"Dangerous shell metacharacter detected in command token: '{token}'")


# Global singleton
project_profiler = ProjectProfiler()
