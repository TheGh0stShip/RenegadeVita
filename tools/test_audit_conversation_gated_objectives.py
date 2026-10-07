"""Synthetic (retail-free) counterexamples for the conversation-gated objective audit."""
import unittest

from tools.audit_conversation_gated_objectives import (
    BUILTIN_CONSTANTS, Script, analyse_mission, annotate_against_baseline, conversation_flags, eval_cond, key_state, parse_statements,
    path_state, render_markdown)
from tools.audit_deep_saved_content import conversations
from tools.audit_m13_level_owners import chunks
from tools.test_m13_level_owners import chunk, integer, micro

CONSTANTS = {k: str(v) for k, v in BUILTIN_CONSTANTS.items()}

SOURCE = '''
DECLARE_SCRIPT(T_Controller, "")
{
	void Created(GameObject * obj)
	{
		Commands->Add_Objective(1001, OBJECTIVE_TYPE_PRIMARY, OBJECTIVE_STATUS_PENDING, 1, NULL, 2);
		Commands->Add_Objective(1002, OBJECTIVE_TYPE_SECONDARY, OBJECTIVE_STATUS_PENDING, 1, NULL, 2);
		Commands->Add_Objective(1003, OBJECTIVE_TYPE_PRIMARY, OBJECTIVE_STATUS_PENDING, 1, NULL, 2);
		Commands->Add_Objective(1004, OBJECTIVE_TYPE_PRIMARY, OBJECTIVE_STATUS_PENDING, 1, NULL, 2);
	}
	void Custom(GameObject * obj, int type, int param, GameObject * sender)
	{
		if (type >= 1000 && type <= 1005)
		{
			switch (param)
			{
				case 1: if (type == 1003)
						{
							Commands->Set_Objective_Status(1003, OBJECTIVE_STATUS_ACCOMPLISHED);
						}
						else
						{
							Commands->Set_Objective_Status(type, OBJECTIVE_STATUS_ACCOMPLISHED);
						}
						break;
				case 2: Commands->Set_Objective_Status(type, OBJECTIVE_STATUS_FAILED);
						break;
			}
		}
	}
};

DECLARE_SCRIPT(T_Sole_Emitter, "")
{
	void Action_Complete(GameObject * obj, int action_id, ActionCompleteReason reason)
	{
		if (action_id == 100014)
		{
			Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1001, 1);
		}
	}
	void Killed(GameObject * obj, GameObject * killer)
	{
		int id = Commands->Create_Conversation("T_NONKEY", 99, 2000, false);
		Commands->Join_Conversation(NULL, id);
		Commands->Start_Conversation(id, 100014);
		Commands->Monitor_Conversation(obj, id);
	}
};

DECLARE_SCRIPT(T_Key_Gate, "")
{
	void Action_Complete(GameObject * obj, int action_id, ActionCompleteReason reason)
	{
		if (action_id == 100015)
		{
			Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1003, 1);
		}
	}
	void Killed(GameObject * obj, GameObject * killer)
	{
		int id = Commands->Create_Conversation("T_KEY", 99, 2000, false);
		Commands->Start_Conversation(id, 100015);
		Commands->Monitor_Conversation(obj, id);
	}
};

DECLARE_SCRIPT(T_Alt_Gate, "")
{
	void Action_Complete(GameObject * obj, int action_id, ActionCompleteReason reason)
	{
		if (action_id == 100016)
		{
			Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1004, 1);
		}
	}
	void Killed(GameObject * obj, GameObject * killer)
	{
		int id = Commands->Create_Conversation("T_NONKEY", 99, 2000, false);
		Commands->Start_Conversation(id, 100016);
		Commands->Monitor_Conversation(obj, id);
	}
};

DECLARE_SCRIPT(T_Alt_Zone, "")
{
	void Entered(GameObject * obj, GameObject * enterer)
	{
		Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1004, 1);
	}
};

DECLARE_SCRIPT(T_Secondary_Gate, "")
{
	void Action_Complete(GameObject * obj, int action_id, ActionCompleteReason reason)
	{
		if (action_id == 100017)
		{
			Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1002, 1);
		}
	}
	void Killed(GameObject * obj, GameObject * killer)
	{
		int id = Commands->Create_Conversation("T_NONKEY", 99, 2000, false);
		Commands->Start_Conversation(id, 100017);
		Commands->Monitor_Conversation(obj, id);
	}
};

DECLARE_SCRIPT(T_Complete_Gate, "")
{
	void Action_Complete(GameObject * obj, int action_id, ActionCompleteReason reason)
	{
		switch (action_id)
		{
			case 100020:
				Commands->Mission_Complete(true);
				break;
			case 5:
				Commands->Mission_Complete(false);
				break;
		}
	}
	void Killed(GameObject * obj, GameObject * killer)
	{
		int conv = Commands->Create_Conversation("T_NONKEY", 99, 2000, false);
		Commands->Start_Conversation(conv, 100020);
		Commands->Monitor_Conversation(obj, conv);
	}
};

DECLARE_SCRIPT(T_Missing_Gate, "")
{
	void Action_Complete(GameObject * obj, int action_id, ActionCompleteReason reason)
	{
		if (action_id == 100021)
		{
			Commands->Mission_Complete(true);
		}
	}
	void Killed(GameObject * obj, GameObject * killer)
	{
		int id = Commands->Create_Conversation("T_GONE", 99, 2000, false);
		Commands->Start_Conversation(id, 100021);
		Commands->Monitor_Conversation(obj, id);
	}
};
'''


