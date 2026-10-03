"""Asset-free counterexamples for dialogue ownership and voice provenance."""
import contextlib
import io
import struct
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.audit_m13_level_owners import chunks
from tools.audit_mission_conversations import RetailFiles, sound_definitions
from tools.audit_mission_voice_routes import (
    ROOT, audit, definition_dialogues, dialogue_tables, event_callers, float_metadata,
    instance_dialogues, link_options, link_summary, main, remark_voice,
    sound_reference, source_schema,
)
from tools.test_m13_level_owners import chunk, definition, integer, micro
from tools.test_mission_conversations import FakeArchive


SCHEMA, _ = source_schema(ROOT)


def option(conversation=7, weight=1.0, fields=None):
    fields = micro(0, struct.pack('<f', weight)) + micro(2, integer(conversation)) if fields is None else fields
    return chunk(SCHEMA['option'], chunk(SCHEMA['option_variables'], fields), True)


def entry(options=b'', scope='definition', silence=None):
    variables = b'' if silence is None else chunk(SCHEMA['dialogue_variables'], micro(0, struct.pack('<f', silence)))
    return chunk(SCHEMA[scope + '_entry'], variables + options, True)


def owner(tables, scope='definition', key=1, included=True):
    return {'scope': scope, 'definition_id': key, 'tables': tables, 'in_partial_binding_closure': included}


def conversation(key=7, name='Fixture', archive='always.dbs'):
    return {'id': key, 'name': name, 'archive': archive, 'member': 'conv10.cdb', 'category': 0,
            'remarks': [{'text_id': 1001}]}


