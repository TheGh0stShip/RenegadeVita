import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
FETCHER = ROOT / "tools" / "fetch_vita_open_source_references.py"
MANIFEST = ROOT / "tools" / "vita_open_source_references.yml"
VITA3K_RUNNER = ROOT / "tools" / "run_vita3k_candidate.py"


def load_fetcher_module():
    spec = importlib.util.spec_from_file_location("fetch_vita_open_source_references", FETCHER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class VitaOpenSourceReferenceTests(unittest.TestCase):
    def test_manifest_is_policy_checked_and_pinned(self):
        module = load_fetcher_module()
        manifest = module.load_manifest(MANIFEST)
        refs = module.validate_manifest(manifest)
        self.assertGreaterEqual(len(refs), 12)
        ids = {ref["id"] for ref in refs}
        for required in {"vitagl", "vita3k", "vita-crashdump", "sokol-audio", "vitasdk-buildscripts"}:
            self.assertIn(required, ids)
        for ref in refs:
            self.assertRegex(ref["commit"], r"^[0-9a-f]{40}$")
            self.assertTrue(ref["sparse_paths"])
            if "GPL-2.0-only" in str(ref["license"]):
                self.assertEqual(ref["license_policy"], "study_only_no_code_copy")
            if "NOASSERTION" in str(ref["license"]):
                self.assertTrue(ref["license_policy"].startswith("study_only_"))

    def test_manifest_keeps_external_sources_out_of_tree(self):
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["generated_policy"], "external_reference_cache_only")
        for ref in data["references"]:
            plan = ref["reuse_plan"].lower()
            forbidden = ref["license_policy"].startswith("study_only")
            if forbidden:
                self.assertTrue(
                    "no source copy" in plan
                    or "no implementation import" in plan
                    or "no code copy" in plan
                    or "reference only" in plan
                )

    def test_reference_fetcher_dry_run_writes_report(self):
        with tempfile.TemporaryDirectory() as tempdir:
            report = pathlib.Path(tempdir) / "report.json"
            completed = subprocess.run(
                [
                    "python3",
                    str(FETCHER),
                    "--dry-run",
                    "--id",
                    "vitagl",
                    "--id",
                    "vita3k",
                    "--report",
                    str(report),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertIn('"references": 2', completed.stdout)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload["external_sources_imported_to_repo"])
            self.assertEqual([item["status"] for item in payload["references"]], ["PLANNED_DRY_RUN", "PLANNED_DRY_RUN"])

    def test_reference_fetcher_counts_materialized_sparse_files(self):
        source = FETCHER.read_text(encoding="utf-8")
        self.assertIn('"ls-files", "-t"', source)
        self.assertIn('not line.startswith("S ")', source)
        self.assertIn("sparse path(s) did not materialize", source)

    def test_vita3k_runner_dry_run_records_non_physical_evidence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            vpk = pathlib.Path(tempdir) / "candidate.vpk"
            vpk.write_bytes(b"not-a-real-vpk-but-good-enough-for-runner-dry-run")
            evidence = pathlib.Path(tempdir) / "evidence"
            completed = subprocess.run(
                [
                    "python3",
                    str(VITA3K_RUNNER),
                    "--dry-run",
                    "--vpk",
                    str(vpk),
                    "--candidate",
                    "A3.5-test",
                    "--evidence-root",
                    str(evidence),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            receipt_path = pathlib.Path(json.loads(completed.stdout)["evidence"]) / "vita3k-runner-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertFalse(receipt["physical_acceptance"])
            self.assertEqual(receipt["command"][-1], str(vpk.resolve()))
            self.assertIn("--console", receipt["command"])


if __name__ == "__main__":
    unittest.main()
