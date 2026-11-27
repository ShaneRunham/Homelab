"""Offline test for snapshot.prune: keeps the newest auto backups, never touches manual ones."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import snapshot  # noqa: E402


class Prune(unittest.TestCase):
    def test_keeps_newest_auto_only(self):
        with tempfile.TemporaryDirectory() as d:
            snapshot.BACKUPS = Path(d)
            for i in range(5):
                (Path(d) / f"auto-2026120{i}-040000.json").write_text("{}")
            (Path(d) / "layout-20261126-225206.json").write_text("{}")
            snapshot.prune(keep=2)
            left = sorted(p.name for p in Path(d).iterdir())
            self.assertEqual(left, ["auto-20261203-040000.json", "auto-20261204-040000.json",
                                    "layout-20261126-225206.json"])


if __name__ == "__main__":
    unittest.main()
