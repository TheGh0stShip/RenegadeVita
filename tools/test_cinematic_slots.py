"""Asset-free counterexamples for cinematic chronology and lifetime leads."""
import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.audit_cinematic_slots import (
    ROOT, audit, control_records, created_body, float32, integer, main,
    runtime_parameters, script_effects, slot_uses, time_seconds, trace,
)
from tools.audit_mission_content_bindings import source_scripts
from tools.renegade_cinematic_dependency_scan import scan_all_text


def helper(body, name='Helper'):
    return {name.lower(): {'name': name, 'owner': 'Synthetic.cpp',
                          'body_start_line': 100, 'body': body}}


class FakeArchive:
    def __init__(self, path, entries):
        self.path = Path(path)
        self.entries = entries
    def read_binary(self, name):
        return self.entries[name]
    def read_text(self, name):
        return self.read_binary(name).decode('latin1')


class CinematicSlotsTests(unittest.TestCase):
    def test_float32_time_conversion_preserves_frame_units(self):
        self.assertEqual(time_seconds('-30'), 1.0)
        self.assertEqual(time_seconds('0.1'), float32(0.1))
        self.assertEqual(time_seconds('-.5'), float32(float32(.5) / 30.0))
        self.assertEqual(time_seconds('+1e2'), 100.0)
        for token in ('1e999', 'nan', '1e40'):
            with self.assertRaises((ValueError, OverflowError)):
                time_seconds(token)

    def test_normalized_float_ties_preserve_source_order(self):
        rows, findings = control_records(b'1.00000002 Move_Slot, 2, 1\n1.00000001 Create_Object, 1, "Model"\n-15 Play_Animation, 1, "Animation"\n')
        self.assertFalse(findings)
        self.assertEqual([r['line'] for r in rows], [3, 1, 2])
        self.assertEqual(rows[1]['seconds_float32'], rows[2]['seconds_float32'])

    def test_branch_boundary_is_classified_after_float32_rounding(self):
        result = trace(b'998999.99999 Destroy_Object, 0\n999000.01 Destroy_Object, 1\n999000.1 Destroy_Object, 2\n1000000 Destroy_Object, 3\n', {})
        self.assertEqual([r['line'] for r in result['branches']['boundary']], [1, 2])
        self.assertEqual([r['line'] for r in result['branches']['primary_killed_tail']], [3, 4])
        self.assertFalse(result['branches']['normal'])

    def test_primary_tail_does_not_reuse_normal_end_state(self):
        result = trace(b'0 Create_Object, 3, "Model"\n1 Destroy_Object, 3\n1000000 Destroy_Object, 3\n', {})
        tail = result['branches']['primary_killed_tail'][0]
        self.assertEqual(tail['slot_uses'][0]['state'], 'no_prior_text_producer')
        self.assertEqual(tail['initial_slot_snapshot'], 'unknown_at_primary_death')

    def test_time_order_precedes_file_order_and_no_producer_keeps_external_fill_open(self):
        result = trace(b'-300 Create_Object, 1, "Model"\n0 Attach_Script, 1, "Helper"\n', helper('void Created(GameObject *obj) {}'))
        first, second = result['branches']['normal']
        self.assertEqual([first['line'], second['line']], [2, 1])
        self.assertEqual(first['slot_uses'][0]['state'], 'no_prior_text_producer')
        self.assertTrue(first['slot_uses'][0]['external_slot_fill_and_runtime_lifetime_unverified'])

    def test_failed_create_keeps_old_producer_as_a_candidate(self):
        rows = trace(b'0 Create_Object, 1, "First"\n1 Create_Object, 1, "Second"\n2 Play_Animation, 1, "Animation"\n', {})['branches']['normal']
        use = rows[-1]['slot_uses'][0]
        self.assertEqual([r['name'] for r in use['producer_candidates']], ['First', 'Second'])
        self.assertTrue(use['prior_empty_or_unknown_snapshot_possible'])
        self.assertTrue(all(not r['creation_success_proven'] for r in use['producer_candidates']))

    def test_move_transfers_producers_and_clears_old_slot(self):
        rows = trace(b'0 Create_Object, 1, "Model"\n1 Move_Slot, 2, 1\n2 Play_Animation, 2, "Animation"\n3 Destroy_Object, 1\n', {})['branches']['normal']
        self.assertEqual(rows[2]['slot_uses'][0]['producer_candidates'][0]['creation_line'], 1)
        self.assertEqual(rows[3]['slot_uses'][0]['state'], 'no_prior_text_producer')

    def test_same_slot_move_does_not_clear_and_invalid_destination_does_not_transfer(self):
        rows = trace(b'0 Create_Object, 1, "Model"\n1 Move_Slot, 1, 1\n2 Move_Slot, 40, 1\n3 Destroy_Object, 1\n', {})['branches']['normal']
        self.assertEqual(rows[-1]['slot_uses'][0]['producer_candidates'][0]['creation_line'], 1)

    def test_destroy_retains_raw_id_and_effects_do_not_mutate_earlier_snapshots(self):
        rows = trace(b'0 Create_Object, 1, "Model"\n1 Play_Animation, 1, "Animation"\n2 Destroy_Object, 1\n3 Play_Animation, 1, "Animation"\n', {})['branches']['normal']
        before = rows[1]['slot_uses'][0]['producer_candidates'][0]
        after = rows[3]['slot_uses'][0]['producer_candidates'][0]
        self.assertFalse(before['possible_effects'])
        self.assertEqual(after['possible_effects'][0]['kind'], 'destroy_requested_raw_slot_retained')

    def test_callback_effects_remain_candidates_and_created_damage_is_retained(self):
        scripts = helper('void Created(GameObject *obj) { if (obj) { Commands->Apply_Damage(obj,1,"Fixture",0); } }\nvoid Killed(GameObject *obj) { Commands->Send_Custom_Event(obj,obj,7,0); }')
        effect = script_effects('Helper', scripts)
        self.assertEqual(effect['created_possible_effect_commands'], ['Apply_Damage'])
        self.assertEqual(effect['possible_effect_commands'], ['Apply_Damage', 'Send_Custom_Event'])
        self.assertFalse(effect['callback_execution_proven'])
        rows = trace(b'0 Create_Object, 1, "Model"\n1 Attach_Script, 1, "Helper"\n2 Attach_Script, 1, "Unknown"\n3 Play_Animation, 1, "Animation"\n', scripts)['branches']['normal']
        effects = rows[-1]['slot_uses'][0]['producer_candidates'][0]['possible_effects']
        self.assertEqual(effects[0]['created_possible_effect_commands'], ['Apply_Damage'])
        self.assertTrue(effects[1]['source_not_located'])

    def test_created_body_ignores_quoted_braces_and_other_callbacks(self):
        body = 'void Created(GameObject *obj) { const char *s="}"; /* } */ } void Killed(GameObject *obj) { Commands->Destroy_Object(obj); }'
        self.assertNotIn('Destroy_Object', created_body(body))
        self.assertEqual(created_body('void Killed(GameObject *obj) {}'), '')

    def test_optional_hosts_and_restoration_roles_match_original_commands(self):
        self.assertEqual(slot_uses('create_real_object', ['1', 'Unit']), [])
        self.assertEqual(slot_uses('create_real_object', ['1', 'Unit', '']), [])
        self.assertEqual(slot_uses('play_audio', ['Sound']), [])
        rows = trace(b'0 Play_Audio, "Sound", -1\n0 Control_Camera, -1\n0 Attach_To_Bone, 1, -1\n0 Create_Explosion, "Explosion", 40\n0 Create_Real_Object, 1, "Unit", 40\n', {})['branches']['normal']
        self.assertEqual(rows[0]['slot_uses'][0]['state'], 'original_2d_audio')
        self.assertEqual(rows[1]['slot_uses'][0]['state'], 'original_camera_restore')
        self.assertEqual(rows[2]['slot_uses'][1]['state'], 'original_bone_detach')
        self.assertEqual(rows[3]['slot_uses'][0]['state'], 'unchecked_out_of_range')
        self.assertEqual(rows[4]['slot_uses'][0]['state'], 'unchecked_out_of_range')

    def test_custom_type_parameters_and_object_namespaces_stay_distinct(self):
        rows = trace(b'0 Send_Custom, 100, 77, 200\n0 Send_Custom, 200, 88, 100\n0 Send_Custom, #1, 99, #2\n', {}, [100], [200])['branches']['normal']
        self.assertEqual(rows[0]['custom_event_type'], 77)
        self.assertEqual(rows[0]['literal_custom_parameter'], 200)
        self.assertEqual(rows[0]['literal_custom_destination']['classification'], 'serialized_game_object')
        self.assertEqual(rows[1]['literal_custom_destination']['classification'], 'spawner_namespace_only')
        self.assertEqual([r['role'] for r in rows[2]['slot_uses']], ['custom_destination', 'custom_parameter'])
        self.assertTrue(all(r['external_slot_fill_and_runtime_lifetime_unverified'] for r in rows[2]['slot_uses']))

    def test_invalid_custom_slots_retain_distinct_original_fallback_values(self):
        rows = trace(b'0 Send_Custom, #40, 10001, #-1\n0 Send_Custom, 100, 77, #40\n', {}, [100])['branches']['normal']
        destination, parameter = rows[0]['slot_uses']
        self.assertEqual(destination['original_custom_fallback_value'], -1)
        self.assertEqual(parameter['original_custom_fallback_value'], 0)
        self.assertFalse(parameter['event_delivery_proven'])
        self.assertEqual(rows[1]['literal_custom_destination']['classification'], 'serialized_game_object')
        self.assertEqual(rows[1]['slot_uses'][0]['original_custom_fallback_value'], 0)
        source = (ROOT / 'upstream/CnC_Renegade/Code/Scripts/Test_Cinematic.cpp').read_text()
        body = source.split('void\tCommand_Send_Custom(', 1)[1].split('void\tCommand_Attach_To_Bone(', 1)[0]
        self.assertIn('int to_id = -1;', body)
        self.assertIn('int parameter = 0;', body)
        self.assertIn('Commands->Send_Custom_Event( Owner(), to, type, parameter );', body)

    def test_primary_notification_and_parser_mutation_source_contract(self):
        source = (ROOT / 'upstream/CnC_Renegade/Code/Scripts/Test_Cinematic.cpp').read_text()
        helper_source = source.split('DECLARE_SCRIPT(Test_Cinematic,', 1)[0]
        self.assertEqual(helper_source.count('if (!custom_sent)'), 2)
        self.assertEqual(helper_source.count('custom_sent = true;'), 2)
        self.assertIn('SAVE_VARIABLE( custom_sent, 1 );', helper_source)
        parser = source.split('void\tParse_Commands(', 1)[1].split('void Created(', 1)[0]
        self.assertIn('Controls->Time <= LAST_VALID_TIMESTAMP', parser)
        self.assertLess(parser.index('Parse_Command( Controls->Command );'),
                        parser.index('Remove_Head_Control_Line();', parser.index('Parse_Command( Controls->Command );')))
        remover = source.split('void\tRemove_Head_Control_Line(', 1)[1].split('void\tDisplay_Control_Lines(', 1)[0]
        self.assertIn('if ( Controls != NULL )', remover)
        self.assertLess(remover.index('Controls = Controls->Next;'), remover.index('delete control;'))
        commands = (ROOT / 'upstream/CnC_Renegade/Code/Combat/scriptcommands.cpp').read_text()
        dispatch = commands.split('void\tSend_Custom_Event(', 1)[1].split('void\tSend_Damaged_Event(', 1)[0]
        self.assertIn('if ( delay <= 0 )', dispatch)
        self.assertIn('observer_list[ index ]->Custom( to, type, param, from );', dispatch)
        destroy = commands.split('void\tDestroy_Object(', 1)[1].split('GameObject * Find_Object(', 1)[0]
        self.assertIn('obj->Set_Delete_Pending();', destroy)
        self.assertNotIn('delete obj', destroy)

    def test_integer_tokens_preserve_32_bit_semantics_and_unknown_spelling(self):
        self.assertEqual(integer('2147483647'), 0x7fffffff)
        self.assertEqual(integer('-2147483648'), -0x80000000)
        self.assertEqual(integer('one'), 0)
        self.assertEqual(integer('1junk'), 1)
        self.assertEqual(integer(''), 0)
        for token in ('4294967295', '-2147483649'):
            self.assertIsNone(integer(token))

    def test_zero_id_and_overflow_are_not_serialized_object_owners(self):
        rows = trace(b'0 Send_Custom, 0, 77, 200\n1 Send_Custom, 4294967295, 88, 0\n', {}, [0], [0])['branches']['normal']
        self.assertEqual([r['literal_custom_destination']['classification'] for r in rows], ['zero_or_unsupported_integer'] * 2)
        self.assertIsNone(rows[1]['literal_custom_destination']['id'])

    def test_long_runtime_line_is_truncated_and_unknown_active_lines_remain_findings(self):
        rows, findings = control_records(b'; ignored\r\n0 Create_Object, 1, "' + b'M' * 210 + b'"\r\ninvalid active line\n0 Unknown_Command, 1\n')
        self.assertEqual(len(rows[0]['arguments'][1]), 199 - len('0 Create_Object, 1, "'))
        self.assertEqual([r['line'] for r in rows], [2, 3, 4])
        self.assertEqual({r['kind'] for r in findings}, {'runtime_line_truncated', 'original_parser_unknown_command'})

    def test_original_non_numeric_time_header_and_timestamp_only_line_are_distinct(self):
        rows, findings = control_records(b'*** Header ***\n-30\n0 Create_Object, 1, "Model"\n')
        self.assertEqual([r['line'] for r in rows], [1, 3])
        self.assertEqual(rows[0]['seconds_float32'], 0.0)
        self.assertEqual({r['kind'] for r in findings}, {'original_parser_unknown_command', 'original_loader_ignores_line_without_command'})

    def test_original_title_prefix_and_non_csv_quote_parsing_are_preserved(self):
        rows, findings = control_records(b'0 Create_Object_suffix, 1, "Model"\n')
        self.assertFalse(findings)
        self.assertEqual(rows[0]['command'], 'create_object')
        self.assertEqual(runtime_parameters('1, "Greeting,7", "A""B",'), ['1', 'Greeting,7', 'A""B', ''])
        self.assertEqual(runtime_parameters('1, "Unclosed'), ['1', 'Unclosed'])

    def test_shifted_audio_arguments_keep_original_zero_host_and_ignored_extra(self):
        row = trace(b'0 Play_Audio, 14, "NamedSound", 0, "head"\n', {})['branches']['normal'][0]
        self.assertEqual(row['audio_preset_name'], '14')
        self.assertEqual(row['slot_uses'][0]['slot'], 0)
        self.assertTrue(row['slot_uses'][0]['original_atoi_uses_prefix_or_zero'])
        self.assertEqual(row['trailing_arguments_ignored_by_original_command'], ['head'])

    def test_missing_arguments_are_retained_without_fabricated_objects(self):
        result = trace(b'0 Create_Object, 1\n0 Create_Explosion\n0 Attach_Script, 1\n0 Send_Custom, #1\n', {})
        self.assertEqual({r['kind'] for r in result['findings']}, {'missing_creation_argument', 'missing_slot_argument', 'missing_script_argument', 'missing_custom_argument'})

    def test_original_damage_helper_source_is_exact_and_remains_unexecuted(self):
        row = script_effects('M00_Cinematic_Kill_Object_DAY', source_scripts(ROOT))
        self.assertEqual(row['source_owner'], 'Test_DAY.cpp')
        self.assertEqual(row['created_possible_effect_commands'], ['Apply_Damage'])
        self.assertFalse(row['callback_execution_proven'])

    def test_text_inventory_uses_custom_event_type_not_parameter(self):
        archive = FakeArchive('M13.mix', {'test.txt': b'0 Send_Custom, 100, 77, #2\n1 Send_Custom, #1, 88, 123\n'})
        result = scan_all_text(archive)
        self.assertEqual(result['custom_messages'], ['77', '88'])
        self.assertEqual(result['dependencies']['custom_messages'], ['77', '88'])

    def test_audit_enforces_map_and_control_hashes_and_keeps_acceptance_open(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'M13.mix'
            path.write_bytes(b'synthetic archive identity')
            text = b'0 Create_Object, 1, "Model"\n0 Attach_Script, 1, "Helper"\n'
            receipt = {'map': 'M13.mix', 'archive_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                       'members': {'map.ldd': {'objects': [{'instance_id': 100}], 'spawners': []}},
                       'media': {'text_members': [{'archive': 'M13.mix', 'member': 'test.txt', 'sha256': hashlib.sha256(text).hexdigest()}]}}
            with patch('tools.audit_cinematic_slots.MixArchive', return_value=FakeArchive(path, {'test.txt': text})):
                result = audit(root, receipt, helper('void Created(GameObject *obj) {}'))
                self.assertEqual(result['summary']['text_candidates'], 1)
                self.assertFalse(result['runtime_or_physical_acceptance'])
                self.assertFalse(result['complete_mission_closure'])
                receipt['media']['text_members'][0]['sha256'] = 'changed'
                with self.assertRaisesRegex(ValueError, 'cinematic candidate'):
                    audit(root, receipt, {})
                receipt['archive_sha256'] = 'changed'
                with self.assertRaisesRegex(ValueError, 'mission archive'):
                    audit(root, receipt, {})

    def test_private_output_is_required_before_inspecting_retail(self):
        with tempfile.TemporaryDirectory() as temp:
            argv = ['audit', '--root', temp, '--data', temp, '--bindings-directory', temp, '--output-directory', str(Path(temp) / 'public')]
            with patch('sys.argv', argv), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
