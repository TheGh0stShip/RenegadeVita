"""Asset-free counterexamples for conversation provenance and startup omissions."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.audit_deep_saved_content import conversations
from tools.audit_m13_level_owners import chunks
from tools.audit_mission_conversations import (
    ROOT, RetailFiles, audit, conversation_leads, main, sound_chain,
    sound_definitions, startup_source_findings, translations, utf16_metadata,
)
from tools.test_m13_level_owners import chunk, definition, integer, micro


def conversation_payload(text=1001, legacy=False, category=1):
    fields = micro(0, b'Greeting\0') + micro(1, integer(42)) + micro(3, integer(0xfedcba98)) + micro(8, integer(category))
    if legacy:
        fields += micro(2, integer(0) + integer(text))
    variables = chunk(0x08090316, fields)
    orator = chunk(0x08090317, chunk(0x11060315, micro(1, integer(77)) + micro(2, integer(0xffffffff))), True)
    remark = chunk(0x08090318, chunk(0x01250307, micro(0, integer(0)) + micro(1, integer(text))), True)
    return variables + orator + (b'' if legacy else remark)


def translation_fixture(sound=7, include_sound=True, text='Private fixture subtitle'):
    fields = micro(1, integer(1001)) + micro(2, b'IDS_GREETING\0') + micro(6, b'\0')
    if include_sound:
        fields += micro(5, integer(sound))
    body = chunk(0x06141108, fields) + chunk(0x0614110b, (text + '\0').encode('utf-16le'))
    factory = chunk(0x90001, chunk(0x100100, integer(0xfedcba98)) + chunk(0x100101, body, True), True)
    return chunk(0x90000, chunk(0x07141201, factory, True), True)


class FakeArchive:
    def __init__(self, name, entries):
        self.path = Path(name)
        self.entries = entries

    def read_binary(self, name):
        return self.entries[name]


class MissionConversationsTests(unittest.TestCase):
    def test_scoped_records_preserve_pointer_width_orator_ordinal_and_text_ids(self):
        payload = chunk(0x40700, chunk(0x08090318, integer(1) + chunk(0x08090319, conversation_payload(), True), True), True)
        row = conversations(chunks(payload), allow_legacy_category=False)[0]
        self.assertEqual(row['old_pointer_token'], 0xfedcba98)
        self.assertEqual(row['orators'], [{'index': 0, 'id': 77, 'old_pointer_token': 0xffffffff}])
        self.assertEqual(row['remarks'][0]['orator_index'], 0)
        self.assertEqual(row['text_ids'], [1001])
        self.assertEqual(conversations(chunks(chunk(999, conversation_payload(), True))), [])

    def test_legacy_inline_remarks_and_manager_wrapper_are_retained(self):
        payload = chunk(0x40700, chunk(0x08090316, conversation_payload(legacy=True), True), True)
        row = conversations(chunks(payload))[0]
        self.assertEqual(row['category_bytes'], 0)
        self.assertEqual(row['text_ids'], [1001])
        self.assertEqual(row['remarks'][0]['kind'], 'legacy_inline_remark')

    def test_legacy_and_modern_remark_order_follows_actual_chunk_order(self):
        variables, orator, remark = chunks(conversation_payload())
        old_fields = variables.data + micro(2, integer(0) + integer(1002))
        for body, expected in [(chunk(variables.kind, old_fields) + chunk(remark.kind, remark.data, True), [1002, 1001]),
                               (chunk(remark.kind, remark.data, True) + chunk(variables.kind, old_fields), [1001, 1002])]:
            data = chunk(0x40700, chunk(0x08090316, body, True), True)
            self.assertEqual(conversations(chunks(data))[0]['text_ids'], expected)

    def test_category_mismatch_and_nonretail_category_width_are_rejected(self):
        bad = chunk(0x40700, chunk(0x08090318, integer(0) + chunk(0x08090319, conversation_payload(), True), True), True)
        with self.assertRaises(ValueError):
            conversations(chunks(bad))
        legacy = chunk(0x40700, chunk(0x08090318, b'\1' + chunk(0x08090319, conversation_payload(), True), True), True)
        self.assertEqual(conversations(chunks(legacy))[0]['category_bytes'], 1)
        with self.assertRaises(ValueError):
            conversations(chunks(legacy), allow_legacy_category=False)

    def test_bad_legacy_remark_and_pointer_widths_are_rejected(self):
        for body in [conversation_payload().replace(integer(0xfedcba98), b'12345678'),
                     chunk(0x08090316, micro(0, b'Greeting\0') + micro(1, integer(42)) + micro(2, b'x'))]:
            with self.assertRaises(ValueError):
                conversations(chunks(chunk(0x40700, chunk(0x08090316, body, True), True)))

    def test_translation_payloads_keep_utf16_width_hashes_without_dialogue_text(self):
        rows, issues = translations(chunks(translation_fixture()))
        self.assertEqual(issues, [])
        self.assertEqual(rows[1001]['old_pointer_token'], 0xfedcba98)
        self.assertEqual(rows[1001]['sound_id'], 7)
        self.assertNotIn('Private fixture subtitle', json.dumps(rows))
        self.assertEqual(rows[1001]['translations'][0]['code_units'], 24)

    def test_bad_wide_strings_duplicate_ids_and_factory_wrappers_are_rejected(self):
        for payload in [b'abc', b'x\0', b'x\0\0\0z\0\0\0', b'\0\xd8\0\0']:
            with self.subTest(payload=payload), self.assertRaises((ValueError, UnicodeError)):
                utf16_metadata(payload)
        data = translation_fixture()
        manager = chunks(data)[0]
        factories = manager.children[0].data
        with self.assertRaises(ValueError):
            translations(chunks(chunk(0x90000, chunk(0x07141201, factories + factories, True), True)))
        factory = chunk(0x90001, chunk(0x100100, b'12345678') + chunk(0x100101, b'', True), True)
        with self.assertRaises(ValueError):
            translations(chunks(chunk(0x90000, chunk(0x07141201, factory, True), True)))

    def test_sound_variables_are_scoped_to_audible_factory_and_twiddler_duplicates_survive(self):
        audio = definition(0x30000, 7, chunk(0x100, micro(11, b'author\\Voice.wav\0')))
        twiddle = definition(0x102, 8, chunk(0x100, micro(1, integer(7)) + micro(1, integer(7))))
        rows = sound_definitions(chunks(audio + twiddle))
        self.assertEqual(rows[7]['filename'], 'author\\Voice.wav')
        self.assertEqual(rows[8]['alternatives'], [7, 7])
        other = sound_definitions(chunks(definition(0x40123, 9, chunk(0x100, micro(11, b'not_a_sound.wav\0')))))
        self.assertNotIn('filename', other[9])

    def test_filename_basename_collision_candidates_and_loose_files_are_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p / 'Voice.WAV').write_bytes(b'loose voice fixture')
            files = RetailFiles(p, [FakeArchive('always.dat', {'voice.wav': b'global voice fixture'})])
            candidates = files.candidates('C:\\author\\Voice.WAV', FakeArchive('M13.mix', {'voice.wav': b'mission fixture'}))
        self.assertEqual([c['archive'] for c in candidates], ['M13.mix', 'always.dat', None])
        self.assertEqual(len({c['sha256'] for c in candidates}), 3)

    def test_loose_file_symlinks_outside_the_retail_root_are_not_read(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            data = p / 'Data'
            data.mkdir()
            (p / 'outside.wav').write_bytes(b'unrelated fixture')
            (data / 'voice.wav').symlink_to(p / 'outside.wav')
            self.assertEqual(RetailFiles(data, []).candidates('voice.wav', FakeArchive('M.mix', {})), [])

    def test_missing_definitions_files_and_cycles_are_separate_findings(self):
        defs = {7: {'name': 'Voice', 'factory': '0x00030000', 'filename': 'missing.wav'},
                8: {'name': 'Twiddle', 'factory': '0x00000102', 'alternatives': [7, 7, 9]},
                9: {'name': 'Cycle', 'factory': '0x00000102', 'alternatives': [8]}}
        with tempfile.TemporaryDirectory() as temp:
            leaves, issues = sound_chain(8, defs, RetailFiles(Path(temp), []), FakeArchive('M.mix', {}))
        self.assertEqual([leaf['path'][0]['alternative_ordinal'] for leaf in leaves], [0, 1])
        self.assertEqual([i['kind'] for i in issues], ['sound_file_not_located', 'sound_file_not_located', 'sound_twiddler_cycle'])
        with tempfile.TemporaryDirectory() as temp:
            _, issues = sound_chain(99, defs, RetailFiles(Path(temp), []), FakeArchive('M.mix', {}))
        self.assertEqual(issues[0]['kind'], 'sound_definition_id_not_located')

    def test_literal_default_arguments_computed_calls_and_strings_are_distinguished(self):
        source = '''Commands->Create_Conversation("Hello");
Commands->Create_Conversation("Other", 99);
Commands->Create_Conversation(variable);
Commands->Debug_Message("Commands->Create_Conversation(ignored)");'''
        scripts = {'used': {'name': 'Used', 'owner': 'MissionX0.cpp', 'body': source, 'body_start_line': 10}}
        result = {'map': 'M13.mix', 'discovered_scripts': [{'name': 'Used'}]}
        literals, computed = conversation_leads(scripts, result)
        self.assertEqual([r['name'] for r in literals], ['Hello', 'Other'])
        self.assertEqual([r['line'] for r in literals], [10, 11])
        self.assertEqual([r['line'] for r in computed], [12])

    def test_known_array_names_are_retained_as_leads_without_claiming_execution(self):
        scripts = {'used': {'name': 'Used', 'owner': 'MissionX0.cpp', 'body_start_line': 1,
                           'body': 'const char *lines[]={"Greeting", "Unknown"}; Commands->Create_Conversation(lines[index]);'}}
        result = {'map': 'M13.mix', 'discovered_scripts': [{'name': 'Used'}]}
        leads, computed = conversation_leads(scripts, result, {'greeting'})
        self.assertEqual([(l['name'], l['kind']) for l in leads], [('Greeting', 'known_name_string_lead')])
        self.assertEqual(len(computed), 1)

    def test_quotes_in_character_literals_do_not_become_conversation_strings(self):
        scripts = {'used': {'name': 'Used', 'owner': 'MissionX0.cpp', 'body_start_line': 1,
                           'body': '''if (c == '"') { c = '\\''; }
const char *lines[]={"Greeting"}; Commands->Create_Conversation(lines[index]);'''}}
        result = {'map': 'M13.mix', 'discovered_scripts': [{'name': 'Used'}]}
        leads, computed = conversation_leads(scripts, result, {'greeting'})
        self.assertEqual([(l['name'], l['line']) for l in leads], [('Greeting', 2)])
        self.assertEqual(len(computed), 1)

    def audit_fixture(self, directory, variants):
        root = Path(directory)
        global_row = {'name': 'Greeting', 'id': 1, 'orators': [{'index': 0}],
                      'remarks': [{'text_id': 1001, 'orator_index': 0}], 'remark_count': 1}
        files = RetailFiles(root, [FakeArchive('always.dat', {'voice.wav': b'voice fixture'})])
        context = {'globals': [{'archive': 'always.dbs', 'member': 'conv10.cdb', 'sha256': 'fixture', 'rows': [global_row]}],
                   'strings': variants, 'definitions': {7: {'name': 'Voice', 'factory': '0x00030000', 'filename': 'voice.wav'}},
                   'files': files}
        binding = {'map': 'M13.mix', 'discovered_scripts': [], 'bindings': [], 'archive_sha256': 'fixture'}
        with patch('tools.audit_mission_conversations.audit_map', return_value=binding), \
             patch('tools.audit_mission_conversations.MixArchive', return_value=FakeArchive('M13.mix', {})), \
             patch('tools.audit_mission_conversations.startup_source_findings', return_value=[]):
            return audit(root, root, 'M13.mix', context, {})

    def test_database_candidates_with_the_same_text_id_remain_independent(self):
        variants = []
        for name, sound in [('always.dat', 7), ('always.dbs', 99)]:
            rows, issues = translations(chunks(translation_fixture(sound)))
            variants.append({'archive': name, 'member': 'strings.tdb', 'sha256': name, 'rows': rows, 'issues': issues})
        with tempfile.TemporaryDirectory() as temp:
            result = self.audit_fixture(temp, variants)
        self.assertEqual(result['string_database_candidates'][0]['findings'], [])
        self.assertEqual(result['string_database_candidates'][1]['findings'][0]['kind'], 'sound_definition_id_not_located')
        self.assertFalse(result['runtime_or_physical_acceptance'])
        self.assertFalse(result['complete_mission_closure'])

    def test_zero_minus_one_and_absent_sound_fields_are_distinct(self):
        variants = []
        for name, sound, present in [('zero', 0, True), ('minus_one', 0xffffffff, True), ('absent', 0, False)]:
            rows, issues = translations(chunks(translation_fixture(sound, present)))
            variants.append({'archive': name, 'member': 'strings.tdb', 'sha256': name, 'rows': rows, 'issues': issues})
        with tempfile.TemporaryDirectory() as temp:
            result = self.audit_fixture(temp, variants)
        states = [v['chains'][0]['voice_state'] for v in result['string_database_candidates']]
        self.assertEqual(len(set(states)), 3)
        self.assertEqual([v['finding_counts'] for v in result['string_database_candidates']], [{}, {}, {'translation_sound_field_absent': 1}])

    def test_actual_startup_hooks_and_removed_route_negative_controls(self):
        self.assertEqual(startup_source_findings(ROOT), [])
        paths = ['port/platform/vita/a31_vita_runtime.cpp', 'tools/host_a30_definitions/a31_interactive_main.cpp',
                 'port/platform/a31_gameplay_boundary.cpp']
        for removed in paths:
            with self.subTest(removed=removed), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for path in paths:
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = (ROOT / path).read_text()
                    if path == removed:
                        source = source.replace('A31_Interactive_Load_Global_Conversations', 'Removed_Global_Load')
                    target.write_text(source)
                self.assertTrue(startup_source_findings(root))

    def test_missing_early_failure_cleanup_is_a_source_finding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for path in ['port/platform/vita/a31_vita_runtime.cpp', 'tools/host_a30_definitions/a31_interactive_main.cpp',
                         'port/platform/a31_gameplay_boundary.cpp']:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                source = (ROOT / path).read_text().replace('global_conversations_initialized && !combat_initialized', 'false')
                target.write_text(source)
            rows = startup_source_findings(root)
        self.assertEqual({r['route'] for r in rows}, {'native', 'host'})

    def test_detailed_output_is_rejected_outside_private_build_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = ['audit', '--root', str(root), '--data', str(root), '--output-directory', str(root / 'reports')]
            with patch('sys.argv', args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main()
            self.assertFalse((root / 'reports').exists())


if __name__ == '__main__':
    unittest.main()
