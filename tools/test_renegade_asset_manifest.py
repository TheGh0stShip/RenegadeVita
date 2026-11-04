import json
import contextlib
import io
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from renegade_asset_manifest import build_manifest
from tools.test_collect_retail_content_baseline import write_mix


class ManifestTests(unittest.TestCase):
    def populate(self, root: pathlib.Path) -> None:
        for name, payload in {"always.dat": b"a", "always2.dat": b"b", "always.dbs": b"c", "M00_Tutorial.mix": b"d"}.items():
            (root / name).write_bytes(payload)

    def test_required_files_and_deterministic_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            first, second = build_manifest(root, 'm00'), build_manifest(root, 'm00')
            self.assertTrue(first["valid"])
            self.assertEqual(first["content_digest"], second["content_digest"])
            self.assertEqual(first["file_count"], 4)
            self.assertEqual(first["files"][3]["kind"], "mission_mix")

    def test_missing_and_case_conflict_are_actionable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            (root / "ALWAYS.DAT").write_bytes(b"different")
            result = build_manifest(root, 'm00')
            self.assertFalse(result["valid"])
            self.assertEqual(result["case_conflicts"][0]["normalized_path"], "always.dat")

    def test_optional_always3_is_not_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            self.assertEqual(build_manifest(root, 'm00')["optional_present"], [])
            (root / "always3.dat").write_bytes(b"optional")
            self.assertEqual(build_manifest(root, 'm00')["optional_present"], ["always3.dat"])

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

    def test_default_campaign_derives_missing_map_and_movie_from_retail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / 'Data'
            root.mkdir()
            self.populate(root)
            write_mix(root / 'always.dat', [('campaign.ini',
                      b'[Campaign]\n1=Level M09.mix\n2=Movie Data\\Movies\\Clip.bik Unlock\n3=Score\n')])
            result = build_manifest(root)
            self.assertEqual(result['required_profile'], 'campaign')
            self.assertFalse(result['valid'])
            self.assertEqual(result['required_missing'], ['m09.mix', 'movies/clip.bik'])
            self.assertTrue(build_manifest(root, 'm00')['valid'], 'explicit demo profile retains its limited scope')
            (root / 'M09.mix').write_bytes(b'fixture map availability only')
            (root / 'Movies').mkdir()
            (root / 'Movies/Clip.BIK').write_bytes(b'fixture movie availability only')
            complete = build_manifest(root)
            self.assertTrue(complete['valid'])
            self.assertFalse(complete['gameplay_parity_verified'])
            self.assertEqual(complete['profile_derivation']['level_entries'], 1)

    def test_incomplete_or_unknown_campaign_flow_cannot_fall_back_to_tutorial_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            for flow in (b'[Campaign]\n', b'[Campaign]\n1=UnknownNewDirective\n',
                         b'[Campaign]\n1=Level X.mix\n1=Score\n'):
                write_mix(root / 'always.dat', [('campaign.ini', flow)])
                report = build_manifest(root)
                self.assertFalse(report['valid'])
                self.assertTrue(report['profile_errors'])
            write_mix(root / 'always.dat', [('campaign.ini', b'[Campaign]\n1=Level X.mix\n')])
            (root / 'X.mix').touch()
            self.assertTrue(build_manifest(root)['valid'])
            (root / 'campaign.ini').write_text('[Campaign]\n1=Level Y.mix\n')
            result = build_manifest(root)
            self.assertFalse(result['valid'])
            self.assertIn('loose campaign override', result['profile_errors'][0])

    def test_repair_rejects_missing_campaign_content_before_any_copy(self):
        from tools.repair_vita3k_retail import main
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            source = base / 'source/Data'
            destination = base / 'vfs/ux0/data/renegade/retail/Data'
            source.mkdir(parents=True)
            destination.mkdir(parents=True)
            self.populate(source)
            write_mix(source / 'always.dat', [('campaign.ini', b'[Campaign]\n1=Level M09.mix\n')])
            original = b'unchanged destination sentinel'
            (destination / 'always.dat').write_bytes(original)
            args = ['repair', '--source', str(source), '--destination', str(destination),
                    '--evidence', str(base / 'evidence')]
            with patch('sys.argv', args), self.assertRaisesRegex(SystemExit, 'm09.mix'):
                main()
            self.assertEqual((destination / 'always.dat').read_bytes(), original)
            self.assertFalse((base / 'evidence/backups').exists())

    def test_manifest_cli_cannot_overwrite_retail_input(self):
        from renegade_asset_manifest import main
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.populate(root)
            original = (root / 'always.dat').read_bytes()
            args = ['manifest', str(root), '--profile', 'm00', '--output', str(root / 'always.dat')]
            with patch('sys.argv', args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main()
            self.assertEqual((root / 'always.dat').read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
