import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "live"))

import live_server


class PublicSafeLiveTests(unittest.TestCase):
    def test_sanitizer_redacts_sensitive_shapes(self):
        text = (
            r"C:\Users\casho\secret.txt "
            "https://example.test/private "
            "192.168.1.22 "
            "person@example.com "
            "token=SUPERSECRET "
            "abcdef0123456789abcdef0123456789"
        )
        clean = live_server.sanitize_public_text(text, 1000)
        self.assertNotIn("casho", clean)
        self.assertNotIn("example.test", clean)
        self.assertNotIn("192.168.1.22", clean)
        self.assertNotIn("person@example.com", clean)
        self.assertNotIn("SUPERSECRET", clean)
        self.assertNotIn("abcdef0123456789abcdef0123456789", clean)
        self.assertIn("[LOCAL_PATH]", clean)
        self.assertIn("[URL]", clean)
        self.assertIn("[IP]", clean)
        self.assertIn("[EMAIL]", clean)

    def test_public_command_start_hides_raw_command(self):
        event = {
            "seq": 1,
            "timestamp": 1.0,
            "source": "ASTRA",
            "kind": "COMMAND_START",
            "label": "Validation",
            "detail": r"python C:\Users\casho\private.py --token=ABC",
            "status": "RUN",
        }
        public = live_server.public_event(event)
        self.assertEqual(public["detail"], "Validation lancée")
        self.assertNotIn("python", public["detail"])
        self.assertNotIn("casho", public["detail"])

    def test_public_output_is_summarized(self):
        event = {
            "seq": 2,
            "timestamp": 1.0,
            "source": "ASTRA",
            "kind": "OUTPUT",
            "label": "Tests",
            "detail": "Ran 14 tests in 0.029s",
            "status": "RUN",
        }
        public = live_server.public_event(event)
        self.assertEqual(public["detail"], "14 tests · 0.029s")

    def test_public_snapshot_is_read_only_and_filtered(self):
        snap = live_server.public_snapshot()
        self.assertEqual(snap["mode"], "PUBLIC_SAFE")
        self.assertTrue(snap["read_only"])
        self.assertNotIn("input", snap)
        self.assertNotIn("route", snap)
        self.assertNotIn("source_commit", snap["f1"])
        self.assertIn("source_commit_short", snap["f1"])
        self.assertLessEqual(len(snap["public_values"]), 12)


if __name__ == "__main__":
    unittest.main()
