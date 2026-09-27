from __future__ import annotations

import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.render_livearea import SIZES, png_geometry, render


ROOT = Path(__file__).resolve().parents[1]


class LiveAreaRenderTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("convert"), "ImageMagick convert unavailable")
    def test_candidate_version_and_indexed_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            render("A3.5-dev203", ROOT / "assets", output)
            for name, dimensions in SIZES.items():
                self.assertEqual(png_geometry(output / name), (*dimensions, 3))
            self.assertFalse((output / "candidate-banner.svg").exists())

    def test_bad_candidate_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                render("A3.5-dev203<bad>", ROOT / "assets", Path(directory))

    @unittest.skipUnless(shutil.which("convert"), "ImageMagick convert unavailable")
    def test_version_changes_all_labelled_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            render("A3.5-dev203", ROOT / "assets", root / "203")
            render("A3.5-dev204", ROOT / "assets", root / "204")
            self.assertEqual((root / "203/icon0.png").read_bytes(),
                             (root / "204/icon0.png").read_bytes())
            for name in ("bg0.png", "startup.png", "pic0.png"):
                self.assertNotEqual((root / "203" / name).read_bytes(),
                                    (root / "204" / name).read_bytes())

    def test_template_references_packaged_images(self):
        root = ET.parse(ROOT / "assets/livearea/template.xml").getroot()
        self.assertEqual(root.attrib["style"], "a1")
        self.assertEqual(root.findtext("livearea-background/image"), "bg0.png")
        self.assertEqual(root.findtext("gate/startup-image"), "startup.png")


if __name__ == "__main__":
    unittest.main()
