import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "verify_candidate_provenance.py"
OUTPUT_BASENAME = "{candidate}-CANDIDATE-PROVENANCE"


REQUIRED_FILES = {
    "vpk": "RenegadeVita-{candidate}.vpk",
    "elf": "RenegadeVita-{candidate}.elf",
    "map": "RenegadeVita-{candidate}.map",
    "elf_header": "RenegadeVita-{candidate}.elf-header.txt",
    "symbols": "RenegadeVita-{candidate}.symbols.txt",
    "vpk_contents": "RenegadeVita-{candidate}.vpk-contents.txt",
    "build_report": "{candidate}-BUILD_REPORT.txt",
    "host_log": "{candidate}-HOST-VALIDATION.log",
    "sha_manifest": "{candidate}-SHA256SUMS.txt",
}


def run_tool(dist: Path, candidate: str) -> tuple[Path, Path]:
    command = [sys.executable, str(TOOL), str(dist), candidate]
    subprocess.run(command, check=False, capture_output=True, text=True)
    json_path = dist / f"{OUTPUT_BASENAME.format(candidate=candidate)}.json"
    md_path = dist / f"{OUTPUT_BASENAME.format(candidate=candidate)}.md"
    return json_path, md_path


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class CandidateProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.candidate = "A3.5-dev2-test"

    def make_fixture(self, dist: Path, vpk_contents: list[str] | None = None,
                     manifest_entries: dict[str, str] | None = None) -> None:
        if vpk_contents is None:
            vpk_contents = ["eboot.bin", "sce_sys/param.sfo"]
        for required in REQUIRED_FILES.values():
            path = dist / required.format(candidate=self.candidate)
            if "{candidate}" not in required:
                continue
            if "SHA256SUMS" in path.name:
                continue
            path.write_bytes(f"payload-{path.name}".encode("utf-8"))
        (dist / REQUIRED_FILES["vpk_contents"].format(candidate=self.candidate)).write_text(
            "\n".join(vpk_contents) + "\n", encoding="utf-8")

        if manifest_entries is None:
            manifest_entries = {
                path.format(candidate=self.candidate): hashlib.sha256(
                    (dist / path.format(candidate=self.candidate)).read_bytes()
                ).hexdigest()
                for path in REQUIRED_FILES.values()
                if "SHA256SUMS" not in path
            }
            # include manifest file checks for itself after we create it
        manifest_lines = [f"{digest}  {path}" for path, digest in sorted(manifest_entries.items())]
        manifest_path = dist / REQUIRED_FILES["sha_manifest"].format(candidate=self.candidate)
        manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    def status_for_artifact(self, result: dict[str, object], artifact: str) -> str:
        for check in result["checks"]:
            if check.get("artifact") == artifact:
                return str(check["status"])
        return "MISSING"

    def test_valid_evidence_is_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            json_path, _ = run_tool(root, self.candidate)
            result = read_json(json_path)
            self.assertEqual(result["overall_status"], "PASS")
            self.assertEqual(self.status_for_artifact(result, "vpk"), "PASS")
            self.assertEqual(self.status_for_artifact(result, "vpk_contents"), "PASS")
            self.assertEqual(result["manifest"]["status"], "PASS")

    def test_hash_mismatch_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            elf = root / REQUIRED_FILES["elf"].format(candidate=self.candidate)
            elf.write_bytes(b"corrupt")
            manifest_path = root / REQUIRED_FILES["sha_manifest"].format(candidate=self.candidate)
            manifest_lines = manifest_path.read_text().splitlines()
            entries: dict[str, str] = {}
            for entry in manifest_lines:
                digest, path = entry.split("  ", 1)
                if path == elf.name:
                    continue
                entries[path] = digest
            entries[elf.name] = hashlib.sha256(b"legacy").hexdigest()
            manifest_path.write_text(
                "\n".join(f"{digest}  {path}" for path, digest in sorted(entries.items())) + "\n",
                encoding="utf-8",
            )
            json_path, _ = run_tool(root, self.candidate)
            result = read_json(json_path)
            self.assertEqual(self.status_for_artifact(result, "elf"), "FAIL")
            self.assertEqual(result["overall_status"], "FAIL")

    def test_path_traversal_in_manifest_is_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            manifest_path = root / REQUIRED_FILES["sha_manifest"].format(candidate=self.candidate)
            base = manifest_path.read_text()
            traversal = f'{"0" * 64}  ../outside.bin\n'
            manifest_path.write_text(base + traversal, encoding="utf-8")
            json_path, _ = run_tool(root, self.candidate)
            result = read_json(json_path)
            manifest_failures = [
                entry for entry in result["manifest"]["entries"]
                if str(entry.get("status", "")).upper() == "FAIL" and str(entry.get("path", "")).endswith("outside.bin")
            ]
            self.assertEqual(len(manifest_failures), 1)
            self.assertEqual(result["overall_status"], "FAIL")

    def test_missing_required_file_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            (root / REQUIRED_FILES["symbols"].format(candidate=self.candidate)).unlink()
            json_path, _ = run_tool(root, self.candidate)
            result = read_json(json_path)
            self.assertEqual(self.status_for_artifact(result, "symbols"), "MISSING")
            self.assertEqual(result["overall_status"], "FAIL")

    def test_unexpected_vpk_contents_is_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root, vpk_contents=["eboot.bin", "sce_sys/param.sfo", "retail/assets.pak"])
            json_path, _ = run_tool(root, self.candidate)
            result = read_json(json_path)
            self.assertEqual(self.status_for_artifact(result, "vpk_contents_report"), "FAIL")
            self.assertEqual(result["overall_status"], "FAIL")

    def test_byte_identical_reruns(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            self.make_fixture(dist)
            json1_path, md1_path = run_tool(dist, self.candidate)

            json1 = json1_path.read_bytes()
            md1 = md1_path.read_bytes()

            run_tool(dist, self.candidate)
            json2 = json1_path.read_bytes()
            md2 = md1_path.read_bytes()

        self.assertEqual(json1, json2)
        self.assertEqual(md1, md2)

if __name__ == "__main__":
    unittest.main()
