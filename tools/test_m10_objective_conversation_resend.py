"""M10 objectives 1001/1002/1004/1005 survive a key-conversation preemption.

Source contract for scripts-a38-m10-objective-conversation-resend.patch. The
four follow-up conversations are not key, so ActiveConversationClass::
Start_Conversation stops them at once while a key conversation plays. The
patch registers the monitor before Start_Conversation, so that stop reaches
Action_Complete, and guards each objective send with a saved flag.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MISSION10 = ROOT / 'staging/scripts/Mission10.cpp'
UPSTREAM_MISSION10 = ROOT / 'upstream/CnC_Renegade/Code/Scripts/Mission10.cpp'
ACTIVE = ROOT / 'staging/combat/activeconversation.cpp'
COMMANDS = ROOT / 'staging/combat/scriptcommands.cpp'
STAGE = ROOT / 'tools/stage_sources.sh'
PATCH = 'scripts-a38-m10-objective-conversation-resend.patch'

# script, trigger, conversation, action id, objective, guard flag, save id
SITES = (
    ('M10_Power_Plant', 'Killed', 'M10CON014', 100014, 1001, 'objective_sent', 2),
    ('M10_Con_Yard', 'Killed', 'M10CON005', 100005, 1002, 'objective_sent', 1),
    ('M10_Comm_Center', 'Killed', 'M10CON011', 100011, 1004, 'objective_sent', 1),
    ('M10_Gate_Check', 'Poked', 'M10CON002', 100002, 1005, 'objective_1005_sent', 4),
)


def script_body(source, name):
    start = re.search(r'DECLARE_SCRIPT\s*\(\s*' + name + r'\s*,', source)
    assert start is not None, name
    following = re.search(r'\nDECLARE_SCRIPT\s*\(', source[start.end():])
    end = start.end() + following.start() if following else len(source)
    return source[start.start():end]


def method(body, name):
    """Return one member function, matched by brace depth."""
    match = re.search(r'void\s+' + name + r'\s*\([^)]*\)\s*\{', body)
    assert match is not None, name
    depth, index = 1, match.end()
    while depth:
        depth += {'{': 1, '}': -1}.get(body[index], 0)
        index += 1
    return body[match.start():index]


def function(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth, index = 1, brace + 1
    while depth:
        depth += {'{': 1, '}': -1}.get(source[index], 0)
        index += 1
    return source[start:index]


class M10ObjectiveConversationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MISSION10.read_text(errors='replace')

    def test_monitor_registered_before_start(self):
        for script, trigger, conversation, action, _, _, _ in SITES:
            with self.subTest(script=script):
                body = method(script_body(self.source, script), trigger)
                create = body.index('Create_Conversation("%s"' % conversation)
                start = body.index('Start_Conversation(id, %d);' % action)
                monitor = body.index('Monitor_Conversation(obj, id);', create)
                self.assertLess(create, monitor)
                self.assertLess(monitor, start)
                self.assertEqual(body.count('Start_Conversation(id, %d);' % action), 1)
                fallback = body[start:]
                self.assertRegex(fallback, r'if \(id < 0\)\s*\{\s*Action_Complete\(obj, %d, '
                                 r'ACTION_COMPLETE_CONVERSATION_UNABLE_TO_INIT\);' % action)

    def test_objective_sent_once_behind_saved_flag(self):
        for script, _, _, action, objective, flag, save_id in SITES:
            with self.subTest(script=script):
                body = script_body(self.source, script)
                ids = [int(value) for value in re.findall(r'SAVE_VARIABLE\s*\(\s*\w+\s*,\s*(\d+)\s*\)', body)]
                self.assertEqual(len(ids), len(set(ids)), 'duplicate SAVE_VARIABLE id')
                self.assertRegex(body, r'SAVE_VARIABLE\s*\(\s*%s\s*,\s*%d\s*\)' % (flag, save_id))
                self.assertIn('%s = false;' % flag, method(body, 'Created'))
                complete = method(body, 'Action_Complete')
                send = 'Send_Custom_Event(obj, obj_con, %d, 1);' % objective
                self.assertEqual(complete.count(send), 1)
                self.assertEqual(body.count(send), 1, 'objective must have one sender')
                guard = complete.index('!%s' % flag)
                assign = complete.index('%s = true;' % flag)
                self.assertLess(complete.index('action_id == %d' % action), guard)
                self.assertLess(guard, assign)
                self.assertLess(assign, complete.index(send))

    def test_engine_preemption_and_single_notify_assumptions(self):
        active = ACTIVE.read_text(errors='replace')
        start = function(active, 'ActiveConversationClass::Start_Conversation (void)')
        self.assertRegex(start, r'Is_Key_Conversation_Playing \(\)\) \{\s*'
                         r'Stop_Conversation \(ACTION_COMPLETE_CONVERSATION_INTERRUPTED\);')
        self.assertNotIn('MonitorArray', start)
        register = function(active, 'ActiveConversationClass::Register_Monitor (ScriptableGameObj *game_obj)')
        self.assertNotIn('State', register)
        stop = function(active, 'ActiveConversationClass::Stop_Conversation (ActionCompleteReason reason)')
        self.assertRegex(stop, r'if \(Is_Finished \(\)\) \{\s*return ;')
        self.assertEqual(stop.count('Notify_Monitors_On_End (reason);'), 1)
        notify = function(active, 'ActiveConversationClass::Notify_Monitors_On_End (ActionCompleteReason reason)')
        self.assertIn('->Action_Complete (game_obj, ActionID, reason);', notify)
        self.assertNotIn('if (reason', notify)
        commands = COMMANDS.read_text(errors='replace')
        monitor = function(commands, 'void\tMonitor_Conversation( GameObject * object, int active_conversation_id )')
        self.assertIn('Find_Active_Conversation( active_conversation_id);', monitor)
        self.assertIn('Register_Monitor( object );', monitor)

    def test_other_conversation_sites_keep_retail_order(self):
        if not UPSTREAM_MISSION10.is_file():
            self.skipTest('upstream source not present in this checkout')
        pattern = re.compile(r'Start_Conversation\((\w+), \d+\);\s*\n\s*Commands->Monitor_Conversation\(obj, \1\);')
        upstream = len(pattern.findall(UPSTREAM_MISSION10.read_text(errors='replace')))
        staged = len(pattern.findall(self.source))
        self.assertEqual(upstream - staged, len(SITES))

    def test_patch_registered_once_after_existing_m10_patches(self):
        stage = STAGE.read_text()
        self.assertEqual(stage.count(PATCH), 1)
        self.assertTrue((ROOT / 'port/patches' / PATCH).is_file())
        for earlier in ('scripts-a35-apache-controller-bounds.patch',
                        'scripts-a36-m10-gate-check-save-flags.patch',
                        'scripts-a36-m10-stealth-attack-loc-bounds.patch'):
            self.assertLess(stage.index(earlier), stage.index(PATCH))
        patch = (ROOT / 'port/patches' / PATCH).read_text()
        self.assertEqual(re.findall(r'^\+\+\+ (\S+)', patch, re.M), ['b/Mission10.cpp'])


if __name__ == '__main__':
    unittest.main()
