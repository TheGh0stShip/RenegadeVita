import tempfile
from pathlib import Path
import unittest
from tools.audit_sweep_retail import map_names, summarize


class RetailSweepTests(unittest.TestCase):
    def test_expected_missing_and_non_campaign_inputs_remain_visible(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            for name in ('m01.mix', 'C&C_Field.mix', 'Skirmish00.mix', 'ignore.dat'):
                (data / name).touch()
            names = map_names(data)
            self.assertIn('M09.mix', names)
            self.assertIn('C&C_Field.mix', names)
            self.assertIn('Skirmish00.mix', names)
            self.assertIn('m01.mix', names)
            self.assertNotIn('M01.mix', names)
            self.assertNotIn('ignore.dat', names)

    def test_summary_cross_checks_known_and_unknown_names_without_parameters(self):
        receipt = {'map': 'test.mix', 'archive_sha256': 'a', 'objects_ddb_sha256': 'b',
                   'discovered_scripts': [{'name': 'Present'}, {'name': 'Absent'}],
                   'bindings': [{'name': 'Absent', 'member': 'test.ldd', 'offset': 123,
                                 'parameters': 'private metadata'}],
                   'summary': {'unknown_shipped_scripts': ['Unknown'], 'level_bindings': 4,
                               'all_discovered_bindings': 7, 'structural_findings': 1,
                               'not_located_definition_ids': [123]}}
        link = {'registration_candidates': [{'kind': 'script', 'arguments': ['PRESENT'],
                                            'defined_symbol_matches': [{'address': '1'}]}]}
        row = summarize(receipt, link)
        self.assertEqual(row['script_names_without_defined_registrar'], ['absent', 'unknown'])
        self.assertEqual(row['discovered_script_names'], 3)
        self.assertNotIn('bindings', row)
        self.assertEqual(row['unmatched_serialized_binding_provenance'],
                         [{'name': 'Absent', 'member': 'test.ldd', 'offset': 123}])
        self.assertFalse(row['runtime_registration_verified'])
