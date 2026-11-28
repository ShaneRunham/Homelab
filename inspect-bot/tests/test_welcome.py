"""Offline test: the licence draws for every status and for awkward names."""
import datetime as dt
import io
import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import licence  # noqa: E402

AV = (Path(__file__).resolve().parent.parent / "assets" / "server_icon.png").read_bytes()


class Licence(unittest.TestCase):
    def test_draws(self):
        for status, revoked in (("unverified", False), ("verified", False), ("verified", True)):
            png = licence.render(AV, "🌇 Blacki 🌆", 42, dt.date(2026, 11, 28), status, 123, revoked, "blacki")
            self.assertEqual(Image.open(io.BytesIO(png)).size, (1448, 908))

    def test_names(self):
        self.assertEqual(licence.clean("Brydzzzzz (@Brydz_2AM)"), "Brydzzzzz")
        self.assertEqual(licence.clean("𝐂𝐀𝐏𝐎𝐍𝐄😎"), "CAPONE")
        self.assertEqual(licence.clean("كوباسيتيك<", "headamoe"), "headamoe")
        self.assertEqual(licence.clean("🔥🔥"), "New rider")


if __name__ == "__main__":
    unittest.main()
