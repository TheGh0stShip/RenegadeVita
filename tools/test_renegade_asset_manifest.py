import json
import pathlib
import tempfile
import unittest

from renegade_asset_manifest import build_manifest


class ManifestTests(unittest.TestCase):
    def populate(self, root: pathlib.Path) -> None:
        for name, payload in {"always.dat": b"a", "always2.dat": b"b", "always.dbs": b"c", "M00_Tutorial.mix": b"d"}.items():
            (root / name).write_bytes(payload)

    def test_required_files_and_deterministic_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            first, second = build_manifest(root), build_manifest(root)
            self.assertTrue(first["valid"])
            self.assertEqual(first["content_digest"], second["content_digest"])
            self.assertEqual(first["file_count"], 4)
            self.assertEqual(first["files"][3]["kind"], "mission_mix")

    def test_missing_and_case_conflict_are_actionable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            (root / "ALWAYS.DAT").write_bytes(b"different")
            result = build_manifest(root)
            self.assertFalse(result["valid"])
            self.assertEqual(result["case_conflicts"][0]["normalized_path"], "always.dat")

    def test_optional_always3_is_not_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            self.assertEqual(build_manifest(root)["optional_present"], [])
            (root / "always3.dat").write_bytes(b"optional")
            self.assertEqual(build_manifest(root)["optional_present"], ["always3.dat"])

    def test_scene_profiles_make_missing_archive_actionable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            self.assertEqual(build_manifest(root, "m01")["required_missing"], ["m01.mix"])
            self.assertEqual(build_manifest(root, "city")["required_missing"], ["c&c_city.mix"])
            (root / "M01.mix").write_bytes(b"m01")
            (root / "C&C_City.mix").write_bytes(b"city")
            self.assertTrue(build_manifest(root, "m01")["valid"])
            self.assertTrue(build_manifest(root, "city")["valid"])

    def test_unknown_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            with self.assertRaises(ValueError):
                build_manifest(root, "unknown")


if __name__ == "__main__":
    unittest.main()
