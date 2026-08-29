import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "docs" / "HISTORICAL_SCREENSHOT_TIMELINE.md"
SCREENSHOT_DIR = ROOT / "docs" / "history" / "screenshots"


class HistoricalScreenshotTimelineContract(unittest.TestCase):
    def test_timeline_references_every_gallery_png(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        screenshots = sorted(path.name for path in SCREENSHOT_DIR.glob("*.png"))

        self.assertGreaterEqual(len(screenshots), 10)
        self.assertLessEqual(len(screenshots), 15)
        self.assertEqual(len(screenshots), 15)
        self.assertFalse(list(SCREENSHOT_DIR.glob("*.bmp")))
        for name in screenshots:
            self.assertIn(f"history/screenshots/{name}", doc)

    def test_timeline_is_gameplay_first(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        self.assertIn("## Five Gameplay-First Samples", doc)
        self.assertIn("curated 15-image set", doc)
        lead = doc.split("## Five Gameplay-First Samples", 1)[1].split(
            "## Timeline", 1
        )[0]
        image_refs = re.findall(r"history/screenshots/[^\"<\s]+\.png", lead)

        self.assertEqual(len(image_refs), 5)
        self.assertIn("a35-dev5-spawn-control.png", lead)
        self.assertIn("a35-dev7-effects-131326.png", lead)
        self.assertIn("a35-dev13-selected-frame.png", lead)
        self.assertIn("a35-dev16-selected-frame.png", lead)
        self.assertIn("a35-dev17-selected-frame.png", lead)

    def test_timeline_declares_boundary_and_missing_screenshots(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        normalized = " ".join(doc.split())

        self.assertIn("Each build section includes up to five", doc)
        self.assertIn("These images are historical evidence", doc)
        self.assertIn("They do not make dev82 physically accepted", normalized)
        self.assertIn("## Builds With No Local Screenshot File", doc)
        self.assertIn("Do not fabricate images from logs", normalized)


if __name__ == "__main__":
    unittest.main()
