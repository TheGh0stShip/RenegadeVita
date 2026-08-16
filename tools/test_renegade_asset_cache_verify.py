import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from renegade_asset_cache_key import build_key
from renegade_asset_cache_verify import CACHE_METADATA_NAME, verify_cache


class CacheVerifyTests(unittest.TestCase):
    manifest = {"valid": True, "schema_version": 1, "content_digest": "a" * 64, "file_count": 5}
    options = {"mipmaps": True, "texture_format": "rgba8"}

    def write_valid_cache(self, root: Path) -> None:
        artifact = root / "indexes/m01.txt"
        artifact.parent.mkdir()
        artifact.write_bytes(b"original factory names\n")
        metadata = {
            "schema_version": 1,
            "cache_key": build_key(self.manifest, self.options)["cache_key"],
            "entries": [{"logical_path": "m01.mix", "artifact": "indexes/m01.txt",
                         "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}],
        }
        (root / CACHE_METADATA_NAME).write_text(json.dumps(metadata), encoding="utf-8")

    def test_missing_stale_and_valid_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(verify_cache(root, self.manifest, self.options)["state"], "missing")
            self.write_valid_cache(root)
            self.assertEqual(verify_cache(root, self.manifest, self.options)["state"], "valid")
            self.assertEqual(verify_cache(root, self.manifest, {"mipmaps": False})["state"], "stale")

    def test_corrupt_entry_is_actionable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_valid_cache(root)
            metadata_path = root / CACHE_METADATA_NAME
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["entries"][0]["artifact"] = "../escape.txt"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            result = verify_cache(root, self.manifest, self.options)
            self.assertEqual(result["state"], "corrupt")
            self.assertEqual(result["reasons"], ["cache entry artifact path is unsafe"])

    def test_hash_mismatch_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_valid_cache(root)
            (root / "indexes/m01.txt").write_bytes(b"changed")
            result = verify_cache(root, self.manifest, self.options)
            self.assertEqual(result["state"], "corrupt")
            self.assertEqual(result["entries"][0]["status"], "hash_mismatch")


if __name__ == "__main__":
    unittest.main()
