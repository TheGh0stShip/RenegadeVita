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

        self.assertGreaterEqual(len(screenshots), 150)
        self.assertFalse(list(SCREENSHOT_DIR.glob("*.bmp")))
        for name in screenshots:
            self.assertIn(f"history/screenshots/{name}", doc)

    def test_timeline_has_uncapped_quick_historical_view(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        self.assertNotIn("## Five Gameplay-First Samples", doc)
        self.assertIn("## Quick Historical View", doc)
        self.assertIn("up to 15", doc)
        self.assertIn("fewer than 15 local or Vita-pulled screenshots exist", doc)
        lead = doc.split("## Quick Historical View", 1)[1].split(
            "## Timeline", 1
        )[0]
        image_refs = re.findall(r"history/screenshots/[^\"<\s]+\.png", lead)

        self.assertGreaterEqual(len(image_refs), 20)
        self.assertIn("a35-dev5-spawn-control.png", lead)
        self.assertIn("a35-dev6-vita-first-interactive-player-frame-f1-t31158328.png", lead)
        self.assertIn("a35-dev7-effects-131326.png", lead)
        self.assertIn("a35-dev42-vita-original-loading-screen-level-ready-t28329716.png", lead)
        self.assertIn("a35-dev78-loading-physical.png", lead)
        self.assertIn("a35-dev79-vita-original-loading-screen-level-ready-t29494542.png", lead)

    def test_each_build_section_is_capped_at_fifteen_images(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        timeline = doc.split("## Timeline", 1)[1].split(
            "## Builds With No Local Or Vita-Pulled Screenshot File", 1
        )[0]
        sections = re.split(r"\n### ", timeline)

        for section in sections:
            if not section.strip():
                continue
            image_refs = re.findall(r"history/screenshots/[^\"<\s]+\.png", section)
            self.assertLessEqual(len(image_refs), 15, section.splitlines()[0])

    def test_recovered_builds_have_expected_section_counts(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        expected_counts = {
            "A3.5-dev5": 15,
            "A3.5-dev6": 2,
            "A3.5-dev7": 15,
            "A3.5-dev18": 14,
            "A3.5-dev19": 6,
            "A3.5-dev42": 8,
            "A3.5-dev43": 15,
            "A3.5-dev47": 4,
            "A3.5-dev78": 8,
            "A3.5-dev79": 4,
        }

        for build, expected in expected_counts.items():
            section = doc.split(f"### {build}", 1)[1].split("\n### ", 1)[0]
            image_refs = re.findall(r"history/screenshots/[^\"<\s]+\.png", section)
            self.assertEqual(len(image_refs), expected, build)

    def test_timeline_declares_boundary_and_missing_screenshots(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        normalized = " ".join(doc.split())

        self.assertIn("Each build section includes up to 15", doc)
        self.assertIn("VitaShell FTP pull", doc)
        self.assertIn("These images are historical evidence", doc)
        self.assertIn("They do not make dev82 physically accepted", normalized)
        self.assertIn("## Builds With No Local Or Vita-Pulled Screenshot File", doc)
        self.assertIn("Do not fabricate images from logs", normalized)
        missing = doc.split("## Builds With No Local Or Vita-Pulled Screenshot File", 1)[1]
        for recovered in (
            "A3.5-dev6",
            "A3.5-dev19",
            "A3.5-dev20",
            "A3.5-dev21",
            "A3.5-dev24",
            "A3.5-dev42",
            "A3.5-dev44",
            "A3.5-dev47",
            "A3.5-dev79",
        ):
            self.assertNotIn(recovered, missing)

    def test_readme_surfaces_gallery_before_current_state(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertLess(
            readme.index("## Historical Visual Progress"),
            readme.index("## Current State"),
        )
        lead = readme.split("## Historical Visual Progress", 1)[1].split(
            "## Current State", 1
        )[0]
        self.assertIn("docs/history/screenshots/a35-dev5-spawn-control.png", readme)
        self.assertIn("docs/history/screenshots/a35-dev79-vita-original-loading-screen-level-ready-t29494542.png", readme)
        self.assertIn("historical screenshot timeline", readme)
        self.assertGreaterEqual(len(re.findall(r"docs/history/screenshots/[^\"<\s]+\.png", lead)), 20)


if __name__ == "__main__":
    unittest.main()
