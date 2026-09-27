import re
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "docs" / "HISTORICAL_SCREENSHOT_TIMELINE.md"
SCREENSHOT_DIR = ROOT / "docs" / "history" / "screenshots"


class HistoricalScreenshotTimelineContract(unittest.TestCase):
    def test_every_audited_build_has_a_manifest_entry(self):
        coverage = json.loads((ROOT / "docs/history/screenshot-coverage.json").read_text())
        doc = TIMELINE.read_text(encoding="utf-8")
        builds = {int(build) for build in coverage["candidate_file_counts_by_build"]}
        manifest = doc.split("## Complete Gallery Manifest", 1)[1]
        index = {int(build) for build in re.findall(r"\| A3\.5-dev(\d+) \|", manifest)}
        self.assertGreaterEqual(len(builds), 108)
        self.assertFalse(builds - index, f"Uncovered builds: {builds - index}")

    def test_recovered_catalog_matches_images(self):
        from tools.generate_historical_screenshot_timeline import recovered_catalog, sha256, png_dimensions

        doc = TIMELINE.read_text(encoding="utf-8")
        for entry in recovered_catalog():
            path = ROOT / "docs" / entry["link"]
            self.assertEqual(entry["sha256"], sha256(path))
            self.assertEqual(tuple(entry["dimensions"]), png_dimensions(path))
            self.assertIn(entry["link"], doc)
            self.assertNotIn("/mnt/", entry["source"])
            self.assertNotIn("/home/", entry["source"])

    def test_regeneration_preserves_published_timeline(self):
        from tools import generate_historical_screenshot_timeline as generator

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "timeline.md"
            with patch.object(generator, "TIMELINE_PATH", target):
                generator.write_timeline()
            self.assertEqual(TIMELINE.read_bytes(), target.read_bytes())

    def test_recent_captures_have_platform_source_and_matching_checksums(self):
        from tools.generate_historical_screenshot_timeline import RECENT_CAPTURES, sha256

        doc = TIMELINE.read_text(encoding="utf-8")
        recent = doc
        self.assertGreaterEqual(len(RECENT_CAPTURES), 13)
        for build, filename, platform, caption, source in RECENT_CAPTURES:
            self.assertIn(f"media/{filename}", recent)
            self.assertIn(platform, recent)
            self.assertIn(source, recent)
            self.assertIn(sha256(ROOT / "docs" / "media" / filename), recent)
        self.assertIn("No Dev207 runtime image", recent)
        self.assertNotIn("Dev134 is the current", doc)

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
            "## Screenshot Timeline", 1
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

    def test_chronological_sections_use_original_thumbnail_layout(self):
        doc = TIMELINE.read_text(encoding="utf-8")
        timeline = doc.split("## Screenshot Timeline", 1)[1].split(
            "## Builds With No Local Or Vita-Pulled Screenshot File", 1
        )[0]
        sections = re.split(r"\n### ", timeline)

        for section in sections:
            if not section.strip():
                continue
            image_refs = re.findall(r'<img src="[^"]+" width="220"', section)
            self.assertGreater(len(image_refs), 0)
            self.assertLessEqual(len(image_refs), 15, section.splitlines()[0])
            self.assertIn("<table>", section)
            self.assertNotIn("<details>", section)
        builds = [int(n) for n in re.findall(r"### A3\.5-dev(\d+)\b", timeline)]
        self.assertEqual(builds, sorted(set(builds)))
        self.assertNotIn("## Recent Build Captures", doc)
        self.assertNotIn("## Recovered Build Gallery", doc)
        self.assertNotIn("Historical captures; platform and visible state are labeled below.", doc)
        self.assertNotIn("<details>", doc)
        self.assertNotIn('width="640"', doc)
        self.assertEqual(re.findall(r"^## (.+)$", doc, re.MULTILINE), [
            "Current Capture Completeness",
            "Quick Gameplay View",
            "Screenshot Timeline",
            "Builds With No Local Or Vita-Pulled Screenshot File",
            "Complete Gallery Manifest",
        ])
        coverage = json.loads((ROOT / "docs/history/screenshot-coverage.json").read_text())
        self.assertEqual(set(builds), {int(n) for n in coverage["candidate_file_counts_by_build"]})

    def test_each_build_keeps_all_capture_types_together(self):
        from tools.generate_historical_screenshot_timeline import additional_captures

        doc = TIMELINE.read_text(encoding="utf-8")
        timeline = doc.split("## Screenshot Timeline", 1)[1].split("## Builds With No Local Or Vita-Pulled Screenshot File", 1)[0]
        seen = set()
        for entry in additional_captures():
            key = (entry["build"], entry["platform"], entry["sha256"])
            if key in seen:
                continue
            seen.add(key)
            section = timeline.split(f"### A3.5-dev{entry['build']} -", 1)[1].split("\n### ", 1)[0]
            self.assertIn(f'<img src="{entry["link"]}"', section)

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
        gameplay_timeline = doc.split("## Screenshot Timeline", 1)[1].split(
            "## Builds With No Local Or Vita-Pulled Screenshot File", 1
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
        self.assertIn("## Builds With No Local Or Vita-Pulled Screenshot File", doc)
        self.assertIn("## Complete Gallery Manifest", doc)
        self.assertIn("Do not fabricate images from logs", normalized)
        loading_section = doc.split("### A3.5-dev78 -", 1)[1].split("\n### ", 1)[0]
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
        section = doc.split("### A3.5-dev82 -", 1)[1].split("\n### ", 1)[0]
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
        section = timeline.split("### A3.5-dev86 -", 1)[1].split("\n### ", 1)[0]

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
