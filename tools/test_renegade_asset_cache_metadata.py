import json
import tempfile
import unittest
from pathlib import Path

from renegade_asset_cache_metadata import build_metadata
from renegade_asset_cache_verify import CACHE_METADATA_NAME, verify_cache


class CacheMetadataTests(unittest.TestCase):
    manifest = {"valid": True, "schema_version": 1, "content_digest": "a" * 64, "file_count": 5}
    options = {"format": "mix-index-v1"}

    def test_metadata_is_sorted_and_verifiable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "indexes").mkdir()
            (root / "indexes/city.txt").write_text("city", encoding="utf-8")
            (root / "indexes/m01.txt").write_text("m01", encoding="utf-8")
            entries = [("m01.mix", "indexes/m01.txt"), ("c&c_city.mix", "indexes/city.txt")]
            metadata = build_metadata(root, self.manifest, self.options, list(reversed(entries)))
            self.assertEqual(metadata["entries"][0]["logical_path"], "c&c_city.mix")
            (root / CACHE_METADATA_NAME).write_text(json.dumps(metadata), encoding="utf-8")
            self.assertEqual(verify_cache(root, self.manifest, self.options)["state"], "valid")

    def test_missing_and_unsafe_artifacts_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                build_metadata(root, self.manifest, self.options, [("m01.mix", "missing.txt")])
            with self.assertRaises(ValueError):
                build_metadata(root, self.manifest, self.options, [("m01.mix", "../escape.txt")])


if __name__ == "__main__":
    unittest.main()
