"""M10 follow-up fixes after the objective-conversation resend (2026-10-07).

Source contracts for four staging patches on scripts/Mission10.cpp:
- scripts-a38-m10-ne-gate-briefing-monitor-first: M10CON018 (adds primary
  1006) registers its monitor before Start_Conversation.
- scripts-a38-m10-attack-target-save-ids: attack/target id tables set in
  Created() are saved under unused SAVE_VARIABLE ids.
- scripts-a38-m10-paradrop-param-buffer: M10_Chinook_ParaDrop formats the
  owner id into a bounded 16-byte buffer.
- scripts-a38-m10-primary-add-before-accomplish: the objective controller adds
  a primary before marking it accomplished.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MISSION10 = ROOT / 'staging/scripts/Mission10.cpp'
OBJECTIVES = ROOT / 'staging/combat/objectives.cpp'
STAGE = ROOT / 'tools/stage_sources.sh'
PREVIOUS = 'scripts-a38-m10-objective-conversation-resend.patch'
PATCHES = (
    'scripts-a38-m10-ne-gate-briefing-monitor-first.patch',
    'scripts-a38-m10-attack-target-save-ids.patch',
    'scripts-a38-m10-paradrop-param-buffer.patch',
    'scripts-a38-m10-primary-add-before-accomplish.patch',
)
PRIMARIES = (1001, 1002, 1003, 1004, 1005, 1006, 1007, 1012)


def script_body(source, name):
    start = re.search(r'DECLARE_SCRIPT\s*\(\s*' + name + r'\s*,', source)
    assert start is not None, name
    following = re.search(r'\nDECLARE_SCRIPT\s*\(', source[start.end():])
    end = start.end() + following.start() if following else len(source)
    return source[start.start():end]


def block(text, opener):
    """Return the brace block that starts at the first '{' after opener."""
    start = text.index(opener)
    index = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += {'{': 1, '}': -1}.get(text[index], 0)
        index += 1
    return text[start:index]


def save_ids(body):
    return {name: int(value) for name, value in
            re.findall(r'SAVE_VARIABLE\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)', body)}


class M10FollowUpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MISSION10.read_text(errors='replace')

    def test_ne_gate_briefing_monitor_precedes_start(self):
        body = script_body(self.source, 'M10_Conversation_Zone')
        case = block(body, 'case 18:')
        create = case.index('Create_Conversation("M10CON018"')
        monitor = case.index('Monitor_Conversation(obj, id);')
        start = case.index('Start_Conversation(id, 100018);')
        self.assertLess(case.index('already_entered = true;'), create)
        self.assertLess(create, monitor)
        self.assertLess(monitor, start)
        self.assertEqual(case.count('Monitor_Conversation(obj, id);'), 1)
        self.assertRegex(case[start:], r'if \(id < 0\)\s*\{\s*Action_Complete\(obj, 100018, '
                         r'ACTION_COMPLETE_CONVERSATION_UNABLE_TO_INIT\);')
        complete = block(body, 'void Action_Complete')
        handler = block(complete, 'if (action_id == 100018)')
        self.assertIn('Send_Custom_Event(obj, obj_con, 1006, 3);', handler)
        self.assertNotIn('reason', handler)
        # 1006 is added nowhere else, so this briefing is the only source of its guidance.
        self.assertEqual(self.source.count('1006, 3)'), 1)

    def test_attack_tables_saved_with_unique_ids(self):
        expected = {
            'M10_Stealth_Attack_01': {'attack_loc': 9, 'same': 8},
            'M10_Stealth_Attack_02': {'attack_loc': 8, 'same': 9},
            'M10_Mammoth_Attack': {'target': 4},
        }
        for script, wanted in expected.items():
            with self.subTest(script=script):
                body = script_body(self.source, script)
                ids = save_ids(body)
                values = [int(v) for v in re.findall(r'SAVE_VARIABLE\s*\(\s*\w+\s*,\s*(\d+)\s*\)', body)]
                self.assertEqual(len(values), len(set(values)), 'duplicate SAVE_VARIABLE id')
                self.assertTrue(all(0 < value < 256 for value in values))
                for name, save_id in wanted.items():
                    self.assertEqual(ids.get(name), save_id)
                created = block(body, 'void Created')
                for name in wanted:
                    self.assertRegex(created, r'\b%s\s*(\[\s*\d+\s*\])?\s*=' % name)
        # Auto_Save_Variable drops anything over 250 bytes.
        for script, array, count in (('M10_Stealth_Attack_01', 'attack_loc', 13),
                                     ('M10_Stealth_Attack_02', 'attack_loc', 13),
                                     ('M10_Mammoth_Attack', 'target', 4)):
            body = script_body(self.source, script)
            self.assertRegex(body, r'int\s+%s\s*\[\s*%d\s*\]' % (array, count))
            self.assertLessEqual(count * 4, 250)

    def test_paradrop_parameter_buffer_bounded(self):
        body = script_body(self.source, 'M10_Chinook_ParaDrop')
        self.assertIn('char params[16];', body)
        self.assertIn('snprintf(params, sizeof(params), "%d", Commands->Get_ID(obj));', body)
        self.assertNotRegex(body, r'\bsprintf\s*\(\s*params')
        self.assertGreaterEqual(16, len(str(-2**31)) + 1)

    def test_primary_added_before_accomplished(self):
        body = script_body(self.source, 'M10_Objective_Controller')
        custom = block(body, 'void Custom')
        add = custom.index('Add_An_Objective(type);')
        accomplish = custom.index('Commands->Set_Objective_Status(type, OBJECTIVE_STATUS_ACCOMPLISHED);')
        count = custom.index('++primary_count')
        self.assertLess(add, accomplish)
        self.assertLess(accomplish, count)
        guard = custom.rindex('if (type < 1008 || type == 1012)', 0, add)
        self.assertNotIn('}', custom[guard:add])
        self.assertEqual(custom.count('Add_An_Objective(type);'), 2)  # case 3 and the new site
        helper = block(body, 'void Add_An_Objective')
        for objective in PRIMARIES:
            case = block(helper, 'case %d:' % objective)
            self.assertIn('Add_Objective(%d, OBJECTIVE_TYPE_PRIMARY' % objective, case)
            self.assertNotIn('Send_Custom_Event', case)
        # Duplicate adds return before creating a second objective or a message.
        objectives = OBJECTIVES.read_text(errors='replace')
        add_fn = block(objectives, 'void\tObjectiveManager::Add_Objective(')
        self.assertRegex(add_fn, r'if \( Find_Objective\( id \) != NULL \) \{\s*'
                         r'Debug_Say\(\( "Adding a duplicate Objective ID\\n" \)\);\s*return;')

    def test_patches_registered_after_resend_patch(self):
        stage = STAGE.read_text()
        previous = stage.index(PREVIOUS)
        for patch in PATCHES:
            with self.subTest(patch=patch):
                self.assertEqual(stage.count(patch), 1)
                self.assertLess(previous, stage.index(patch))
                text = (ROOT / 'port/patches' / patch).read_text()
                self.assertEqual(re.findall(r'^\+\+\+ (\S+)', text, re.M), ['b/Mission10.cpp'])
        positions = [stage.index(patch) for patch in PATCHES]
        self.assertEqual(positions, sorted(positions))


if __name__ == '__main__':
    unittest.main()
