"""Publication checks must reject stale status without pinning historical prose."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.verify_public_docs import DOCUMENTS, LICENSE_FILES, REQUIRED_TEXT, validate


class PublicDocsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in DOCUMENTS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(REQUIRED_TEXT.get(relative, ())) +
                            "\nA3.5-dev195\n", encoding="utf-8")
        source_root = Path(__file__).resolve().parents[1]
        for relative in LICENSE_FILES:
            (self.root / relative).write_bytes((source_root / relative).read_bytes())
        (self.root / "reports").mkdir()
        (self.root / "reports/candidate.md").write_text("Evidence\n", encoding="utf-8")
        self.state = {"public_candidate": {
            "label": "A3.5-dev195", "report": "reports/candidate.md"}}
        self.write_state()

    def write_state(self):
        (self.root / "reports/BUILD_STATE.json").write_text(
            json.dumps(self.state), encoding="utf-8")

    def test_current_docs_pass_without_obsolete_candidate_tokens(self):
        self.assertEqual(validate(self.root), [])

    def test_stale_current_status_fails(self):
        self.state["public_candidate"]["label"] = "A3.5-dev196"
        self.write_state()
        failures = validate(self.root)
        self.assertTrue(any("README.md: missing current" in item for item in failures))
        self.assertTrue(any("CURRENT_STATUS.md: missing current" in item for item in failures))

    def test_stale_install_and_build_guides_fail(self):
        for relative in ("docs/INSTALLING.md", "docs/BUILDING.md"):
            (self.root / relative).write_text("Old candidate\n", encoding="utf-8")
        failures = validate(self.root)
        self.assertTrue(any("docs/INSTALLING.md: missing current" in item for item in failures))
        self.assertTrue(any("docs/BUILDING.md: missing current" in item for item in failures))

    def test_reusing_published_label_in_build_example_fails(self):
        with (self.root / "docs/QUICKSTART.md").open("a", encoding="utf-8") as document:
            document.write("RENEGADE_CANDIDATE_LABEL=A3.5-dev195 bash ./tools/build.sh\n")
        self.assertTrue(any("build example reuses" in item for item in validate(self.root)))

    def test_missing_report_fails(self):
        (self.root / "reports/candidate.md").unlink()
        self.assertTrue(any("report is missing" in item for item in validate(self.root)))

    def test_missing_full_license_fails(self):
        (self.root / "LICENSE").unlink()
        self.assertTrue(any("missing complete license" in item for item in validate(self.root)))

    def test_changed_ea_terms_fail(self):
        (self.root / "EA-SOURCE-LICENSE.md").write_text("GPLv3\n", encoding="utf-8")
        self.assertTrue(any("license text differs" in item for item in validate(self.root)))

    def test_invalid_candidate_fails(self):
        self.state["public_candidate"]["label"] = "latest"
        self.write_state()
        self.assertTrue(any("invalid public candidate" in item for item in validate(self.root)))

    def test_missing_local_link_fails(self):
        with (self.root / "README.md").open("a", encoding="utf-8") as document:
            document.write("[Missing](docs/missing.md)\n")
        self.assertTrue(any("missing linked path" in item for item in validate(self.root)))

    def test_escaping_link_fails(self):
        with (self.root / "README.md").open("a", encoding="utf-8") as document:
            document.write("[Private](../private.md)\n")
        self.assertTrue(any("link escapes" in item for item in validate(self.root)))


if __name__ == "__main__":
    unittest.main()