def build_scripts(source=SOURCE):
    import re
    rows = []
    declarations = list(re.finditer(r'DECLARE_SCRIPT\((\w+),', source))
    for index, match in enumerate(declarations):
        end = declarations[index + 1].start() if index + 1 < len(declarations) else len(source)
        rows.append({'name': match[1], 'owner': 'MissionT.cpp', 'line': source.count('\n', 0, match.start()) + 1,
                     'body': source[match.end():end]})
    return [Script(row, dict(CONSTANTS)) for row in rows]


def db(**flags):
    rows = {name.lower(): {'name': name, 'is_key': value, 'id': 1, 'category': 1, 'priority': 30, 'remarks': 1,
                           'source': 'fixture'} for name, value in flags.items()}
    return {'level': rows, 'global': {}, 'sources': []}


class ConditionEvaluation(unittest.TestCase):
    def test_three_valued_logic_and_negation(self):
        env = {'action_id': 100014}
        self.assertTrue(eval_cond('action_id == 100014', env, CONSTANTS))
        self.assertFalse(eval_cond('action_id == 5 || action_id == 6', env, CONSTANTS))
        self.assertIsNone(eval_cond('action_id == 100014 && already', env, CONSTANTS))
        self.assertFalse(eval_cond('action_id == 1 && already', env, CONSTANTS))
        self.assertFalse(eval_cond('!(action_id == 100014)', env, CONSTANTS))
        self.assertTrue(eval_cond('type >= 1000 && type <= 1025', {'type': 1011}, CONSTANTS))

    def test_else_branch_negates_and_switch_labels_become_equalities(self):
        code = 'if (a == 1) { x; } else { y; } switch (b) { case 1: case 2: z; break; default: w; }'
        out = []
        parse_statements(code, 0, len(code), (), out)
        by_text = {code[s:e].strip(): conds for s, e, conds in out}
        self.assertEqual(by_text['x;'], (('a == 1', False),))
        self.assertEqual(by_text['y;'], (('a == 1', True),))
        self.assertEqual(by_text['z;'], (('b == 1 || b == 2', False),))
        passes, _, anchored = path_state(by_text['y;'], {'a': 1}, CONSTANTS, ('a',))
        self.assertFalse(passes)
        passes, _, anchored = path_state(by_text['y;'], {'a': 2}, CONSTANTS, ('a',))
        self.assertTrue(passes and anchored)


