"""Offline tests for suggestions.py's rules (no Discord connection)."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import suggestions as sg  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400


def member(days_in=30, verified=True, id=1):
    roles = [NS(name="Verified")] if verified else []
    return NS(id=id, roles=roles, joined_at=dt.datetime.fromtimestamp(NOW - days_in * DAY, dt.timezone.utc))


class Limits(unittest.TestCase):
    def test_ok(self):
        self.assertIsNone(sg.can_submit({"last": {}}, member(), NOW, staff=False))

    def test_must_verify(self):
        self.assertIn("Verify", sg.can_submit({"last": {}}, member(verified=False), NOW, staff=False))

    def test_seven_days(self):
        self.assertIn("2 days to go", sg.can_submit({"last": {}}, member(days_in=5.5), NOW, staff=False))

    def test_one_a_day(self):
        st = {"last": {"1": NOW - 3600 * 20}}
        self.assertIn("4 hours", sg.can_submit(st, member(), NOW, staff=False))
        self.assertIsNone(sg.can_submit(st, member(), NOW + 3600 * 4, staff=False))

    def test_staff_skip_limits(self):
        st = {"last": {"1": NOW - 60}}
        self.assertIsNone(sg.can_submit(st, member(days_in=0, verified=False), NOW, staff=True))


class Voting(unittest.TestCase):
    def test_vote_change_and_take_back(self):
        item = {}
        sg.vote(item, 1, 1)
        sg.vote(item, 2, 1)
        sg.vote(item, 3, -1)
        self.assertEqual(sg.tally(item), (2, 1))
        sg.vote(item, 3, 1)  # switch
        self.assertEqual(sg.tally(item), (3, 0))
        sg.vote(item, 3, 1)  # same again: taken back
        self.assertEqual(sg.tally(item), (2, 0))

    def test_close_after_seven_days(self):
        pop = {"n": 1, "status": "open", "posted": NOW - 7 * DAY, "votes": {str(i): 1 for i in range(6)} | {"x": -1}}
        quiet = {"n": 2, "status": "open", "posted": NOW - 8 * DAY, "votes": {"a": 1, "b": 1}}
        young = {"n": 3, "status": "open", "posted": NOW - 6 * DAY, "votes": {}}
        decided = {"n": 4, "status": "accepted", "posted": NOW - 30 * DAY, "votes": {}}
        st = {"items": {"1": pop, "2": quiet, "3": young, "4": decided}}
        done = sg.close_due(st, NOW)
        self.assertEqual([i["n"] for i in done], [1, 2])
        self.assertEqual((pop["status"], quiet["status"], young["status"], decided["status"]),
                         ("popular", "quiet", "open", "accepted"))

    def test_buttons(self):
        item = {"n": 5, "cat": "bls", "status": "queued", "votes": {}}
        ids = [b.custom_id for b in sg.queue_view(item).children]
        self.assertEqual(ids, ["sg:post:5", "sg:bin:5", "sg:dupe:5", "sg:pass:5"])
        item["status"] = "open"
        self.assertEqual([b.custom_id for b in sg.queue_view(item).children],
                         ["sg:accept:5", "sg:progress:5", "sg:deny:5", "sg:pass:5"])
        item["cat"], item["status"] = "discord", "bls"
        self.assertEqual(sg.queue_view(item).children, [])
        self.assertTrue(all(b.disabled for b in sg.public_view({"n": 5, "status": "quiet"}).children))


if __name__ == "__main__":
    unittest.main()
