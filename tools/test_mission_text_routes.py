"""Asset-free counterexamples for direct text and computed dialogue discovery."""
import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.audit_mission_text_routes import (
    ROOT, arguments, assignments, audit, cinematic_bindings, command_calls, computed_names,
    constant_id, literal_string, main, source_routes, string_id_definitions, texture_candidates,
)
from tools.audit_mission_conversations import RetailFiles
from tools.test_mission_conversations import FakeArchive


def script(body, name='Used'):
    return {'name': name, 'owner': 'MissionX0.cpp', 'body': body, 'body_start_line': 10}


def binding(rows=None):
    return {'map': 'M13.mix', 'discovered_scripts': [{'name': 'Used'}], 'bindings': rows or [],
            'archive_sha256': 'synthetic'}


class MissionTextRoutesTests(unittest.TestCase):
    def test_argument_delimiters_handle_nested_calls_arrays_braces_and_quoted_commas(self):
        source = '(ID, helper(a,b[2]), {1,2}, "voice,with)paren", Vector3(1,2,3))'
        rows, end = arguments(source, 1)
        self.assertEqual([r[1] for r in rows], ['ID', 'helper(a,b[2])', '{1,2}', '"voice,with)paren"', 'Vector3(1,2,3)'])
        self.assertEqual(end, len(source))

    def test_bad_argument_delimiters_are_rejected(self):
        for source in ('(unclosed', '(one[2))', '(one, {1,2))'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                arguments(source, 1)

    def test_comments_strings_and_character_literals_are_not_commands(self):
        source = '''// Commands->Display_Text(1);
char quote='"'; const char *example="Commands->Display_Text(2)";
Commands->Display_Text(3);'''
        rows = list(command_calls(source))
        self.assertEqual([(r['command'], r['arguments'][0][1]) for r in rows], [('Display_Text', '3')])
        self.assertEqual(source[:rows[0]['offset']].count('\n'), 2)

    def test_adjacent_narrow_literals_comments_and_c_string_termination(self):
        self.assertEqual(literal_string('(("MX0_" /* preserve offsets */ "GREETING"))'), 'MX0_GREETING')
        self.assertEqual(literal_string(r'"Greeting\0Ignored"'), 'Greeting')
        self.assertEqual(literal_string(r'"Quote\"And\\Slash"'), 'Quote"And\\Slash')

    def test_unsupported_encoding_and_cpp_hex_escape_do_not_create_false_names(self):
        for value in ('L"Wide"', 'u8"Unicode"', 'R"(raw)"', r'"\x4142"', r'"\u0041"', 'format("Name",id)'):
            self.assertIsNone(literal_string(value), value)

    def test_numeric_aliases_negative_sentinels_and_cycles_are_explicit(self):
        ids = {'BASE': '1000', 'TEXT': '(BASE + 3)', 'LOOP': 'LOOP'}
        self.assertEqual(constant_id('TEXT', ids), 1003)
        self.assertEqual(constant_id('-1', ids), -1)
        self.assertEqual(constant_id('0xffffffff', ids), 0xffffffff)
        for expression in ('LOOP', 'missing', 'call()', '__import__("os").system("false")', 'True', 'BASE * 2'):
            self.assertIsNone(constant_id(expression, ids))

    def test_array_and_variable_names_not_located_in_the_database_are_still_candidates(self):
        row = script('''const char *names[]={"Known", "Absent"};
Commands->Create_Conversation(names[index]);''')
        values = computed_names('names[index]', row, [])
        self.assertEqual([r['name'] for r in values], ['Known', 'Absent'])
        self.assertTrue(all(r['assignment_line'] == 10 for r in values))

    def test_same_script_aliases_shadowing_and_cycles_are_conservative(self):
        row = script('''const char *a="One"; const char *b=a;
{ const char *a="Two"; } a=b;''')
        values = computed_names('b', row, [])
        self.assertEqual({r['name'] for r in values}, {'One', 'Two'})
        self.assertTrue(all(r['kind'] == 'same_script_assignment_candidate' for r in values))

    def test_members_function_returns_and_formatted_names_remain_computed(self):
        row = script('obj.name="Member"; local=choose("Formatted");')
        self.assertNotIn('name', assignments(row['body']))
        for expression in ('obj.name', 'pickName()', 'Get_Parameter(variable)', 'local'):
            self.assertEqual(computed_names(expression, row, []), [])

    def test_parameter_matching_retains_every_binding_without_underscore_aliases_or_defaults(self):
        rows = [{'name': 'Used', 'parameter_fields': [{'name': 'ConvName', 'index': 0, 'value': 'One'}]},
                {'name': 'Used', 'parameter_fields': [{'name': 'convname', 'index': 1, 'value': 'Two'}]},
                {'name': 'Used', 'parameter_fields': [{'name': 'Conv_Name', 'index': 0, 'value': 'Other'}]},
                {'name': 'Unrelated', 'parameter_fields': [{'name': 'ConvName', 'index': 0, 'value': 'Unrelated'}]}]
        values = computed_names('Get_Parameter("CONVNAME")', script(''), rows)
        self.assertEqual([(r['name'], r['binding_index'], r['parameter_index']) for r in values], [('One', 0, 0), ('Two', 1, 1)])
        self.assertEqual(computed_names('Get_Parameter("Absent")', script(''), rows), [])

    def test_typed_command_arguments_keep_objective_ids_distinct_from_text_ids(self):
        row = script('''Commands->Add_Objective(999,1,2,TITLE,NULL,LONG_TEXT);
Commands->Set_Objective_HUD_Info_Position(999,99,"icon.tga",TITLE,Vector3(1,2,3));
Commands->Set_HUD_Help_Text(0,color); Commands->Display_Text(variable);''')
        routes = source_routes({'used': row}, binding(), {'TITLE': '1001', 'LONG_TEXT': '1002'})
        self.assertEqual([r['text_id'] for r in routes['text_calls']], [1001, 1002, 1001, 0, None])
        self.assertEqual([r['state'] for r in routes['text_calls']][-2:], ['clear_help', 'unresolved_or_out_of_range_expression'])
        self.assertTrue(routes['media_calls'][0]['null_argument'])
        self.assertEqual(routes['media_calls'][1]['name'], 'icon.tga')

    def test_defaulted_trailing_add_objective_arguments_are_not_indexed(self):
        # Original Add_Objective(id,type,status,short_id,sound=NULL,long_id=0): four-argument calls are valid.
        row = script('Commands->Add_Objective(7,1,2,TITLE);')
        routes = source_routes({'used': row}, binding(), {'TITLE': '1001'})
        self.assertEqual([r['text_id'] for r in routes['text_calls']], [1001])
        self.assertEqual(routes['media_calls'], [])

    def test_direct_conversation_literals_and_computed_candidates_remain_distinct(self):
        row = script('name="Missing"; Commands->Create_Conversation(name); Commands->Create_Conversation("Known");')
        routes = source_routes({'used': row}, binding(), {})
        self.assertEqual([r['computed'] for r in routes['conversation_calls']], [True, False])
        self.assertEqual([r['candidates'][0]['name'] for r in routes['conversation_calls']], ['Missing', 'Known'])

    def test_literal_source_attachments_supply_parameter_candidates_with_origin(self):
        row = script('Commands->Attach_Script(obj,"Helper","Absent");')
        helper = {**script('Commands->Create_Conversation(Get_Parameter("ConvName"));', 'Helper'),
                  'owner': 'Toolkit.cpp', 'descriptor': 'ConvName:string'}
        data = binding()
        data['discovered_scripts'].append({'name': 'Helper'})
        routes = source_routes({'used': row, 'helper': helper}, data, {})
        value = routes['conversation_calls'][0]['candidates'][0]
        self.assertEqual(value['name'], 'Absent')
        self.assertEqual(value['binding_kind'], 'literal_source_attachment')
        self.assertEqual(value['source_owner'], 'MissionX0.cpp')
        self.assertEqual(value['source_line'], 10)

    def test_original_dds_attempt_and_targa_fallback_preserve_archive_alternatives(self):
        with tempfile.TemporaryDirectory() as temp:
            files = RetailFiles(Path(temp), [FakeArchive('always.dat', {'icon.dds': b'original dds fixture'})])
            rows = texture_candidates(files, 'ICON.tga', FakeArchive('M.mix', {'icon.tga': b'original targa fixture'}))
        self.assertEqual([(r['member'], r['lookup_role']) for r in rows],
                         [('icon.dds', 'original_dds_attempt'), ('icon.tga', 'original_targa_fallback')])

    def test_cinematic_parameters_keep_quotes_commas_comments_and_hash_provenance(self):
        text = b';-1 Attach_Script, 0, "Helper", "Ignored"\n-2 Attach_Script, 4, "Helper", "Greeting,7"\n'
        data = {'media': {'text_members': [{'archive': 'M.mix', 'member': 'intro.txt', 'sha256': hashlib.sha256(text).hexdigest()}]}}
        rows = cinematic_bindings(data, {'helper': {'descriptor': 'ConvName:string,Priority:int'}}, [FakeArchive('M.mix', {'intro.txt': text})])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['cinematic_line'], 2)
        self.assertEqual(rows[0]['object_slot'], '4')
        self.assertEqual([r['value'] for r in rows[0]['parameter_fields']], ['Greeting', '7'])
        with self.assertRaises(ValueError):
            cinematic_bindings(data, {}, [FakeArchive('M.mix', {'intro.txt': b'changed'})])

    def test_original_string_header_resolves_m13_help_ids(self):
        ids = string_id_definitions(ROOT)
        self.assertEqual([constant_id(f'MX0_HELPTEXT_0{i}', ids) for i in range(1, 5)], [8576, 8577, 8578, 8579])
        self.assertEqual(constant_id('IDS_M01DSGN_DSGN0524I1DSGN_TXT', ids), 8282)

    def test_conservative_source_roots_keep_unbound_mission_calls_as_leads(self):
        rows = {'used': script('Commands->Display_Text(1001);'),
                'orphan': script('Commands->Display_Text(1002);', 'Orphan'),
                'other': {**script('Commands->Display_Text(1003);', 'Other'), 'owner': 'Other.cpp'}}
        routes = source_routes(rows, binding(), {})
        self.assertEqual({r['text_id'] for r in routes['text_calls']}, {1001, 1002})
        self.assertFalse(next(r for r in routes['text_calls'] if r['text_id'] == 1002)['script_in_discovered_closure'])

    def test_translation_candidates_unknown_computed_names_and_texture_collisions_are_independent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ids = root / 'upstream/CnC_Renegade/Code/Scripts/string_ids.h'
            ids.parent.mkdir(parents=True)
            ids.write_text('#define TEXT 1001\n')
            header = root / 'port/platform/renegade_vita_tutorial_help.h'
            header.parent.mkdir(parents=True)
            header.write_text('switch(id) { case TEXT: return "Original synthetic hint"; }')
            row = script('''name="Absent"; Commands->Create_Conversation(name);
Commands->Set_HUD_Help_Text(TEXT,color);
Commands->Set_Objective_HUD_Info(999,1,"icon.tga",TEXT);''')
            globals_ = [FakeArchive('always.dat', {'icon.tga': b'global fixture'})]
            context = {'globals': [{'rows': [{'name': 'Known'}]}], 'definitions': {},
                       'files': RetailFiles(root, globals_),
                       'strings': [{'archive': 'always.dat', 'member': 'strings.tdb', 'sha256': 'one', 'rows': {1001: {}}},
                                   {'archive': 'always.dbs', 'member': 'strings.tdb', 'sha256': 'two', 'rows': {}}]}
            with patch('tools.audit_mission_text_routes.audit_map', return_value=binding()), \
                 patch('tools.renegade_cinematic_dependency_scan.MixArchive', return_value=FakeArchive('M13.mix', {'icon.tga': b'level fixture'})):
                result = audit(root, root, 'M13.mix', context, {'used': row})
        self.assertEqual(result['summary']['text_findings_per_candidate'], {'always.dat': 0, 'always.dbs': 2})
        self.assertEqual(result['summary']['unlocated_conversation_candidate_names'], ['Absent'])
        self.assertTrue(result['text_calls'][0]['has_english_vita_help_replacement'])
        self.assertEqual([r['archive'] for r in result['media_calls'][0]['candidates']], ['M13.mix', 'always.dat'])
        self.assertFalse(result['runtime_or_physical_acceptance'])
        self.assertFalse(result['complete_mission_closure'])

    def test_private_receipts_are_rejected_outside_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = ['audit', '--root', str(root), '--data', str(root), '--output-directory', str(root / 'reports')]
            with patch('sys.argv', args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main()
            self.assertFalse((root / 'reports').exists())


if __name__ == '__main__':
    unittest.main()
