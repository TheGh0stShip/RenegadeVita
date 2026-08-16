#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from renegade_asset_cache_key import build_key
from renegade_asset_cache_verify import CACHE_METADATA_NAME
from renegade_asset_cache_audit import audit_cache


SCRIPT = Path(__file__).with_name("renegade_asset_cache_audit.py")


def run_audit(cache_root: Path, manifest: Path, options: Path, artifact: str, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(cache_root),
            str(manifest),
            "--options",
            str(options),
            "--index-artifact",
            artifact,
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )


class CacheAuditTests(unittest.TestCase):
    manifest = {
        "valid": True,
        "schema_version": 1,
        "content_digest": "a" * 64,
        "file_count": 5,
    }
    options = {"cache_schema": "renegade-vita-mix-index-v1"}

    def make_manifest(self, path: Path, *, content_digest: str = "a" * 64) -> Path:
        payload = dict(self.manifest, content_digest=content_digest)
        path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        return path

    def make_options(self, path: Path, *, mipmaps: bool | None = None) -> Path:
        payload = dict(self.options)
        if mipmaps is not None:
            payload["mipmaps"] = mipmaps
        path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        return path

    def make_artifact(self, root: Path, name: str, *, payload: bytes = b"index", size: int | None = None) -> Path:
        artifact = root / name
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(payload if size is None else payload[:size].ljust(size, b"0"))
        return artifact

    def make_metadata(
        self,
        root: Path,
        artifact_name: str,
        *,
        digest: str | None = None,
        size: int | None = None,
    ) -> Path:
        artifact = root / artifact_name
        if artifact.exists():
            artifact_bytes = artifact.read_bytes()
            digest_value = digest if digest is not None else hashlib.sha256(artifact_bytes).hexdigest()
            size_value = artifact.stat().st_size if size is None else size
        else:
            digest_value = digest if digest is not None else ("a" * 64)
            size_value = 0 if size is None else size
        metadata = {
            "schema_version": 1,
            "cache_key": build_key(self.manifest, self.options)["cache_key"],
            "entries": [
                {
                    "logical_path": "m01.mix",
                    "artifact": artifact_name,
                    "sha256": digest_value,
                    "size": size_value,
                },
            ],
        }
        (root / CACHE_METADATA_NAME).write_text(json.dumps(metadata, sort_keys=True, indent=2), encoding="utf-8")
        return root / CACHE_METADATA_NAME

    def test_valid_cache_is_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_manifest(root / "manifest.json")
            options = self.make_options(root / "options.json")
            artifact = self.make_artifact(root, "indexes/m01.txt")
            self.make_metadata(root, "indexes/m01.txt")
            output = root / "audit.json"
            result = run_audit(root, manifest, options, "indexes/m01.txt", output)
            self.assertEqual(result.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["state"], "valid")
            self.assertEqual(report["artifact"]["status"], "valid")

    def test_stale_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_manifest(root / "manifest.json")
            options = self.make_options(root / "options.json")
            self.make_artifact(root, "indexes/m01.txt")
            self.make_metadata(root, "indexes/m01.txt")
            stale_manifest = self.make_manifest(root / "stale-manifest.json", content_digest="b" * 64)
            output = root / "audit.json"
            result = run_audit(root, stale_manifest, options, "indexes/m01.txt", output)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["state"], "stale")

    def test_changed_options(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_manifest(root / "manifest.json")
            options = self.make_options(root / "options.json")
            self.make_artifact(root, "indexes/m01.txt")
            self.make_metadata(root, "indexes/m01.txt")
            changed_options = self.make_options(root / "options-changed.json", mipmaps=False)
            output = root / "audit.json"
            result = run_audit(root, manifest, changed_options, "indexes/m01.txt", output)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["state"], "stale")

    def test_missing_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_manifest(root / "manifest.json")
            options = self.make_options(root / "options.json")
            # Declare an index artifact but do not write its payload file.
            self.make_metadata(root, "indexes/missing.txt")
            output = root / "audit.json"
            result = run_audit(root, manifest, options, "indexes/missing.txt", output)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["state"], "missing")
            self.assertEqual(report["artifact"]["status"], "missing")

    def test_corrupt_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_manifest(root / "manifest.json")
            options = self.make_options(root / "options.json")
            self.make_artifact(root, "indexes/m01.txt", payload=b"good")
            self.make_metadata(root, "indexes/m01.txt", digest="b" * 64)
            output = root / "audit.json"
            result = run_audit(root, manifest, options, "indexes/m01.txt", output)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["state"], "corrupt")
            self.assertEqual(report["artifact"]["status"], "corrupt")

    def test_unsafe_artifact_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_manifest(root / "manifest.json")
            options = self.make_options(root / "options.json")
            (root / "indexes").mkdir()
            (root / "indexes" / "m01.txt").write_text("index", encoding="utf-8")
            bad_metadata = {
                "schema_version": 1,
                "cache_key": build_key(self.manifest, self.options)["cache_key"],
                "entries": [
                    {
                        "logical_path": "m01.mix",
                        "artifact": "../unsafe.txt",
                        "sha256": "a" * 64,
                        "size": 5,
                    }
                ],
            }
            (root / CACHE_METADATA_NAME).write_text(json.dumps(bad_metadata, sort_keys=True, indent=2), encoding="utf-8")
            output = root / "audit.json"
            result = run_audit(root, manifest, options, "../unsafe.txt", output)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["state"], "unsafe")
            self.assertEqual(report["artifact"]["status"], "unsafe")

    def test_deterministic_rerun(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_manifest(root / "manifest.json")
            options = self.make_options(root / "options.json")
            self.make_artifact(root, "indexes/m01.txt")
            self.make_metadata(root, "indexes/m01.txt")
            output_one = root / "audit-1.json"
            output_two = root / "audit-2.json"
            first = run_audit(root, manifest, options, "indexes/m01.txt", output_one)
            second = run_audit(root, manifest, options, "indexes/m01.txt", output_two)
            self.assertEqual(first.returncode, 0)
            self.assertEqual(second.returncode, 0)
            self.assertEqual(output_one.read_bytes(), output_two.read_bytes())

    def test_audit_cache_function_is_deterministic(self):
        manifest = {
            "valid": True,
            "schema_version": 1,
            "content_digest": "a" * 64,
            "file_count": 5,
        }
        options = {"cache_schema": "renegade-vita-mix-index-v1"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_artifact(root, "indexes/m01.txt")
            self.make_metadata(root, "indexes/m01.txt")
            result_one = audit_cache(root, manifest, options, "indexes/m01.txt")
            result_two = audit_cache(root, manifest, options, "indexes/m01.txt")
            self.assertEqual(result_one["state"], "valid")
            self.assertEqual(result_one, result_two)


if __name__ == "__main__":
    unittest.main()
