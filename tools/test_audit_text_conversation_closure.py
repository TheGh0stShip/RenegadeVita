import unittest

from tools.audit_text_conversation_closure import analyze_map, scan_script_arguments, voice_state


class ScriptArgumentScan(unittest.TestCase):
    def test_flags_defaulted_long_id_and_zero_arguments(self):
        source = '''
        Commands->Add_Objective(1, OBJECTIVE_TYPE_PRIMARY, OBJECTIVE_STATUS_PENDING, IDS_A, NULL, IDS_B);
        Commands->Add_Objective(2, OBJECTIVE_TYPE_PRIMARY, OBJECTIVE_STATUS_HIDDEN, 1000, NULL);
        Commands->Set_HUD_Help_Text(0, color);
        // Commands->Add_Objective(3, a, b, 0);
        Commands->Display_Text(f(1, 2));
        '''
        result = scan_script_arguments(source, 'x.cpp')
        self.assertEqual(result['calls'], 4)
        self.assertEqual([r['line'] for r in result['defaulted_long_id']], [3])
        self.assertEqual([(r['command'], r['index']) for r in result['zero_arguments']],
                         [('Set_HUD_Help_Text', 0)])

    def test_comma_inside_string_and_nested_call_stays_one_argument(self):
        source = 'Commands->Add_Objective(1, 2, 3, IDS_X, "a,b", g(1, 2));'
        self.assertEqual(scan_script_arguments(source, 'x.cpp')['defaulted_long_id'], [])

    def test_voice_state(self):
        self.assertEqual(voice_state({'sound_id': None}), 'no_voice')
        self.assertEqual(voice_state({'sound_id': 0}), 'no_voice')
        self.assertEqual(voice_state({'sound_id': 0xFFFFFFFF}), 'no_voice')
        self.assertEqual(voice_state({'sound_id': 163845379}), 'positive')


class MapAnalysis(unittest.TestCase):
    def test_missing_name_text_and_sound_gap(self):
        receipt = {
            'level_conversations': [{'name': 'Level_A', 'orators': [{}], 'remarks': [
                {'text_id': 1001, 'orator_index': 0}, {'text_id': 1002, 'orator_index': 3}]}],
            'source_name_leads': [{'name': 'level_a', 'script': 's', 'line': 1},
                                  {'name': 'gone', 'script': 's', 'line': 2, 'script_in_discovered_closure': True}],
            'string_database_candidates': [{'archive': 'always.dat', 'findings': [
                {'kind': 'sound_definition_id_not_located', 'text_id': 1001},
                {'kind': 'sound_definition_id_not_located', 'text_id': 9999}]}]}
        strings = {'always.dat': {1001: {'sound_id': 5, 'translations': [{'code_units': 3}]}}}
        result = analyze_map(receipt, {}, strings)
        self.assertEqual(result['found_level'], 1)
        self.assertEqual([m['name'] for m in result['missing_names']], ['gone'])
        self.assertEqual(result['orator_index_errors'], 1)
        self.assertEqual(result['candidates']['always.dat']['text_ids_absent'], [1002])
        self.assertEqual(result['sound_gaps']['always.dat'],
                         {'sound_definition_id_not_located': [1001]})


if __name__ == '__main__':
    unittest.main()
