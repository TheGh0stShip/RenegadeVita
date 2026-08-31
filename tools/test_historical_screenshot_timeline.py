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

        self.assertGreaterEqual(len(screenshots), 173)
        self.assertFalse(list(SCREENSHOT_DIR.glob("*.bmp")))
        for name in screenshots:
            self.assertIn(f"history/screenshots/{name}", doc)

    def test_quick_gameplay_view_excludes_loading_and_diagnostic_only_refs(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        self.assertNotIn("## Five Gameplay-First Samples", doc)
        self.assertIn("## Quick Gameplay View", doc)
        self.assertIn("up to 15", doc)
        self.assertIn("not pad this section to 15", doc)
        self.assertIn("NPC detail crop", doc)
        lead = doc.split("## Quick Gameplay View", 1)[1].split(
            "## Gameplay Timeline", 1
        )[0]
        image_refs = re.findall(r"history/screenshots/[^\"<\s]+\.png", lead)

        self.assertGreaterEqual(len(image_refs), 15)
        self.assertIn("a35-dev5-spawn-control.png", lead)
        self.assertIn("a35-dev7-effects-131326.png", lead)
        self.assertIn("a35-dev13-npc-crop.png", lead)
        self.assertIn("a35-dev19-npc-detail-crop.png", lead)
        forbidden = (
            "a35-dev6-",
            "a35-dev12-first-frame",
            "a35-dev20-",
            "a35-dev21-",
            "a35-dev24-",
            "a35-dev42-",
            "a35-dev43-",
            "a35-dev44-",
            "a35-dev45-",
            "a35-dev46-",
            "a35-dev47-",
            "a35-dev78-",
            "a35-dev79-",
            "a35-dev82-",
        )
        for image_ref in image_refs:
            for name in forbidden:
                self.assertNotIn(name, image_ref)
            self.assertNotIn("loading-screen", image_ref)
            self.assertNotIn("loading-replay", image_ref)
            self.assertNotIn("loading-physical", image_ref)

    def test_gameplay_sections_are_capped_and_do_not_use_loading_frames(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        timeline = doc.split("## Gameplay Timeline", 1)[1].split(
            "## One Loading-Screen Regression Reference", 1
        )[0]
        sections = re.split(r"\n### ", timeline)

        for section in sections:
            if not section.strip():
                continue
            image_refs = re.findall(r"history/screenshots/[^\"<\s]+\.png", section)
            self.assertLessEqual(len(image_refs), 15, section.splitlines()[0])
            for image_ref in image_refs:
                self.assertNotIn("loading-screen", image_ref)
                self.assertNotIn("loading-replay", image_ref)
                self.assertNotIn("loading-physical", image_ref)

        for diagnostic_build in (
            "A3.5-dev6",
            "A3.5-dev12",
            "A3.5-dev20",
            "A3.5-dev42",
            "A3.5-dev78",
            "A3.5-dev79",
        ):
            self.assertNotIn(f"### {diagnostic_build}", timeline)

    def test_recovered_builds_have_expected_gameplay_counts(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        expected_counts = {
            "A3.1": 4,
            "A3.5-dev5": 12,
            "A3.5-dev7": 7,
            "A3.5-dev13": 5,
            "A3.5-dev16": 6,
            "A3.5-dev17": 6,
            "A3.5-dev18": 6,
            "A3.5-dev19": 5,
            "A3.5-dev87": 6,
        }
        gameplay_timeline = doc.split("## Gameplay Timeline", 1)[1].split(
            "## One Loading-Screen Regression Reference", 1
        )[0]

        for build, expected in expected_counts.items():
            section = gameplay_timeline.split(f"### {build}", 1)[1].split("\n### ", 1)[0]
            image_refs = re.findall(r"history/screenshots/[^\"<\s]+\.png", section)
            self.assertEqual(len(image_refs), expected, build)

    def test_timeline_declares_boundary_inventory_and_single_loading_reference(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        normalized = " ".join(doc.split())

        self.assertIn("Each build may include up to 15 displayed screenshots", doc)
        self.assertIn("One historical loading-screen frame is displayed as a regression reference", doc)
        self.assertIn("VitaShell FTP pull", doc)
        self.assertIn("These images are historical evidence", doc)
        self.assertIn("They do not make dev82 physically accepted", normalized)
        self.assertIn("## Diagnostic-Only Screenshot Inventory", doc)
        self.assertIn("## Builds With No Local Or Vita-Pulled Screenshot File", doc)
        self.assertIn("## Complete Gallery Manifest", doc)
        self.assertIn("Do not fabricate images from logs", normalized)
        loading_section = doc.split("## One Loading-Screen Regression Reference", 1)[1].split(
            "## A3.5-dev82 — Returned Physical Diagnostic Evidence", 1
        )[0]
        self.assertEqual(
            len(re.findall(r"<img src=\"history/screenshots/", loading_section)),
            1,
        )
        missing = doc.split("## Builds With No Local Or Vita-Pulled Screenshot File", 1)[1].split(
            "## Complete Gallery Manifest", 1
        )[0]
        for recovered in ("A3.5-dev6", "A3.5-dev19", "A3.5-dev20", "A3.5-dev42", "A3.5-dev79"):
            self.assertNotIn(recovered, missing)

    def test_dev82_returned_diagnostics_are_visibly_displayed(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        section = doc.split("## A3.5-dev82 — Returned Physical Diagnostic Evidence", 1)[1].split(
            "## A3.5-dev86 — Returned Physical Frontend Diagnostic Evidence", 1
        )[0]
        expected = (
            "a35-dev82-vita-original-loading-screen-t54494725.png",
            "a35-dev82-vita-original-loading-screen-t67280479.png",
            "a35-dev82-vita-first-interactive-frame-t64590857.png",
            "a35-dev82-vita-first-interactive-frame-t88041059.png",
        )

        self.assertIn("All four raw capture records returned for Dev82", section)
        self.assertIn("three distinct rendered images", section)
        self.assertIn("byte-identical to the full-frame loading image", section)
        self.assertIn("must not be presented as gameplay proof", section)
        self.assertEqual(len(re.findall(r'<img src="history/screenshots/', section)), 4)
        for name in expected:
            self.assertIn(f"history/screenshots/{name}", section)
        self.assertEqual(
            (SCREENSHOT_DIR / expected[0]).read_bytes(),
            (SCREENSHOT_DIR / expected[2]).read_bytes(),
        )

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("historical screenshot timeline", readme)
        self.assertNotIn("### A3.5-dev82 — Returned Physical Diagnostic Frames", readme)

    def test_dev86_returned_frontend_diagnostic_is_visibly_displayed(self):
        timeline = TIMELINE.read_text(encoding="utf-8")
        filename = "a35-dev86-vita-original-loading-screen-level-ready-t119137636-annotated.png"
        section = timeline.split(
            "## A3.5-dev86 — Returned Physical Frontend Diagnostic Evidence", 1
        )[1].split("## Diagnostic-Only Screenshot Inventory", 1)[0]

        self.assertIn("exact returned physical capture", section)
        self.assertIn("original WWUI text regions are blank", section)
        self.assertIn(f"history/screenshots/{filename}", section)
        self.assertEqual(len(re.findall(r'<img src="history/screenshots/', section)), 1)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"docs/history/screenshots/{filename}", readme)
        self.assertIn("diagnostic loading frame, not gameplay", readme)

    def test_readme_links_current_gallery_and_dev87_recorder_stills(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("## Visual evidence, honestly presented", readme)
        self.assertIn("historical screenshot timeline", readme)
        self.assertIn("docs/history/screenshots/a35-dev5-walk-manual.png", readme)
        self.assertIn("docs/history/screenshots/a35-dev13-selected-frame.png", readme)
        for name in (
            "a35-dev87-vita-recorder-m00-exterior-npc-t0040s.png",
            "a35-dev87-vita-recorder-m00-warfactory-door-t0080s.png",
            "a35-dev87-vita-recorder-m00-interior-console-t0120s.png",
        ):
            self.assertIn(f"docs/history/screenshots/{name}", readme)
        self.assertIn("not acceptance proof", readme)

    def test_inventory_report_records_vita_appdata_and_gallery_counts(self):
        report = (ROOT / "reports" / "HISTORICAL_EVIDENCE_INVENTORY.md").read_text(
            encoding="utf-8"
        )
        inventory = (ROOT / "reports" / "generated" / "historical_evidence_inventory.json").read_text(
            encoding="utf-8"
        )

        gallery_count = len(list(SCREENSHOT_DIR.glob("*.png")))
        self.assertGreaterEqual(gallery_count, 182)
        self.assertIn(f"GitHub gallery PNGs: {gallery_count}", report)
        self.assertIn("24 runtime logs, 89 capture directories", report)
        self.assertIn("All 89 live Vita capture directories", report)
        self.assertIn("<managed-builder-root>", report)
        self.assertIn("<historical-evidence-root>/Vita Logs", report)
        self.assertIn(f'"gallery_png_count": {gallery_count}', inventory)
        self.assertIn('"vita3k_user_appdata"', inventory)
        self.assertIn('"missing_c_local_builder_root"', inventory)


if __name__ == "__main__":
    unittest.main()