class KeyFlagDecoding(unittest.TestCase):
    def test_is_key_flag_is_read_from_original_varid_13(self):
        def record(name, key):
            fields = (micro(0, name.encode() + b'\0') + micro(1, integer(7)) + micro(3, integer(0)) + micro(8, integer(1))
                      + micro(10, integer(30)) + micro(13, bytes([key])))
            return chunk(0x08090319, chunk(0x08090316, fields), True)
        payload = chunk(0x40700, chunk(0x08090318, integer(1) + record('KeyConv', 1) + record('PlainConv', 0), True), True)
        rows = conversation_flags(payload, conversations(chunks(payload), allow_legacy_category=False))
        self.assertEqual({r['name']: r['is_key'] for r in rows}, {'KeyConv': True, 'PlainConv': False})
        self.assertEqual({r['priority'] for r in rows}, {30})

    def test_key_state_mixed_missing_and_unknown(self):
        database = db(A=True, B=False)
        gate = {'names': ['A', 'B']}
        self.assertEqual(key_state(gate, database)[0], 'mixed')
        self.assertEqual(key_state({'names': ['A']}, database)[0], 'key')
        self.assertEqual(key_state({'names': ['Z']}, database)[0], 'missing')
        self.assertEqual(key_state({'names': []}, database)[0], 'unknown')


class GateClassification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = analyse_mission('MT', build_scripts(), db(T_NONKEY=False, T_KEY=True))
        cls.by_script = {g['script']: g for g in cls.result['gates']}

    def test_all_six_gates_are_found(self):
        self.assertEqual(sorted(self.by_script), ['T_Alt_Gate', 'T_Complete_Gate', 'T_Key_Gate', 'T_Missing_Gate',
                                                   'T_Secondary_Gate', 'T_Sole_Emitter'])
        self.assertEqual(len(self.result['gates']), 6)

    def test_non_key_sole_emitter_of_primary_objective_is_at_risk(self):
        gate = self.by_script['T_Sole_Emitter']
        self.assertEqual(gate['classification'], 'AT RISK')
        self.assertEqual(gate['key_state'], 'non-key')
        self.assertEqual(gate['actions'], [100014])
        self.assertIn(['status', 1001, 1], [p['signature'] for p in gate['progress']])
        self.assertTrue(gate['progress'][0]['via'].startswith('receiver T_Controller:'))
        self.assertEqual(gate['progress'][0]['alternative_count'], 0)

    def test_key_conversation_is_safe(self):
        self.assertEqual(self.by_script['T_Key_Gate']['classification'], 'SAFE (key)')

    def test_independent_emitter_makes_non_key_gate_safe(self):
        gate = self.by_script['T_Alt_Gate']
        self.assertEqual(gate['classification'], 'SAFE (alt path)')
        self.assertEqual(gate['progress'][0]['alternatives'][0]['script'], 'T_Alt_Zone')

    def test_secondary_objective_is_low(self):
        gate = self.by_script['T_Secondary_Gate']
        self.assertEqual(gate['classification'], 'LOW')
        self.assertEqual(gate['progress'][0]['significance'], 'secondary')

    def test_switch_case_gates_mission_complete_true_but_not_the_false_case(self):
        gate = self.by_script['T_Complete_Gate']
        self.assertEqual(gate['classification'], 'AT RISK')
        self.assertEqual([p['signature'] for p in gate['progress']], [['complete', 1]])

    def test_missing_conversation_name_is_reported_before_key_state(self):
        gate = self.by_script['T_Missing_Gate']
        self.assertEqual(gate['key_state'], 'missing')
        self.assertEqual(gate['classification'], 'NAME MISSING')

    def test_markdown_lists_at_risk_gates_and_counts(self):
        report = {'scripts_directory': 'fixture', 'missions': {'MT': self.result}, 'limits': ['fixture limit']}
        text = render_markdown(report)
        self.assertIn('## AT RISK gates', text)
        self.assertIn('`T_Sole_Emitter`', text)
        self.assertIn('| MT | 6 | 2 |', text)