class MissionVoiceRoutesTests(unittest.TestCase):
    def test_schema_is_derived_from_original_owners_and_keeps_event_order(self):
        schema, sources = source_schema(ROOT)
        self.assertEqual(schema['definition_entry'], 909991658)
        self.assertEqual(schema['instance_entry'], 909991663)
        self.assertEqual(schema['event_count'], 20)
        self.assertEqual(schema['event_names'][10], 'DIE')
        self.assertEqual(schema['event_names'][-1], 'COMBAT_TO_IDLE')
        self.assertTrue(all(len(row['sha256']) == 64 for row in sources))

    def test_caller_scan_ignores_definition_comments_strings_and_disabled_examples(self):
        source = '''void SoldierGameObj::Say_Dialogue(int event) {}
// soldier->Say_Dialogue(DIALOG_ON_DIE);
Debug_Message("Say_Dialogue(DIALOG_ON_DIE)");
#if 0
soldier->Say_Dialogue(DIALOG_ON_DIE);
#endif
soldier->Say_Dialogue(DIALOG_ON_POKE_IDLE);'''
        rows = event_callers(source, SCHEMA, 'fixture.cpp')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['line'], 7)
        self.assertEqual(rows[0]['event_name'], 'POKE_IDLE')

    def test_dynamic_event_argument_stays_unknown(self):
        rows = event_callers('Say_Dialogue(dialogue_id);', SCHEMA, 'fixture.cpp')
        self.assertIsNone(rows[0]['event_ordinal'])
        self.assertEqual(rows[0]['expression'], 'dialogue_id')

    def test_original_death_route_does_not_directly_call_die_table(self):
        source = (ROOT / 'staging/combat/soldier.cpp').read_text()
        rows = event_callers(source, SCHEMA, 'staging/combat/soldier.cpp')
        self.assertNotIn('DIE', [r['event_name'] for r in rows])
        self.assertIn('Create_Instant_Sound( death_sound_id', source)
        self.assertTrue(any(r['event_ordinal'] is None for r in rows))

    def test_defaults_are_marked_without_inventing_serialized_values(self):
        tables, ignored = dialogue_tables(chunks(entry(option(fields=b''))), SCHEMA)
        self.assertEqual(ignored, 0)
        self.assertFalse(tables[0]['silence_weight']['serialized'])
        row = tables[0]['options'][0]
        self.assertFalse(row['weight']['serialized'])
        self.assertEqual(row['weight']['bits'], 0x3f800000)
        self.assertEqual(row['conversation_id'], 0)
        self.assertFalse(row['conversation_serialized'])

    def test_duplicate_options_keep_ordinals_weights_and_last_scalar_writes(self):
        fields = micro(0, struct.pack('<f', 0.0)) + micro(0, struct.pack('<f', 2.0))
        fields += micro(2, integer(1)) + micro(2, integer(7))
        tables, _ = dialogue_tables(chunks(entry(option(7) + option(fields=fields), silence=3)), SCHEMA)
        options = tables[0]['options']
        self.assertEqual([r['ordinal'] for r in options], [0, 1])
        self.assertEqual([r['conversation_id'] for r in options], [7, 7])
        self.assertEqual([r['weight']['value'] for r in options], [1, 2])
        self.assertEqual(options[1]['conversation_writes'], 2)
        self.assertEqual(tables[0]['silence_weight']['value'], 3)

    def test_weight_bit_patterns_preserve_zero_negative_and_nonfinite_without_simulation(self):
        for value, expected in [(0.0, 'zero'), (-1.0, 'negative'), (1.0, 'positive'), (float('nan'), 'nonfinite')]:
            with self.subTest(value=value):
                row = float_metadata(struct.pack('<f', value), True)
                self.assertEqual(row['class'], expected)
                if expected == 'nonfinite':
                    self.assertIsNone(row['value'])
        self.assertEqual(float_metadata(bytes.fromhex('00000080'), True)['bits'], 0x80000000)

    def test_original_event_limit_ignores_excess_entries_without_shifting_ordinals(self):
        tables, ignored = dialogue_tables(chunks(entry(option()) * 22), SCHEMA)
        self.assertEqual(len(tables), 20)
        self.assertEqual(ignored, 2)
        self.assertEqual(tables[-1]['event_ordinal'], 19)

    def test_bad_scalar_widths_are_rejected(self):
        for fields in [micro(0, b'\0' * 8), micro(2, b'\0' * 8), micro(2, b'\0')]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                dialogue_tables(chunks(entry(option(fields=fields))), SCHEMA)

    def test_definition_factory_scope_rejects_reused_dialogue_ids_in_other_factories(self):
        payload = definition(SCHEMA['definition_factory'], 1, entry(option()))
        payload += definition(0x12345, 2, entry(option(99)))
        nodes = chunks(payload)
        result = definition_dialogues(nodes, sound_definitions(nodes), SCHEMA)
        self.assertEqual(set(result), {1})
        self.assertEqual(result[1]['tables'][0]['options'][0]['conversation_id'], 7)

    def instance_fixture(self, identity=None, body=None):
        identity = chunk(910991407, micro(2, integer(1)) + micro(3, integer(99))) if identity is None else identity
        body = entry(option(8), 'instance') if body is None else body
        return chunk(SCHEMA['instance_factory'], chunk(0x100100, integer(0xfedcba98)) +
                     chunk(0x100101, chunk(1234, identity, True) + body, True), True)

    def test_serialized_instance_tables_remain_separate_from_preset_and_tokens_are_u32(self):
        result = instance_dialogues(chunks(self.instance_fixture()), SCHEMA)
        self.assertEqual(result[0]['instance_id'], 99)
        self.assertEqual(result[0]['definition_id'], 1)
        self.assertEqual(result[0]['old_pointer_token'], 0xfedcba98)
        self.assertEqual(result[0]['tables'][0]['options'][0]['conversation_id'], 8)

    def test_nested_dialogue_decoys_are_not_direct_soldier_entries(self):
        result = instance_dialogues(chunks(self.instance_fixture(body=chunk(1234, entry(option(), 'instance'), True))), SCHEMA)
        self.assertEqual(result[0]['tables'], [])

    def test_zero_id_records_are_not_discarded_or_deduplicated_as_one_live_object(self):
        identity = chunk(910991407, micro(2, integer(1)) + micro(3, integer(0)))
        payload = self.instance_fixture(identity=identity) * 2
        rows = instance_dialogues(chunks(payload), SCHEMA)
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]['offset'], rows[1]['offset'])
        self.assertTrue(all(r['serialized_id_state'] == 'zero_assignment_lifetime_unverified' for r in rows))

    def test_missing_or_ambiguous_instance_identity_is_rejected(self):
        for identity in [b'', chunk(910991407, micro(2, integer(1)) + micro(3, integer(99))) * 2]:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                instance_dialogues(chunks(self.instance_fixture(identity=identity)), SCHEMA)

    def test_sound_zero_negative_absent_and_positive_follow_distinct_original_call_sites(self):
        for raw, speech, duration in [(None, False, True), (0, False, False), (0xffffffff, False, True),
                                      (0x80000000, False, True), (7, True, True)]:
            row = sound_reference(raw)
            self.assertEqual(row['soldier_speech_lookup_attempt'], speech)
            self.assertEqual(row['conversation_duration_lookup_attempt'], duration)
        self.assertNotEqual(sound_reference(None)['state'], sound_reference(0xffffffff)['state'])

    def link_fixture(self, rows=None, entries=None, sound=99):
        with tempfile.TemporaryDirectory() as temp:
            files = RetailFiles(Path(temp), [])
            tables, _ = dialogue_tables(chunks(entry(option()) if entries is None else entries), SCHEMA)
            return link_options([owner(tables)], [conversation()] if rows is None else rows,
                                {1001: {'sound_id': sound}}, {}, files, FakeArchive('M13.mix', {}))

    def test_voice_gap_options_are_metadata_even_with_zero_or_nonfinite_weights(self):
        links, resolutions = self.link_fixture(entries=entry(option(7, 0) + option(7, float('nan'))))
        summary = link_summary(links)
        self.assertEqual(summary['voice_finding_option_records'], 2)
        self.assertEqual(summary['voice_finding_weight_classes'], {'nonfinite': 1, 'zero': 1})
        self.assertEqual(len(resolutions), 1)

    def test_duplicate_conversation_ids_retain_both_candidates_without_choosing_a_winner(self):
        links, resolutions = self.link_fixture(rows=[conversation(), conversation(name='LevelFixture', archive='M13.mix')])
        self.assertEqual(links[0]['conversation_resolution'], 'ambiguous_candidates')
        self.assertEqual([r['archive'] for r in resolutions[0]['candidates']], ['always.dbs', 'M13.mix'])

    def test_unlocated_positive_conversation_and_signed_sentinel_have_distinct_states(self):
        links, resolutions = self.link_fixture(rows=[], entries=entry(option(7) + option(0xffffffff)))
        self.assertEqual([r['conversation_resolution'] for r in links], ['not_located', 'nonpositive_id_no_start'])
        self.assertEqual(resolutions[0]['conversation_id'], -1)

    def test_negative_sound_duration_query_is_not_counted_as_missing_speech(self):
        links, resolutions = self.link_fixture(sound=0xffffffff)
        self.assertFalse(links[0]['has_voice_finding_candidate'])
        chain = resolutions[0]['candidates'][0]['chains'][0]
        self.assertTrue(chain['conversation_duration_lookup_attempt'])
        self.assertEqual(chain['findings'], [])

    def test_missing_text_and_missing_filename_remain_separate_findings(self):
        with tempfile.TemporaryDirectory() as temp:
            files, mission = RetailFiles(Path(temp), []), FakeArchive('M13.mix', {})
            missing_text = remark_voice({'text_id': 1001}, {}, {}, files, mission)
            missing_file = remark_voice({'text_id': 1001}, {1001: {'sound_id': 7}},
                                        {7: {'factory': '0x00030000', 'name': 'Fixture', 'filename': 'fixture.wav'}}, files, mission)
        self.assertEqual(missing_text['findings'][0]['kind'], 'conversation_text_id_not_located')
        self.assertEqual(missing_file['findings'][0]['kind'], 'sound_file_not_located')

    def test_binding_definition_identity_mismatch_is_rejected(self):
        binding = {'objects_ddb_sha256': 'different'}
        with patch('tools.audit_mission_voice_routes.audit_map', return_value=binding), \
             patch('tools.audit_mission_voice_routes.MixArchive', return_value=FakeArchive('always.dbs', {'objects.ddb': b'fixture'})), \
             self.assertRaisesRegex(ValueError, 'identity changed'):
            audit(ROOT, Path('/fixture'), 'M13.mix', {'archives': []}, {})

    def test_private_output_and_map_traversal_are_rejected_before_reading_data(self):
        for output, name in [('reports', 'M13.mix'), ('build/private', '../M13.mix')]:
            with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stderr(io.StringIO()), \
                 patch('sys.argv', ['audit', '--root', temp, '--data', temp, '--output-directory', str(Path(temp) / output), '--map', name]), \
                 self.assertRaises(SystemExit):
                main()


if __name__ == '__main__':
    unittest.main()
