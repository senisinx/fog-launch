"""The icon files the window and the program file use.

Fog Launch needs no third-party packages, so these checks read the files with the standard library; the pixel
checks run only where Pillow happens to be installed.
"""

import io
import struct
import unittest
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # the tests on GitHub run without third-party packages
    Image = None

ASSETS = Path(__file__).resolve().parent.parent / "fog_launch" / "assets"


def png_size(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", data[16:24])


def ico_sizes(path):
    data = path.read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1), path
    sizes = []
    for index in range(count):
        width, height = data[6 + 16 * index], data[7 + 16 * index]
        sizes.append((width or 256, height or 256))
    return sorted(sizes)


class IconTests(unittest.TestCase):
    def test_the_pictures_have_their_sizes(self):
        self.assertEqual(png_size(ASSETS / "icon.png"), (256, 256))
        self.assertEqual(png_size(ASSETS / "icon-32.png"), (32, 32))
        self.assertIn("<svg", (ASSETS / "icon.svg").read_text(encoding="utf-8"))

    def test_the_ico_has_every_size_for_windows(self):
        sizes = ico_sizes(ASSETS / "icon.ico")
        for size in (16, 24, 32, 48, 256):
            self.assertIn((size, size), sizes)

    @unittest.skipIf(Image is None, "needs Pillow")
    def test_the_corners_are_transparent_and_small_sizes_use_the_small_picture(self):
        for name in ("icon.png", "icon-32.png"):
            with Image.open(ASSETS / name) as picture:
                self.assertEqual(picture.convert("RGBA").getpixel((0, 0))[3], 0)
        ico = Image.open(io.BytesIO((ASSETS / "icon.ico").read_bytes()))
        ico.size = (32, 32)
        with Image.open(ASSETS / "icon-32.png") as small:
            self.assertEqual(ico.convert("RGBA").tobytes(), small.convert("RGBA").tobytes())


if __name__ == "__main__":
    unittest.main()