class FixedDetection(unittest.TestCase):
    MONITOR_FIRST = SOURCE.replace(
        '''		Commands->Join_Conversation(NULL, id);
		Commands->Start_Conversation(id, 100014);
		Commands->Monitor_Conversation(obj, id);''',
        '''		Commands->Join_Conversation(NULL, id);
		Commands->Monitor_Conversation(obj, id);
		Commands->Start_Conversation(id, 100014);''')
    ADDED_EMITTER = SOURCE + '''
DECLARE_SCRIPT(T_Resend, "")
{
	void Timer_Expired(GameObject * obj, int timer_id)
	{
		Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1001, 1);
	}
	void Entered(GameObject * obj, GameObject * enterer)
	{
		Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1001, 1);
	}
};
'''

    def test_monitor_registered_before_start_neutralises_key_preemption(self):
        self.assertNotEqual(self.MONITOR_FIRST, SOURCE)
        result = analyse_mission('MT', build_scripts(self.MONITOR_FIRST), db(T_NONKEY=False, T_KEY=True))
        gate = {g['script']: g for g in result['gates']}['T_Sole_Emitter']
        self.assertTrue(gate['monitor_before_start'])
        self.assertEqual(gate['classification'], 'FIXED')
        self.assertIn('Monitor_Conversation precedes Start_Conversation', gate['fixed_by'])

    def test_baseline_at_risk_becomes_fixed_when_a_later_script_adds_an_independent_emitter(self):
        database = db(T_NONKEY=False, T_KEY=True)
        baseline_scripts, patched_scripts = build_scripts(SOURCE), build_scripts(self.ADDED_EMITTER)
        baseline = analyse_mission('MT', baseline_scripts, database)
        entry = analyse_mission('MT', patched_scripts, database)
        gate = {g['script']: g for g in entry['gates']}['T_Sole_Emitter']
        self.assertEqual(gate['classification'], 'SAFE (alt path)')
        annotate_against_baseline(entry, baseline, patched_scripts, baseline_scripts,
                                  {'scripts-a38-fixture': {'Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1001, 1);',
                                                           'void Timer_Expired(GameObject * obj, int timer_id)'}})
        # The gate script is unchanged; the independent emitter lives in a new script and is attributed.
        self.assertFalse(gate['script_changed'])
        self.assertEqual(gate['classification'], 'FIXED')
        self.assertEqual(gate['baseline_class'], 'AT RISK')
        self.assertEqual(gate['patches'], ['scripts-a38-fixture'])

    def test_changed_gate_script_with_removed_risk_is_marked_fixed_and_attributed(self):
        database = db(T_NONKEY=False, T_KEY=True)
        patched_source = SOURCE.replace('''		if (action_id == 100014)
		{
			Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1001, 1);
		}''', '''		if (action_id == 100014)
		{
			Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1001, 1);
		}
		Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1001, 1);  // resend on kill''')
        patched_source = patched_source.replace('''		int id = Commands->Create_Conversation("T_NONKEY", 99, 2000, false);
		Commands->Join_Conversation(NULL, id);''', '''		Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1001, 1);
		int id = Commands->Create_Conversation("T_NONKEY", 99, 2000, false);
		Commands->Join_Conversation(NULL, id);''')
        baseline_scripts, patched_scripts = build_scripts(SOURCE), build_scripts(patched_source)
        baseline = analyse_mission('MT', baseline_scripts, database)
        entry = analyse_mission('MT', patched_scripts, database)
        lines = {'scripts-a38-fixture': {'Commands->Send_Custom_Event(obj, Commands->Find_Object(1), 1001, 1);',
                                         'int id = Commands->Create_Conversation("T_NONKEY", 99, 2000, false);'}}
        annotate_against_baseline(entry, baseline, patched_scripts, baseline_scripts, lines)
        gate = {g['script']: g for g in entry['gates']}['T_Sole_Emitter']
        self.assertTrue(gate['script_changed'])
        self.assertEqual(gate['classification'], 'FIXED')
        self.assertEqual(gate['patches'], ['scripts-a38-fixture'])
        self.assertEqual(gate['baseline_class'], 'AT RISK')


class UnclassifiedWithoutDatabase(unittest.TestCase):
    def test_without_database_nothing_is_called_safe_or_at_risk(self):
        result = analyse_mission('MT', build_scripts(), None)
        classes = {g['classification'] for g in result['gates']}
        self.assertTrue(classes <= {'REVIEW', 'LOW', 'NO EFFECT'})


if __name__ == '__main__':
    unittest.main()
