"""
Project Discovery for MARK XLVIII / JARVIS.
Safely discovers projects in approved workspace roots (Desktop, Projects, Developer)
using exact, case-insensitive, and fuzzy matching with ambiguity protection.
"""

from __future__ import annotations

import difflib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ProjectDiscovery:
    """
    Discovers projects within approved roots on macOS without scanning the full filesystem.
    """

    IGNORED_DIRS: Set[str] = {
        "node_modules",
        ".git",
        ".venv",
        "venv",
        "dist",
        "build",
        "__pycache__",
        ".next",
        ".cache",
        "site-packages",
        "Library",
        "Applications",
        "System",
    }

    def __init__(self, custom_roots: Optional[List[Path]] = None):
        home = Path.home()
        self.approved_roots: List[Path] = custom_roots or [
            home / "Desktop",
            home / "Projects",
            home / "Developer",
            home / "Workspace",
            Path.cwd(),
        ]

    def _clean_query(self, query: str) -> str:
        """Strip conversational prefixes like 'project', 'app', 'the'."""
        cleaned = query.strip().lower()
        cleaned = re.sub(r"^(the|project|app|repository|repo)\s+", "", cleaned)
        cleaned = re.sub(r"\s+(project|app|repo)$", "", cleaned)
        return cleaned.strip()

    def find_project(self, name: str, location_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Finds a project by name across approved roots.
        Supports exact match, case-insensitive match, and fuzzy matching.
        """
        if not name or not name.strip():
            return {"found": False, "error": "Project name cannot be empty.", "ambiguous": False, "candidates": []}

        target = self._clean_query(name)
        candidates: List[Dict[str, Any]] = []

        # Determine roots to search
        search_roots = self.approved_roots
        if location_hint:
            hint_clean = location_hint.lower().strip()
            filtered = [r for r in self.approved_roots if hint_clean in r.name.lower() or hint_clean in str(r).lower()]
            if filtered:
                search_roots = filtered
            elif "desktop" in hint_clean:
                search_roots = [Path.home() / "Desktop"]
            elif "projects" in hint_clean or "developer" in hint_clean:
                search_roots = [Path.home() / "Projects", Path.home() / "Developer"]

        # Collect directories from approved roots (max depth 1)
        for root in search_roots:
            if not root.exists() or not root.is_dir():
                continue

            try:
                for entry in root.iterdir():
                    if not entry.is_dir() or entry.name in self.IGNORED_DIRS or entry.name.startswith("."):
                        continue

                    entry_name_clean = self._clean_query(entry.name)

                    # 1. Exact match (case-sensitive)
                    if entry.name == name.strip():
                        return {
                            "found": True,
                            "name": entry.name,
                            "path": str(entry.resolve()),
                            "confidence": 1.0,
                            "ambiguous": False,
                            "candidates": [],
                        }

                    # 2. Case-insensitive exact match
                    if entry_name_clean == target:
                        candidates.append({
                            "name": entry.name,
                            "path": str(entry.resolve()),
                            "confidence": 0.95,
                        })
                        continue

                    # 3. Fuzzy similarity
                    ratio = difflib.SequenceMatcher(None, target, entry_name_clean).ratio()
                    if ratio >= 0.70:
                        candidates.append({
                            "name": entry.name,
                            "path": str(entry.resolve()),
                            "confidence": round(ratio, 2),
                        })
            except PermissionError:
                continue

        if not candidates:
            return {
                "found": False,
                "name": name,
                "error": f"Project '{name}' was not found in approved locations.",
                "ambiguous": False,
                "candidates": [],
            }

        # Sort candidates by confidence descending
        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        # Check for ambiguity (e.g. top candidates have nearly identical confidence)
        if len(candidates) > 1:
            top_conf = candidates[0]["confidence"]
            close_candidates = [c for c in candidates if abs(c["confidence"] - top_conf) < 0.05]
            if len(close_candidates) > 1 and top_conf < 0.95:
                return {
                    "found": False,
                    "name": name,
                    "ambiguous": True,
                    "candidates": [c["name"] for c in close_candidates],
                    "error": f"Ambiguous project name '{name}'. Multiple candidates found.",
                }

        best = candidates[0]
        return {
            "found": True,
            "name": best["name"],
            "path": best["path"],
            "confidence": best["confidence"],
            "ambiguous": False,
            "candidates": [c["name"] for c in candidates],
        }


# Global singleton
project_discovery = ProjectDiscovery()
