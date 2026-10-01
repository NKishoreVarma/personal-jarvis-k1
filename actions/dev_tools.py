"""
Developer Tools Layer for MARK XLVIII / JARVIS.
Provides safe, sandboxed development operations (list directory, read file, search code,
git status, project detection, and whitelisted project command execution).
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Allowed workspace roots for developer actions
ALLOWED_WORKSPACE_ROOTS: List[Path] = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Projects",
    Path(__file__).resolve().parent.parent,
]

# Sensitive patterns and filenames that must never be accessed or exposed
FORBIDDEN_NAMES: Set[str] = {
    ".ssh",
    ".aws",
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "private_key",
    "private.key",
    "id_dsa",
    "id_ecdsa",
}

# Directories to ignore during code search
IGNORED_DIRS: Set[str] = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
}

# Whitelist prefixes for safe project commands
SAFE_COMMAND_PREFIXES: List[str] = [
    "npm test",
    "npm run build",
    "npm run lint",
    "pytest",
    "python -m unittest",
    "python -m py_compile",
    "python3 -m unittest",
    "python3 -m py_compile",
    "git status",
    "git diff",
    "git log",
    "git branch",
    "cargo test",
    "cargo check",
    "go test",
]


def _validate_sandbox_path(target_path: str) -> Path:
    """
    Validates and resolves a path against allowed workspace roots.
    Raises PermissionError if path is outside allowed roots or targets forbidden files.
    """
    if not target_path or not str(target_path).strip():
        target_path = "."

    p = Path(target_path).expanduser().resolve()

    # Check against forbidden filenames or path parts
    for part in p.parts:
        if part in FORBIDDEN_NAMES or part.startswith(".env"):
            raise PermissionError(f"Access to sensitive path '{part}' is restricted.")

    # Verify that resolved path is inside at least one allowed workspace root
    is_allowed = False
    for root in ALLOWED_WORKSPACE_ROOTS:
        try:
            resolved_root = root.expanduser().resolve()
            if p == resolved_root or resolved_root in p.parents:
                is_allowed = True
                break
        except Exception:
            continue

    if not is_allowed:
        raise PermissionError(
            f"Path '{target_path}' is outside the allowed workspace directories."
        )

    return p


def _mask_secrets(text: str) -> str:
    """Masks API keys, tokens, and credentials in file output."""
    masked = re.sub(
        r'(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{8,})["\']?',
        r'\1 = "***MASKED***"',
        text,
    )
    return masked


def list_directory(path: str = ".") -> Dict[str, Any]:
    """Lists files and directories inside an allowed workspace path."""
    try:
        resolved = _validate_sandbox_path(path)
        if not resolved.exists():
            return {"success": False, "error": f"Directory '{path}' does not exist"}

        if not resolved.is_dir():
            return {"success": False, "error": f"Path '{path}' is not a directory"}

        items: List[Dict[str, Any]] = []
        for entry in os.scandir(resolved):
            if entry.name in IGNORED_DIRS or entry.name in FORBIDDEN_NAMES:
                continue
            is_file = entry.is_file()
            items.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size_bytes": entry.stat().st_size if is_file else None,
            })

        items.sort(key=lambda x: (not x["is_dir"], x["name"]))
        return {
            "success": True,
            "path": str(resolved),
            "total_items": len(items),
            "items": items,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_file(path: str, max_lines: int = 500, max_bytes: int = 100_000) -> Dict[str, Any]:
    """Reads a text file safely with line numbers and secret masking."""
    try:
        resolved = _validate_sandbox_path(path)
        if not resolved.exists():
            return {"success": False, "error": f"File '{path}' does not exist"}

        if not resolved.is_file():
            return {"success": False, "error": f"Path '{path}' is not a file"}

        size = resolved.stat().st_size
        if size > max_bytes:
            return {"success": False, "error": f"File exceeds size limit ({size} > {max_bytes} bytes)"}

        lines: List[str] = []
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, start=1):
                if idx > max_lines:
                    lines.append(f"... Truncated after {max_lines} lines")
                    break
                lines.append(f"{idx}: {line.rstrip()}")

        content_str = "\n".join(lines)
        safe_content = _mask_secrets(content_str)
        return {
            "success": True,
            "path": str(resolved),
            "line_count": len(lines),
            "lines": safe_content.split("\n"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_code(query: str, path: str = ".", max_matches: int = 50) -> Dict[str, Any]:
    """Recursively searches for code pattern inside an allowed directory."""
    try:
        resolved = _validate_sandbox_path(path)
        if not resolved.exists() or not resolved.is_dir():
            return {"success": False, "error": f"Invalid directory '{path}'"}

        matches: List[Dict[str, Any]] = []
        query_lower = query.lower()

        for root, dirs, files in os.walk(resolved):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and d not in FORBIDDEN_NAMES]
            for file in files:
                if file in FORBIDDEN_NAMES or file.startswith(".env"):
                    continue

                file_path = Path(root) / file
                # Search only source/text files
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_idx, line in enumerate(f, start=1):
                            if query_lower in line.lower():
                                rel_path = file_path.relative_to(resolved)
                                matches.append({
                                    "file": str(rel_path),
                                    "line": line_idx,
                                    "content": _mask_secrets(line.strip()),
                                })
                                if len(matches) >= max_matches:
                                    break
                except Exception:
                    continue

                if len(matches) >= max_matches:
                    break
            if len(matches) >= max_matches:
                break

        return {
            "success": True,
            "query": query,
            "path": str(resolved),
            "total_matches": len(matches),
            "matches": matches,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_project_info(path: str = ".") -> Dict[str, Any]:
    """Detects project structure, languages, and manifests in an allowed directory."""
    try:
        resolved = _validate_sandbox_path(path)
        if not resolved.exists() or not resolved.is_dir():
            return {"success": False, "error": f"Invalid directory '{path}'"}

        manifests: List[str] = []
        project_types: List[str] = []

        manifest_mapping = {
            "package.json": "Node.js / JavaScript / TypeScript",
            "requirements.txt": "Python",
            "pyproject.toml": "Python (Poetry / Flit / PEP 517)",
            "Cargo.toml": "Rust",
            "go.mod": "Go",
            "pom.xml": "Java (Maven)",
            "build.gradle": "Java / Kotlin (Gradle)",
        }

        for filename, ptype in manifest_mapping.items():
            if (resolved / filename).exists():
                manifests.append(filename)
                if ptype not in project_types:
                    project_types.append(ptype)

        return {
            "success": True,
            "path": str(resolved),
            "project_types": project_types or ["Generic / Unknown"],
            "manifests": manifests,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_git_status(path: str = ".") -> Dict[str, Any]:
    """Checks git status and active branch within an allowed directory."""
    try:
        resolved = _validate_sandbox_path(path)
        if not resolved.exists() or not resolved.is_dir():
            return {"success": False, "error": f"Invalid directory '{path}'"}

        # Run git status safely
        branch_proc = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(resolved),
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        status_proc = subprocess.run(
            ["git", "status", "-s"],
            cwd=str(resolved),
            capture_output=True,
            text=True,
            timeout=5.0,
        )

        branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else "unknown"
        status_output = status_proc.stdout.strip() if status_proc.returncode == 0 else "Not a git repository"

        return {
            "success": True,
            "path": str(resolved),
            "branch": branch,
            "status": status_output or "Clean working tree",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_project_command(command: str, path: str = ".") -> Dict[str, Any]:
    """
    Executes a whitelisted project command inside an allowed directory.
    Rejects shell injection and dangerous or unwhitelisted commands.
    """
    try:
        resolved = _validate_sandbox_path(path)
        cmd_clean = command.strip()

        # Reject dangerous shell operators
        for char in [";", "&&", "||", "|", "`", "$", ">", "<", "\n"]:
            if char in cmd_clean:
                return {
                    "success": False,
                    "error": f"Shell operator '{char}' is forbidden in project commands.",
                }

        # Validate against whitelist
        is_safe = any(cmd_clean.startswith(prefix) for prefix in SAFE_COMMAND_PREFIXES)
        if not is_safe:
            return {
                "success": False,
                "error": f"Command '{cmd_clean}' is not in the safe command whitelist.",
            }

        # Execute using split tokens without shell=True
        import sys
        tokens = cmd_clean.split()
        if tokens and tokens[0] in ("python", "python3"):
            tokens[0] = sys.executable

        proc = subprocess.run(
            tokens,
            cwd=str(resolved),
            capture_output=True,
            text=True,
            timeout=30.0,
        )

        return {
            "success": proc.returncode == 0,
            "command": cmd_clean,
            "returncode": proc.returncode,
            "stdout": _mask_secrets(proc.stdout.strip()),
            "stderr": _mask_secrets(proc.stderr.strip()),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command execution timed out (30s limit)"}
    except Exception as e:
        return {"success": False, "error": str(e)}
