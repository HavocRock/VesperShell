"""Check icons are present without requiring PySide6 or Pillow at test time."""
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IconAssetsTests(unittest.TestCase):
    def test_png_is_a_real_png(self):
        png = ROOT / "assets" / "vespershell_icon.png"
        data = png.read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(data), 5_000)

    def test_windows_icon_has_multiple_resolutions(self):
        ico = ROOT / "assets" / "vespershell.ico"
        data = ico.read_bytes()
        reserved, kind, count = struct.unpack_from("<HHH", data, 0)
        self.assertEqual((reserved, kind), (0, 1))
        self.assertGreaterEqual(count, 4)


if __name__ == "__main__":
    unittest.main()
