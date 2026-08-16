import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("renegade_asset_manifest_delta.py")


def manifest_digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write_manifest(path: Path, *, profile="m00", required_files=None, required_missing=None, files=None):
    if files is None:
        files = []
    if required_files is None:
        required_files = ["always.dat"]
    if required_missing is None:
        required_missing = []
    payload = {
        "schema_version": 1,
        "required_profile": profile,
        "required_files": required_files,
        "required_missing": required_missing,
        "optional_present": [],
        "file_count": len(files),
        "files": files,
        "content_digest": manifest_digest(files),
        "valid": len(required_missing) == 0,
    }
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")


def entry(path, sha):
    return {"path": path, "normalized_path": path.lower(), "size": 4, "sha256": sha, "kind": "dat"}


def run_delta(before: Path, after: Path, json_output: Path, markdown_output: Path):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(before),
            str(after),
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
        ],
        capture_output=True,
        text=True,
    )


class ManifestDeltaTests(unittest.TestCase):
    def test_equal_manifests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = root / "before.json"
            after = root / "after.json"
            entries = [entry("always.dat", "a" * 64)]
            write_manifest(before, files=entries)
            write_manifest(after, files=entries)
            out_json = root / "out.json"
            out_md = root / "out.md"
            result = run_delta(before, after, out_json, out_md)
            self.assertEqual(result.returncode, 0)
            delta = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(delta["summary"]["added"], 0)
            self.assertEqual(delta["summary"]["removed"], 0)
            self.assertEqual(delta["summary"]["changed"], 0)
            self.assertEqual(delta["summary"]["case_conflicts"], 0)
            self.assertIn("- None", out_md.read_text(encoding="utf-8"))

    def test_added_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = root / "before.json"
            after = root / "after.json"
            write_manifest(before, files=[entry("always.dat", "a" * 64)])
            write_manifest(after, files=[entry("always.dat", "a" * 64), entry("m01.mix", "b" * 64)])
            out_json = root / "out.json"
            out_md = root / "out.md"
            result = run_delta(before, after, out_json, out_md)
            self.assertEqual(result.returncode, 0)
            delta = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(delta["summary"]["added"], 1)
            self.assertEqual(delta["added"][0]["normalized_path"], "m01.mix")

    def test_changed_hash_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = root / "before.json"
            after = root / "after.json"
            digest_before = "a" * 64
            digest_after = "b" * 64
            write_manifest(before, files=[entry("always.dat", digest_before)])
            write_manifest(after, files=[entry("always.dat", digest_after)])
            out_json = root / "out.json"
            out_md = root / "out.md"
            result = run_delta(before, after, out_json, out_md)
            self.assertEqual(result.returncode, 0)
            delta = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(delta["summary"]["changed"], 1)
            self.assertEqual(delta["changed"][0]["before"]["sha256"], digest_before)
            self.assertEqual(delta["changed"][0]["after"]["sha256"], digest_after)

    def test_case_conflict_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = root / "before.json"
            after = root / "after.json"
            write_manifest(before, files=[{"path": "ALWAYS.DAT", "normalized_path": "always.dat", "size": 4, "sha256": "a" * 64, "kind": "dat"}])
            write_manifest(after, files=[entry("always.dat", "a" * 64)])
            out_json = root / "out.json"
            out_md = root / "out.md"
            result = run_delta(before, after, out_json, out_md)
            self.assertEqual(result.returncode, 0)
            delta = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(delta["summary"]["case_conflicts"], 1)
            self.assertEqual(delta["case_conflicts"][0]["before_path"], "ALWAYS.DAT")
            self.assertEqual(delta["case_conflicts"][0]["after_path"], "always.dat")

    def test_malformed_schema_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = root / "before.json"
            after = root / "after.json"
            write_manifest(before, files=[entry("always.dat", "a" * 64)], required_files=["always.dat"])
            write_manifest(after, files=[entry("always.dat", "a" * 64)], required_files=["always.dat"])
            # Unknown schema version must be rejected.
            payload = json.loads(after.read_text(encoding="utf-8"))
            payload["schema_version"] = 2
            after.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
            out_json = root / "out.json"
            out_md = root / "out.md"
            result = run_delta(before, after, out_json, out_md)
            self.assertNotEqual(result.returncode, 0)

    def test_profile_required_input_change_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = root / "before.json"
            after = root / "after.json"
            write_manifest(before, profile="m00", required_files=["always.dat"], files=[entry("always.dat", "a" * 64)])
            write_manifest(
                after,
                profile="city",
                required_files=["always.dat", "c&c_city.mix"],
                required_missing=["m01.mix"],
                files=[entry("always.dat", "a" * 64)],
            )
            out_json = root / "out.json"
            out_md = root / "out.md"
            result = run_delta(before, after, out_json, out_md)
            self.assertEqual(result.returncode, 0)
            delta = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(delta["before"]["required_profile"], "m00")
            self.assertEqual(delta["after"]["required_profile"], "city")
            self.assertEqual(delta["profile_required_input_changes"]["required_files_added"], ["c&c_city.mix"])
            self.assertEqual(delta["profile_required_input_changes"]["required_missing_added"], ["m01.mix"])

    def test_byte_identical_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = root / "before.json"
            after = root / "after.json"
            shared = [entry("always.dat", "a" * 64)]
            write_manifest(before, files=shared)
            write_manifest(after, files=shared)
            out_json_1 = root / "out1.json"
            out_md_1 = root / "out1.md"
            out_json_2 = root / "out2.json"
            out_md_2 = root / "out2.md"
            first = run_delta(before, after, out_json_1, out_md_1)
            second = run_delta(before, after, out_json_2, out_md_2)
            self.assertEqual(first.returncode, 0)
            self.assertEqual(second.returncode, 0)
            self.assertEqual(out_json_1.read_bytes(), out_json_2.read_bytes())
            self.assertEqual(out_md_1.read_bytes(), out_md_2.read_bytes())


if __name__ == "__main__":
    unittest.main()
