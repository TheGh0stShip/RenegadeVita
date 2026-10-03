"""Asset-free controls for binding provenance and conservative ID discovery."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.audit_mission_content_bindings import (
    audit_map, constant_branch_code, lookup_rows, main, masked, parameter_fields,
    source_scripts, structural_findings,
)
from tools.test_m13_level_owners import chunk, micro, integer, definition


class MissionContentBindingsTests(unittest.TestCase):
    def source_fixture(self, directory, source):
        root = Path(directory)
        scripts = root / 'upstream/CnC_Renegade/Code/Scripts'
        scripts.mkdir(parents=True)
        (scripts / 'Scripts.dsp').write_text('SOURCE=.\\Used.cpp\nSOURCE=.\\DLLmain.cpp\n')
        (scripts / 'Used.cpp').write_text(source)
        (scripts / 'NotShipped.cpp').write_text('DECLARE_SCRIPT(Unshipped, "") {};')
        return root

    def test_original_project_and_constant_false_blocks_limit_registrations(self):
        source = '''DECLARE_SCRIPT(Used, "Object_ID:int,Misspelled_Name=default:string") {
            Commands->Find_Object(123);
        };
        #if 0
        DECLARE_SCRIPT(Used, "duplicate disabled body") { Commands->Find_Object(456); };
        #endif
        DECLARE_SCRIPT(Orphan, "") { Commands->Find_Object(789); };
        '''
        with tempfile.TemporaryDirectory() as temp:
            rows = source_scripts(self.source_fixture(temp, source))
        self.assertEqual(set(rows), {'used', 'orphan'})
        self.assertEqual(rows['used']['lookups'][0]['id'], 123)
        self.assertNotIn('unshipped', rows)

    def test_comments_strings_and_computed_expressions_are_not_literal_id_calls(self):
        source = '''/* comment\n another line */
DECLARE_SCRIPT(Used, "") {
 Commands->Debug_Message("Commands->Find_Object(999)");
 // Commands->Find_Object(888);
 Commands->Find_Object(777 + variable);
 Commands->Find_Object(123);
};'''
        with tempfile.TemporaryDirectory() as temp:
            rows = source_scripts(self.source_fixture(temp, source))
        self.assertEqual(rows['used']['lookups'], [{'id': 123, 'line': 7}])

    def test_constant_branch_nesting_and_unknown_alternatives(self):
        source = '''#if 0
disabled
#if UNKNOWN
nested_disabled
#endif
#else
enabled
#endif
#if 1
one
#else
not_one
#endif
#ifdef PLATFORM
possible_a
#else
possible_b
#endif
'''
        code = constant_branch_code(masked(source))
        self.assertNotIn('disabled', code)
        self.assertNotIn('not_one', code)
        for token in ('enabled', 'one', 'possible_a', 'possible_b'):
            self.assertIn(token, code)
        self.assertEqual(len(code), len(source))

    def test_unbalanced_conditionals_are_rejected(self):
        for source in ('#if 0\nbody', '#else\nbody', '#endif\n'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                constant_branch_code(source)

    def test_adjacent_descriptor_literals_and_original_spelling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.source_fixture(temp, 'DECLARE_SCRIPT(Used, "Aggessiveness:float," "Take_Cover:float") {};')
            descriptor = source_scripts(root)['used']['descriptor']
        self.assertEqual(parameter_fields(descriptor, '.5,.2'), [
            {'index': 0, 'name': 'Aggessiveness', 'value': '.5'},
            {'index': 1, 'name': 'Take_Cover', 'value': '.2'}])

    def test_actual_values_preserve_empty_slots_and_do_not_invent_defaults(self):
        self.assertEqual(parameter_fields('A=99:int,B=default:string', ''), [])
        self.assertEqual(parameter_fields('A:int,B:string', '1,')[1]['value'], '')
        self.assertEqual([r['value'] for r in parameter_fields('A:string,B:string', '"a,b"')], ['"a', 'b"'])
        self.assertIsNone(parameter_fields(None, 'a'))
        self.assertIsNone(parameter_fields('A:int', None))

    def test_id_namespaces_and_non_discovered_source_leads_are_preserved(self):
        scripts = {'used': {'name': 'Used', 'owner': 'MissionX0.cpp', 'lookups': [{'id': 7, 'line': 1}]},
                   'orphan': {'name': 'Orphan', 'owner': 'MissionX0.cpp', 'lookups': [{'id': 8, 'line': 2}]}}
        rows = lookup_rows(scripts, {'used'}, [{'instance_id': 8}], [{'instance_id': 7}], {'MissionX0.cpp'})
        self.assertEqual(rows[1]['classification'], 'spawner_id_only_not_a_game_object')
        self.assertEqual(rows[0]['classification'], 'serialized_game_object')
        self.assertFalse(rows[0]['script_in_discovered_closure'])

    def test_unknown_bindings_malformed_vectors_and_missing_definitions_remain_findings(self):
        members = {'level.ldd': {'script_binding_issues': [{'kind': 'script_parameter_count_mismatch'}]}}
        defs = {42: {'script_binding_issues': [{'kind': 'script_parameter_count_mismatch'}]}}
        rows = structural_findings(members, {42}, defs, {'unknown'}, {123})
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1]['definition_id'], 42)
        self.assertIn({'kind': 'unknown_shipped_script', 'name': 'unknown'}, rows)

    def test_detailed_receipts_cannot_be_written_to_public_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arguments = ['audit', '--root', str(root), '--data', str(root / 'data'),
                         '--output-directory', str(root / 'reports')]
            with patch('sys.argv', arguments), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 2)
            self.assertFalse((root / 'reports').exists())

    def test_parameter_text_to_preset_to_script_closure_and_unknown_script_control(self):
        source = '''DECLARE_SCRIPT(RootScript, "File:string") {};
DECLARE_SCRIPT(ChildScript, "Target:int") { Commands->Find_Object(77); };
DECLARE_SCRIPT(Orphan, "") { Commands->Find_Object(999); };'''
        for unknown in (False, True):
            with self.subTest(unknown=unknown), tempfile.TemporaryDirectory() as temp:
                root = self.source_fixture(temp, source)
                data = root / 'data'
                data.mkdir()
                for name in ('M13.mix', 'always.dbs', 'always.dat'):
                    (data / name).write_bytes(b'synthetic archive fixture')
                root_body = chunk(627001057, micro(2, b'RootScript\0') + micro(3, b'root.txt\0'))
                child_body = chunk(627001057, micro(2, b'ChildScript\0') + micro(3, b'77\0'))
                database = definition(0x40123, 10, root_body).replace(b'Preset\0', b'Rootxx\0')
                database += definition(0x40123, 20, child_body).replace(b'Preset\0', b'Childx\0')
                obj = chunk(910991407, micro(2, integer(10)) + micro(3, integer(77)))
                archives = {'M13.mix': {'m13.ldd': obj}, 'always.dbs': {'objects.ddb': database},
                            'always.dat': {'root.txt': b'-.5 Create_Real_Object, 1, "Childx"\n' +
                                (b'0 Attach_Script, 1, "NotShipped"\n' if unknown else b'')}}

                class FixtureArchive:
                    def __init__(self, path):
                        self.path = path
                        self.entries = archives[path.name]
                    def read_binary(self, name):
                        return self.entries[name]

                with patch('tools.audit_mission_content_bindings.MixArchive', FixtureArchive), \
                     patch('tools.deep_content_dependencies.MixArchive', FixtureArchive), \
                     patch('tools.audit_mission_content_bindings.reference_fields', return_value={}):
                    result = audit_map(root, data, 'M13.mix')
                self.assertEqual({r['name'] for r in result['discovered_scripts']}, {'RootScript', 'ChildScript'})
                self.assertEqual(result['discovered_definition_count'], 2)
                self.assertEqual(result['discovered_definition_ids'], [10, 20])
                self.assertEqual(result['literal_object_lookups'][0]['classification'], 'serialized_game_object')
                self.assertEqual(result['structural_metadata_gate_passed'], not unknown)
                self.assertEqual(result['summary']['unknown_shipped_scripts'], ['notshipped'] if unknown else [])
                self.assertFalse(result['runtime_or_physical_acceptance'])


if __name__ == '__main__':
    unittest.main()
