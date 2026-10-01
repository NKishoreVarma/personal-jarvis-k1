"""
Computer Observer for MARK XLVIII / JARVIS.
Provides clean observation interfaces (observe_screen, observe_window, observe_browser)
and vision analysis using existing screen capture functionality and Gemini vision models.
"""

from __future__ import annotations

import io
import time
from typing import Any, Dict, Optional
from PIL import Image


class ComputerObserver:
    """
    Handles screen capture and vision analysis for the JARVIS Agent Loop.
    Only captures screen when explicitly requested by an observation/verification step.
    """

    def __init__(self):
        pass

    def observe_screen(self) -> Dict[str, Any]:
        """
        Captures the current screen state using actions/screen_processor.py capture.
        Returns structured observation dictionary.
        """
        t_start = time.monotonic()
        try:
            from actions.screen_processor import _capture_screen
            img = _capture_screen()
            t_cap = time.monotonic() - t_start
            print(f"[VISION] Capture: {t_cap:.2f}s")

            width, height = img.size
            return {
                "success": True,
                "type": "screen",
                "image": img,
                "metadata": {
                    "width": width,
                    "height": height,
                },
                "timestamp": time.monotonic(),
                "capture_duration": t_cap,
            }
        except Exception as e:
            t_cap = time.monotonic() - t_start
            print(f"[VISION] Capture failed: {e}")
            return {
                "success": False,
                "type": "screen",
                "error": str(e),
                "timestamp": time.monotonic(),
                "capture_duration": t_cap,
            }

    def observe_window(self, app_name: Optional[str] = None) -> Dict[str, Any]:
        """Window observation abstraction."""
        obs = self.observe_screen()
        obs["type"] = "window"
        obs["metadata"]["app_name"] = app_name or "active"
        return obs

    def observe_browser(self) -> Dict[str, Any]:
        """Browser state observation abstraction."""
        obs = self.observe_screen()
        obs["type"] = "browser"
        return obs

    def analyze_screen(self, image: Any, question: str) -> Dict[str, Any]:
        """
        Performs vision analysis on a screen image for a specific question.
        Returns structured analysis result.
        """
        t_start = time.monotonic()
        if not image:
            return {"success": False, "answer": "No image provided", "analysis_duration": 0.0}

        try:
            from actions.web_search import _get_api_key
            api_key = _get_api_key()
            if not api_key:
                return {"success": False, "answer": "API key unavailable", "analysis_duration": 0.0}

            from google import genai
            client = genai.Client(api_key=api_key)

            # Convert PIL image to PNG bytes for vision input if needed
            if isinstance(image, Image.Image):
                buf = io.BytesIO()
                image.save(buf, format="PNG")
                img_bytes = buf.getvalue()
            elif isinstance(image, bytes):
                img_bytes = image
            else:
                img_bytes = str(image).encode()

            prompt = (
                f"You are the JARVIS Vision Analyzer.\n"
                f"Question: '{question}'\n"
                f"Answer concisely based strictly on what is visible in the provided screenshot."
            )

            from google.genai import types
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    prompt,
                ],
            )

            t_analysis = time.monotonic() - t_start
            t_total = t_analysis
            print(f"[VISION] Analysis: {t_analysis:.2f}s | Total: {t_total:.2f}s")

            answer_text = response.text.strip() if response and response.text else "No analysis answer"
            return {
                "success": True,
                "answer": answer_text,
                "analysis_duration": t_analysis,
                "total_duration": t_total,
            }
        except Exception as e:
            t_analysis = time.monotonic() - t_start
            print(f"[VISION] Analysis failed: {e}")
            return {
                "success": False,
                "answer": f"Vision analysis error: {e}",
                "analysis_duration": t_analysis,
                "total_duration": t_analysis,
            }


# Global singleton instance
computer_observer = ComputerObserver()
