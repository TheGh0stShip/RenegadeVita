import unittest
import subprocess
import tempfile
from pathlib import Path
from tools.audit_script_parameter_names import audit, parameter_index, scoped_findings

ROOT = Path(__file__).resolve().parents[1]


class ParameterNames(unittest.TestCase):
    def test_scoped_bindings_and_source_closure_are_distinct(self):
        report = {'literal_calls': [{'script': 'Bound', 'finding': True},
                                    {'script': 'Lead', 'finding': True}, {'script': 'Absent', 'finding': True}]}
        binding = {'map': 'test', 'archive_sha256': 'archive', 'objects_ddb_sha256': 'ddb',
                   'definition_overlays': [], 'members': {'test.ldd': {'sha256': 'level'}},
                   'bindings': [{'name': 'BOUND'}, {'name': 'Bound'}], 'discovered_scripts': [{'name': 'Lead'}]}
        result = scoped_findings(report, binding)
        self.assertEqual(len(result['findings']), 2)
        self.assertEqual(result['findings'][0]['authored_binding_count'], 2)
        self.assertFalse(result['findings'][1]['authored_binding_present'])
        self.assertFalse(result['runtime_execution_verified'])
    def test_non_ascii_locale_is_unresolved(self):
        self.assertIsNone(parameter_index('Náme:int', 'náme'))
    def test_original_vector_parser_patch_replays_and_preserves_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'scripts.cpp'
            path.write_bytes((ROOT / 'staging/scripts/scripts.cpp').read_bytes())
            result = subprocess.run(['patch', '--batch', '--forward', '--fuzz=0',
                                     '--no-backup-if-mismatch', '-p1', '-d', directory],
                                    input=(ROOT / 'port/patches/scripts-a35-vector-parameter-initialization.patch').read_bytes(),
                                    capture_output=True, check=True)
            self.assertNotIn(b'offset', result.stdout)
            body = path.read_text().split('Vector3 ScriptImpClass::Get_Vector3_Parameter( int index )', 1)[1].split('\n}', 1)[0]
        self.assertIn('x = 0.0f, y = 0.0f, z = 0.0f', body)
        self.assertIn('::sscanf( Get_Parameter( index ), "%f %f %f", &x, &y, &z );', body)
        self.assertIn('return Vector3( x,y,z );', body)

    def test_empty_descriptor_and_trailing_comma_stop_search(self):
        self.assertEqual(parameter_index('', ''), -1)
        self.assertEqual(parameter_index('A:int,', ''), -1)
        self.assertEqual(parameter_index(',A:int', ''), 0)

    def test_case_ignored_but_underscore_difference_preserved(self):
        self.assertEqual(parameter_index('Killable_by_NotStar=1:int', 'KILLABLE_BY_NOTSTAR'), 0)
        self.assertEqual(parameter_index('Killable_by_NotStar=1:int', 'Killable_ByNotStar'), -1)

    def test_descriptor_limit_is_511_bytes(self):
        self.assertEqual(parameter_index('A' * 510 + ',Hidden:int', 'Hidden'), -1)

    def test_defaults_and_types_are_not_part_of_names(self):
        self.assertEqual(parameter_index(' A =1:int, B :float', 'B'), 1)

    def test_unresolved_descriptor_is_not_missing_parameter(self):
        self.assertIsNone(parameter_index(None, 'Name'))

    def test_numeric_and_variable_calls_are_not_name_mismatches(self):
        row = {'name': 'Synthetic', 'owner': 'Test.cpp', 'descriptor': 'Name:int',
               'body_start_line': 10, 'body': 'Get_Int_Parameter(0); Get_Parameter(variable); Get_Parameter("Name");'}
        report = audit({'synthetic': row})
        self.assertEqual(len(report['literal_calls']), 1)
        self.assertEqual(len(report['non_literal_or_numeric_calls']), 2)
        self.assertFalse(report['literal_calls'][0]['finding'])

    def test_comments_and_quoted_code_are_not_calls(self):
        row = {'name': 'Synthetic', 'owner': 'Test.cpp', 'descriptor': '', 'body_start_line': 1,
               'body': '// Get_Parameter("Bad");\nconst char *s = "Get_Parameter(\\"Bad\\")";'}
        self.assertEqual(audit({'synthetic': row})['literal_calls'], [])
