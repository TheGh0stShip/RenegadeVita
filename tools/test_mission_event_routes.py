"""Asset-free counterexamples for incomplete source event/callback analysis."""
import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.audit_mission_event_routes import (
    ROOT, analyze, callbacks, enum_constants, included_constants, main, numeric_constants, owner_constants, possible_integers, source_routes, verify_definition_receipt,
)
from tools.audit_mission_text_routes import assignments
from tools.audit_mission_content_bindings import parameter_fields, source_scripts
from tools.audit_cinematic_slots import trace

CONSTANTS = {'M00_CUSTOM_CINEMATIC_SET_SLOT': '10000', 'M00_SEND_OBJECT_ID': '9035'}


def script(body, name='Fixture', owner='MissionX0.cpp', descriptor=''):
    return {name.lower(): {'name': name, 'body': body, 'owner': owner,
                          'body_start_line': 10, 'descriptor': descriptor}}


def binding(rows=(), discovered=()):
    return {'map': 'M13.mix', 'archive_sha256': 'synthetic hash',
            'bindings': list(rows), 'discovered_scripts': [{'name': name} for name in discovered]}


class MissionEventRoutesTests(unittest.TestCase):
    def test_enum_values_derive_from_initializers_not_misleading_comments(self):
        values = enum_constants('enum { First=9000, Send, /* 1 */ Set=10000, Last };')
        self.assertEqual(values, {'First': '9000', 'Send': '9001', 'Set': '10000', 'Last': '10001'})

    def test_unknown_increment_and_conflicts_are_not_invented(self):
        values = enum_constants('enum { A=unknown(), B, C=7, D }; enum { C=9 };')
        self.assertNotIn('A', values)
        self.assertNotIn('B', values)
        self.assertNotIn('C', values)
        self.assertEqual(values['D'], '8')
        self.assertNotIn('X', enum_constants('enum { X=2147483648, Y };'))
        self.assertNotIn('Disabled', enum_constants('#if 0\nenum { Disabled=10013 };\n#endif'))

    def test_original_toolkit_derived_values_and_explicit_m10_writers(self):
        scripts = source_scripts(ROOT)
        constants, toolkit = owner_constants(ROOT, scripts)
        self.assertEqual({name: int(toolkit[name]) for name in CONSTANTS},
                         {'M00_CUSTOM_CINEMATIC_SET_SLOT': 10000, 'M00_SEND_OBJECT_ID': 9035})
        data = script('void Created(GameObject *obj) { Commands->Send_Custom_Event(obj, obj, M00_CUSTOM_CINEMATIC_SET_SLOT + 3, 123); }')
        rows, _ = source_routes(binding(), [], data, {'MissionX0.cpp': toolkit})
        self.assertEqual(rows[0]['possible_cinematic_slots'], [3])
        self.assertFalse(rows[0]['destination_identity_delivery_and_slot_write_proven'])
        self.assertEqual(constants['Mission10.cpp']['M00_CUSTOM_CINEMATIC_SET_SLOT'], '10000')

    def test_numeric_macro_aliases_and_forward_aliases_without_execution(self):
        values = numeric_constants('#define Alias (Base + 3)\n#define Base 10000\n#define F(x) ((x)+10000)\nenum { Next=Alias+1 };')
        self.assertEqual(values, {'Alias': '10003', 'Base': '10000', 'Next': '10004'})
        self.assertNotIn('F', values)

    def test_macro_cycles_conflicting_branches_and_undef_remain_unknown(self):
        values = numeric_constants('#define Cycle Other\n#define Other Cycle\n#ifdef A\n#define Type 10013\n#else\n#define Type 5\n#endif\n#define Gone 10002\n#undef Gone\n')
        for name in ('Cycle', 'Other', 'Type', 'Gone'):
            self.assertNotIn(name, values)

    def test_original_m13_numeric_macro_type_is_a_non_slot_event(self):
        scripts = source_scripts(ROOT)
        constants, _ = owner_constants(ROOT, scripts)
        self.assertEqual(constants['MissionX0.cpp']['START_SNIPER'], '114')
        self.assertEqual(possible_integers('START_SNIPER', constants['MissionX0.cpp'], {}, []), ({114}, False))
        self.assertEqual(constants['Test_RAD.cpp']['MX0_A02_CUSTOM_TYPE_DEFAULT_STATE_ON'], '207')
        self.assertIn('M01_ADD_OBJECTIVE_POG_JDG', constants['Mission01.cpp'])

    def test_actual_header_graph_handles_alias_cycle_and_refuses_outside_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'First.h').write_text('#include "second.h"\n#define First 10011\n')
            (directory / 'Second.h').write_text('#include "first.h"\n#define Second 10012\n')
            result = included_constants(directory, '#include "FIRST.h"\n#include "../outside.h"\n', {})
            self.assertEqual(result, {'First': '10011', 'Second': '10012'})

    def test_event_type_is_not_confused_with_custom_parameter(self):
        data = script('void Created(GameObject *obj) { Commands->Send_Custom_Event(obj, obj, M00_SEND_OBJECT_ID, 10013); }')
        rows, _ = source_routes(binding(), [], data, {'MissionX0.cpp': CONSTANTS})
        self.assertEqual(rows[0]['possible_event_types'], [9035])
        self.assertEqual(rows[0]['custom_parameter_expression'], '10013')
        self.assertFalse(rows[0]['possible_cinematic_slots'])

    def test_parameters_follow_original_case_underscore_and_absent_rules(self):
        fields = parameter_fields('Type=10013:int, Other:int', '10011junk,-2')
        for expression, expected in [('Get_Int_Parameter("type")', 10011),
                                     ('Get_Int_Parameter(1)', -2),
                                     ('Get_Int_Parameter("Ty_pe")', 0),
                                     ('Get_Int_Parameter(9)', 0)]:
            self.assertEqual(possible_integers(expression, CONSTANTS, {}, fields), ({expected}, False))
        self.assertEqual(possible_integers('Get_Int_Parameter("Type")', CONSTANTS, {}, []), ({0}, False))
        self.assertEqual(possible_integers('Get_Int_Parameter("Type")', CONSTANTS, {}, None), (set(), True))
        self.assertEqual(possible_integers('Get_Int_Parameter("Type")', CONSTANTS, {},
                                          parameter_fields('Type:int', '4294967295')), (set(), True))

    def test_cross_callback_assignment_and_input_shadowing_stay_unresolved(self):
        body = 'void Created(GameObject *obj) { int type=10013; } void Custom(GameObject *obj, int type) { Commands->Send_Custom_Event(obj,obj,type,123); }'
        data = script(body)
        rows, _ = source_routes(binding(), [], data, {'MissionX0.cpp': CONSTANTS})
        self.assertEqual(rows[0]['possible_cinematic_slots'], [13])
        self.assertTrue(rows[0]['unresolved_event_type_possible'])
        self.assertEqual(rows[0]['callback'], 'Custom')
        self.assertFalse(rows[0]['callback_execution_proven'])

    def test_assignments_aliases_and_unsupported_operators_do_not_close_dataflow(self):
        assigned = assignments('int type=alias; int alias=10039; alias=10040;')
        values, unresolved = possible_integers('type', CONSTANTS, assigned, [])
        self.assertEqual(values, {10039, 10040})
        self.assertTrue(unresolved)
        self.assertEqual(possible_integers('type & 65535', CONSTANTS, assigned, []), (set(), True))
        self.assertEqual(possible_integers('cycle', CONSTANTS, assignments('cycle=cycle;'), []), (set(), True))

    def test_each_authored_parameter_context_remains_separate(self):
        body = 'void Killed(GameObject *obj) { int type=Get_Int_Parameter("Type"); Commands->Send_Custom_Event(obj,obj,type,5,1.0f); }'
        data = script(body, descriptor='Type:int')
        rows = [{'name': 'Fixture', 'binding_kind': 'persisted_script',
                 'parameter_fields': parameter_fields('Type:int', value)} for value in ('10002', '9035')]
        routes, _ = source_routes(binding(rows), [], data, {'MissionX0.cpp': CONSTANTS})
        self.assertEqual([row['possible_cinematic_slots'] for row in routes], [[2], []])
        self.assertEqual([row['context_index'] for row in routes], [0, 1])
        self.assertTrue(all(row['unresolved_event_type_possible'] for row in routes))
        self.assertTrue(all(row['delay_expression'] == '1.0f' for row in routes))

    def test_unbound_mission_script_is_retained_and_unselected_other_mission_is_not_claimed(self):
        data = script('void Created(GameObject *obj) { Commands->Send_Custom_Event(obj,obj,10008,1); }')
        data.update(script('void Created(GameObject *obj) { Commands->Send_Custom_Event(obj,obj,10009,1); }',
                           name='Other', owner='Mission10.cpp'))
        rows, _ = source_routes(binding(), [], data, {name: CONSTANTS for name in ('MissionX0.cpp', 'Mission10.cpp')})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['binding_kind'], 'unbound_source_context')
        self.assertEqual(rows[0]['possible_cinematic_slots'], [8])

    def test_slot_window_uses_derived_type_and_32bit_bounds(self):
        data = script('void Created(GameObject *obj) { Commands->Send_Custom_Event(obj,obj,10039,1); Commands->Send_Custom_Event(obj,obj,10040,1); Commands->Send_Custom_Event(obj,obj,2147483648,1); }')
        rows, _ = source_routes(binding(), [], data, {'MissionX0.cpp': CONSTANTS})
        self.assertEqual([row['possible_cinematic_slots'] for row in rows], [[39], [], []])
        self.assertTrue(rows[-1]['unresolved_event_type_possible'])

    def test_caller_target_assignment_does_not_prove_fresh_identity_or_external_fill(self):
        data = script('void Created(GameObject *obj) { GameObject *controller=Commands->Create_Object("Invisible_Object",p); Commands->Attach_Script(controller,"Test_Cinematic","Example.TXT"); Commands->Attach_Script(obj,"Test_Cinematic",name); }')
        rows, callers = source_routes(binding(), [{'member': 'example.txt', 'branches': {}}], data,
                                      {'MissionX0.cpp': CONSTANTS})
        self.assertFalse(rows)
        self.assertEqual(len(callers), 2)
        self.assertIn('Create_Object', callers[0]['possible_target_assignments'][0]['expression'])
        self.assertIsNone(callers[1]['control_file_literal'])
        self.assertTrue(all(not row['target_identity_and_lifetime_proven'] for row in callers))

    def test_tail_attachment_does_not_inherit_normal_lifetime(self):
        body = 'void Created(GameObject *obj) { Commands->Send_Custom_Event(obj,obj,Get_Int_Parameter("Type"),1); }'
        data = script(body, name='Helper', owner='Toolkit.cpp', descriptor='Type:int')
        files = [{'member': 'example.txt', 'branches': {'primary_killed_tail': [
            {'command': 'attach_script', 'arguments': ['1', 'Helper', '10013'], 'line': 20,
             'seconds_float32': 1000000.0}]}}]
        rows, _ = source_routes(binding(), files, data, {'Toolkit.cpp': CONSTANTS})
        self.assertEqual(rows[0]['binding_kind'], 'cinematic_attachment_candidate')
        self.assertEqual(rows[0]['possible_cinematic_slots'], [13])
        self.assertFalse(rows[0]['callback_execution_proven'])

    def test_callback_provenance_ignores_comments_and_quoted_braces(self):
        rows = callbacks('/* void Fake() {} */ void Created(GameObject *obj) { const char *s="}"; } void Killed(GameObject *obj) {}')
        self.assertEqual([row['name'] for row in rows], ['Created', 'Killed'])

    def test_identity_mismatch_and_native_claims_are_rejected(self):
        cinematic = {'map': 'M13.mix', 'archive_sha256': 'synthetic hash', 'files': []}
        result = analyze(binding(), cinematic, {}, {})
        self.assertFalse(result['runtime_or_physical_acceptance'])
        self.assertFalse(result['complete_mission_closure'])
        cinematic['archive_sha256'] = 'different'
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            analyze(binding(), cinematic, {}, {})

    def test_control_event_roles_and_primary_tail_are_retained_without_delivery_claims(self):
        file = {'member': 'fixture.txt', **trace(b'0 Send_Custom, #1, 9035, 10013\n1000000 Send_Custom, #1, 10013, #2\n', {})}
        result = analyze(binding(), {'map': 'M13.mix', 'archive_sha256': 'synthetic hash', 'files': [file]}, {}, {})
        events = result['control_custom_events']
        self.assertIsNone(events[0]['possible_cinematic_slot'])
        self.assertEqual(events[1]['possible_cinematic_slot'], 13)
        self.assertEqual(events[1]['branch'], 'primary_killed_tail')
        self.assertEqual(events[1]['custom_parameter_token'], '#2')
        self.assertFalse(events[1]['destination_identity_delivery_and_slot_write_proven'])

    def test_changed_definition_database_invalidates_parameter_contexts(self):
        class Archive:
            def read_binary(self, name):
                if name != 'objects.ddb':
                    raise AssertionError(name)
                return b'synthetic definitions'
        receipt = {'objects_ddb_sha256': hashlib.sha256(b'synthetic definitions').hexdigest()}
        archives = {'always.dbs': Archive()}
        verify_definition_receipt(Path('.'), receipt, archives)
        receipt['objects_ddb_sha256'] = hashlib.sha256(b'different').hexdigest()
        with self.assertRaisesRegex(ValueError, 'differs'):
            verify_definition_receipt(Path('.'), receipt, archives)
        for expected in (None, '', 'unknown', 7):
            with self.assertRaisesRegex(ValueError, 'lacks valid'):
                verify_definition_receipt(Path('.'), {'objects_ddb_sha256': expected}, archives)

    def test_public_output_refused_before_retail_or_source_access(self):
        with tempfile.TemporaryDirectory() as temp:
            argv = ['audit', '--root', temp, '--data', temp, '--bindings-directory', temp,
                    '--output-directory', str(Path(temp) / 'public')]
            with patch('sys.argv', argv), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
