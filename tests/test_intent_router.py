"""
Unit tests for core.intent_router (Local Intent Router).
"""

import unittest
from core.intent_router import IntentRouter


class TestIntentRouter(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_get_time(self):
        phrases = [
            "What time is it?",
            "what's the time?",
            "tell me the time",
            "current time",
            "what is the time",
        ]
        for p in phrases:
            m = self.router.match(p)
            self.assertTrue(m["handled"], f"Failed on phrase: {p}")
            self.assertEqual(m["intent"], "GET_TIME")

    def test_get_date(self):
        phrases = [
            "What date is it?",
            "what's today's date?",
            "tell me today's date",
            "current date",
        ]
        for p in phrases:
            m = self.router.match(p)
            self.assertTrue(m["handled"], f"Failed on phrase: {p}")
            self.assertEqual(m["intent"], "GET_DATE")

    def test_open_app(self):
        phrases = [
            ("Open Chrome", "chrome"),
            ("open Safari", "safari"),
            ("Open VS Code", "vs code"),
            ("open Terminal", "terminal"),
        ]
        for p, app in phrases:
            m = self.router.match(p)
            self.assertTrue(m["handled"], f"Failed on phrase: {p}")
            self.assertEqual(m["intent"], "OPEN_APP")
            self.assertEqual(m["parameters"]["app_name"], app)

    def test_close_app(self):
        phrases = [
            ("Close Chrome", "chrome"),
            ("close Safari", "safari"),
        ]
        for p, app in phrases:
            m = self.router.match(p)
            self.assertTrue(m["handled"], f"Failed on phrase: {p}")
            self.assertEqual(m["intent"], "CLOSE_APP")
            self.assertEqual(m["parameters"]["app_name"], app)

    def test_system_control(self):
        phrases = [
            ("Take a screenshot", "TAKE_SCREENSHOT"),
            ("Mute", "MUTE"),
            ("Unmute", "UNMUTE"),
            ("Volume up", "VOLUME_UP"),
            ("Volume down", "VOLUME_DOWN"),
        ]
        for p, expected_intent in phrases:
            m = self.router.match(p)
            self.assertTrue(m["handled"], f"Failed on phrase: {p}")
            self.assertEqual(m["intent"], expected_intent)

    def test_jarvis_control(self):
        phrases = ["Stop", "Quit", "Exit", "Go to sleep"]
        for p in phrases:
            m = self.router.match(p)
            self.assertTrue(m["handled"], f"Failed on phrase: {p}")
            self.assertEqual(m["intent"], "SHUTDOWN")

    def test_unhandled_complex_queries(self):
        complex_phrases = [
            "Hello",
            "What's on my screen?",
            "Search top world news",
            "Open Chrome and search python tutorials",
            "Tell me a story about Jarvis",
        ]
        for p in complex_phrases:
            m = self.router.match(p)
            self.assertFalse(m["handled"], f"Should NOT handle phrase locally: {p}")

    def test_execution(self):
        m = self.router.match("What time is it?")
        res = self.router.execute(m)
        self.assertTrue(res["handled"])
        self.assertIn("It is currently", res["response"])


if __name__ == "__main__":
    unittest.main()
