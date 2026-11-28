"""Offline tests for strikes.py's rules (no Discord connection)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import strikes as sk  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400


def st(*strikes):
    return {"next": len(strikes) + 1, "items": {str(i): dict(n=i, member=m, rule="ramming", note="x", at=at, **extra)
                                                for i, (m, at, extra) in enumerate(strikes, 1)}}


class Active(unittest.TestCase):
    def test_counts_only_this_member(self):
        self.assertEqual(len(sk.active(st((1, NOW, {}), (2, NOW, {})), 1, NOW)), 1)

    def test_expire_after_60_days(self):
        s = st((1, NOW - 61 * DAY, {}), (1, NOW - 59 * DAY, {}))
        self.assertEqual(len(sk.active(s, 1, NOW)), 1)

    def test_removed_dont_count(self):
        self.assertEqual(sk.active(st((1, NOW, {"removed": "Shane"})), 1, NOW), [])


class Ladder(unittest.TestCase):
    def test_steps(self):
        self.assertEqual(sk.step(1), ("Warning", False))
        self.assertEqual(sk.step(2), ("Final warning", False))
        self.assertTrue(sk.step(3)[1] and "Sit out" in sk.step(3)[0])
        self.assertTrue(sk.step(5)[1] and "removal" in sk.step(5)[0])

    def test_dm_matches_count(self):
        s = st((1, NOW, {}))["items"]["1"]
        self.assertIn("warning", sk.dm_text(s, 1, "DPGS"))
        self.assertIn("final warning", sk.dm_text(s, 2, "DPGS"))
        self.assertIn("Staff will be in touch", sk.dm_text(s, 3, "DPGS"))


class Text(unittest.TestCase):
    def test_record(self):
        s = st((1, NOW, {}), (1, NOW - 90 * DAY, {}), (1, NOW, {"removed": "x"}))
        r = sk.record_text(s, 1, "Rider", NOW)
        self.assertIn("1 active", r)
        self.assertIn("expired", r)
        self.assertIn("removed", r)
        self.assertIn("clean record", sk.record_text(s, 9, "Other", NOW))

    def test_rules_card_fits(self):
        t = sk.rules_text()
        self.assertLess(len(t), 2000)
        for name, _ in sk.RULES.values():
            self.assertIn(name, t)


if __name__ == "__main__":
    unittest.main()
