import unittest
from renegade_asset_cache_key import build_key

class CacheKeyTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"valid": True, "schema_version": 1, "content_digest": "a" * 64, "file_count": 51}
        self.options = {"texture_format": "rgba8", "mipmaps": True}

    def test_stable_and_sensitive_to_options_and_source(self):
        first = build_key(self.manifest, self.options)
        self.assertEqual(first, build_key(self.manifest, dict(reversed(list(self.options.items())))))
        changed = build_key(self.manifest, {"texture_format": "rgba8", "mipmaps": False})
        self.assertNotEqual(first["cache_key"], changed["cache_key"])
        other = dict(self.manifest, content_digest="b" * 64)
        self.assertNotEqual(first["cache_key"], build_key(other, self.options)["cache_key"])

    def test_invalid_manifest_is_refused(self):
        with self.assertRaises(ValueError):
            build_key(dict(self.manifest, valid=False), self.options)

if __name__ == "__main__":
    unittest.main()
