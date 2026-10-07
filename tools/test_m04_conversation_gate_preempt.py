"""M04 briefing steps survive a key-conversation preemption.

Source contract for scripts-a38-m04-conversation-gate-preempt.patch. The M04
objective controller and the torpedo announce zone start non-key briefings
whose objective step runs only from Action_Complete.
ActiveConversationClass::Start_Conversation stops a non-key conversation at
once (INTERRUPTED) while a key conversation plays. The patch registers the
monitor before Start_Conversation, accepts that stop as the briefing's end
only while `conversation_starting` names the briefing, and runs each
controller step once behind a saved flag.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MISSION04 = ROOT / 'staging/scripts/Mission04.cpp'
UPSTREAM_MISSION04 = ROOT / 'upstream/CnC_Renegade/Code/Scripts/Mission04.cpp'
ACTIVE = ROOT / 'staging/combat/activeconversation.cpp'
MANAGER = ROOT / 'staging/combat/conversationmgr.cpp'
STAGE = ROOT / 'tools/stage_sources.sh'
PATCH = 'scripts-a38-m04-conversation-gate-preempt.patch'
CONTROLLER = 'M04_Objective_Controller_JDG'
ZONE = 'M04_Start_TorpedoObjective_Zone_JDG'

# variable, conversation, step flag (None: no new flag), save id, objective added by the step
CONTROLLER_SITES = (
    ('missionIntroConv', 'M04_Mission_Start_Conversation', 'mission_intro_step_done', 49, 100),
    ('prisonKeyIntroConv', 'M04_Add_PrisonKey_Objective', 'prison_key_step_done', 50, 110),
    ('engineIntroConv', 'M04_Add_EngineRoom_Objective_Conversation', 'engine_room_step_done', 51, 200),
    ('missileConv', 'M04_Add_MissileRoom_Objective_Conversation', 'missile_objective_activated', 48, 300),
    ('firstmateConv', 'M04_Add_FirstMate_Objective_JDG', 'first_mate_step_done', 52, 600),
    ('protectPOWsConv', 'M04_Protect_The_Prisoners_Conversation', 'protect_pows_step_done', 53, 800),
    ('medlab_conv', 'M04_Eva_Tells_Where_Guard_Is', None, None, None),
)
ACCEPT = (r'case ACTION_COMPLETE_CONVERSATION_INTERRUPTED:\s*'
          r'case ACTION_COMPLETE_CONVERSATION_UNABLE_TO_INIT:\s*'
          r'case ACTION_COMPLETE_CONVERSATION_ENDED:[^\n]*\n\s*'
          r'if \(complete_reason == ACTION_COMPLETE_CONVERSATION_ENDED \|\| '
          r'\(conversation_starting != 0 && action_id == conversation_starting\)\)\s*\{')


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


def monitored_start(text, variable):
    """Offsets of the Create/Monitor/guard/Start sequence for `variable`."""
    create = text.index(variable + ' = Commands->Create_Conversation(')
    monitor = text.index('Commands->Monitor_Conversation (obj, %s);' % variable, create)
    guard = text.index('conversation_starting = %s;' % variable, create)
    start = text.index('Commands->Start_Conversation( %s,' % variable, create)
    return create, monitor, guard, start


class M04ConversationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MISSION04.read_text(errors='replace')
        cls.controller = script_body(cls.source, CONTROLLER)
        cls.zone = script_body(cls.source, ZONE)

    def test_controller_monitors_before_start(self):
        for variable, conversation, _, _, _ in CONTROLLER_SITES:
            with self.subTest(conversation=conversation):
                # (the captain step reuses the mission-start lines unmonitored as int reminderConv)
                assigned = re.findall(r'(?<!int )\b(\w+) = Commands->Create_Conversation\( "%s"' % conversation,
                                      self.controller)
                self.assertEqual(assigned, [variable])
                create, monitor, guard, start = monitored_start(self.controller, variable)
                self.assertIn('"%s"' % conversation, self.controller[create:monitor])
                self.assertLess(create, monitor)
                self.assertLess(monitor, guard)
                self.assertLess(guard, start)
                after = self.controller[start:start + 200]
                self.assertRegex(after, r'Start_Conversation\( %s,\s*%s \);\s*\n\s*Briefing_Start_Done\( obj, %s \);'
                                 % (variable, variable, variable))
        done = method(self.controller, 'Briefing_Start_Done')
        self.assertRegex(done, r'if \(conv < 0\)\s*\{\s*Action_Complete\( obj, conv, '
                               r'ACTION_COMPLETE_CONVERSATION_UNABLE_TO_INIT \);\s*\}\s*conversation_starting = 0;')

    def test_no_controller_or_zone_start_keeps_the_late_monitor(self):
        late = re.compile(r'Start_Conversation\( *(\w+), *\1 *\);\s*\n\s*Commands->Monitor_Conversation \(obj, \1\);')
        self.assertEqual(late.findall(self.controller), [])
        self.assertEqual(late.findall(self.zone), [])

    def test_preempted_stop_accepted_only_inside_start(self):
        for body in (self.controller, self.zone):
            complete = method(body, 'Action_Complete')
            self.assertRegex(complete, ACCEPT)
            self.assertEqual(complete.count('case ACTION_COMPLETE_CONVERSATION_ENDED'), 1)
            self.assertNotIn('complete_reason =', complete.replace('complete_reason ==', ''))
            # transient: never saved, cleared in Created
            self.assertNotRegex(body, r'SAVE_VARIABLE\s*\(\s*conversation_starting')
            self.assertIn('conversation_starting = 0;', method(body, 'Created'))

    def test_steps_run_once_behind_saved_flags(self):
        ids = [int(v) for v in re.findall(r'SAVE_VARIABLE\s*\(\s*\w+\s*,\s*(\d+)\s*\)', self.controller)]
        names = re.findall(r'SAVE_VARIABLE\s*\(\s*(\w+)\s*,', self.controller)
        self.assertEqual(len(ids), len(set(ids)), 'duplicate SAVE_VARIABLE id')
        self.assertEqual(sorted(ids), list(range(1, 56)))
        # firstmateConv was already saved twice (ids 37 and 45) by the retail script
        self.assertEqual([n for n in set(names) if names.count(n) > 1], ['firstmateConv'])
        complete = method(self.controller, 'Action_Complete')
        created = method(self.controller, 'Created')
        for variable, conversation, flag, save_id, objective in CONTROLLER_SITES:
            if flag is None:
                continue
            with self.subTest(conversation=conversation):
                self.assertRegex(self.controller, r'SAVE_VARIABLE\s*\(\s*%s\s*,\s*%d\s*\)' % (flag, save_id))
                self.assertIn('%s' % flag, created)
                branch = re.search(r'if \(action_id == %s && %s == false\)[^\n]*\n\s*\{\s*%s = true;'
                                   % (variable, flag, flag), complete)
                self.assertIsNotNone(branch)
                add = 'Commands->Add_Objective( %d,' % objective
                add = add if add in complete else 'Commands->Add_Objective(  %d,' % objective
                self.assertLess(branch.start(), complete.index(add))
        # the missile fallback (441) is kept as a backstop
        self.assertIn('MISSILE_OBJECTIVE_FALLBACK = 441', self.controller)
        self.assertRegex(self.controller, r'Action_Complete\( obj, missileConv, ACTION_COMPLETE_CONVERSATION_ENDED \);')

    def test_torpedo_zone(self):
        entered = method(self.zone, 'Entered')
        create, monitor, guard, start = monitored_start(entered, 'missionIntroConv')
        self.assertLess(monitor, guard)
        self.assertLess(guard, start)
        self.assertRegex(entered[start:], r'if \(missionIntroConv < 0\)\s*\{\s*Action_Complete\( obj, missionIntroConv, '
                                          r'ACTION_COMPLETE_CONVERSATION_UNABLE_TO_INIT \);\s*\}\s*conversation_starting = 0;')
        # the zone starts its announcement once: conversationPlaying latches before the start and is saved
        self.assertLess(entered.index('conversationPlaying = true;'), create)
        self.assertRegex(self.zone, r'SAVE_VARIABLE\s*\(\s*conversationPlaying\s*,\s*1\s*\)')
        complete = method(self.zone, 'Action_Complete')
        self.assertIn('Send_Custom_Event( obj, Commands->Find_Object (M04_OBJECTIVE_CONTROLLER_JDG), 0, 450, 0 );',
                      complete)

    def test_late_announce_skips_markers_of_sabotaged_torpedoes(self):
        custom = method(self.controller, 'Custom')
        for flag, marker, target, param in (('torpedo_01_done', 401, 100409, 'torpedo_01_sabotaged'),
                                            ('torpedo_02_done', 402, 100410, 'torpedo_02_sabotaged')):
            with self.subTest(marker=marker):
                self.assertRegex(custom, r'if \(%s == false\)\s*\{\s*Commands->Add_Radar_Marker \( %d, '
                                         r'Commands->Get_Position\( Commands->Find_Object \( %d \)\)' % (flag, marker, target))
                self.assertRegex(custom, r'else if \(param == %s\)\s*\{\s*%s = true;\s*Commands->Clear_Radar_Marker \( %d \);'
                                 % (param, flag, marker))

    def test_engine_assumptions(self):
        active = ACTIVE.read_text(errors='replace')
        start = function(active, 'ActiveConversationClass::Start_Conversation (void)')
        self.assertRegex(start, r'Is_Key_Conversation_Playing \(\)\) \{\s*'
                         r'Stop_Conversation \(ACTION_COMPLETE_CONVERSATION_INTERRUPTED\);')
        self.assertNotIn('Notify_Monitors', start)
        self.assertNotIn('MonitorArray', start)
        stop = function(active, 'ActiveConversationClass::Stop_Conversation (ActionCompleteReason reason)')
        self.assertRegex(stop, r'if \(Is_Finished \(\)\) \{\s*return ;')
        self.assertEqual(stop.count('Notify_Monitors_On_End (reason);'), 1)
        # A level reset also stops active conversations with INTERRUPTED: the reason
        # alone must not run a briefing step, hence the conversation_starting guard.
        manager = MANAGER.read_text(errors='replace')
        reset = function(manager, 'ConversationMgrClass::Reset_Active_Conversations (void)')
        self.assertIn('Stop_Conversation (ACTION_COMPLETE_CONVERSATION_INTERRUPTED);', reset)

    def test_patch_registered_once_after_existing_m04_patches(self):
        stage = STAGE.read_text()
        self.assertEqual(stage.count(PATCH), 1)
        self.assertTrue((ROOT / 'port/patches' / PATCH).is_file())
        for earlier in ('scripts-a36-m04-save-variable-ids.patch',
                        'scripts-a38-m04-torpedo-objective-race.patch',
                        'scripts-a38-m04-missile-briefing-drop.patch'):
            self.assertLess(stage.index(earlier), stage.index(PATCH))
        patch = (ROOT / 'port/patches' / PATCH).read_text()
        self.assertEqual(re.findall(r'^\+\+\+ (\S+)', patch, re.M), ['b/Mission04.cpp'])

    def test_retail_site_count(self):
        if not UPSTREAM_MISSION04.is_file():
            self.skipTest('upstream source not present in this checkout')
        late = re.compile(r'Start_Conversation\( *(\w+), *\1 *\);\s*\n\s*Commands->Monitor_Conversation \(obj, \1\);')
        upstream = UPSTREAM_MISSION04.read_text(errors='replace')
        self.assertEqual(sorted(late.findall(script_body(upstream, CONTROLLER))),
                         sorted(site[0] for site in CONTROLLER_SITES))
        self.assertEqual(late.findall(script_body(upstream, ZONE)), ['missionIntroConv'])


if __name__ == '__main__':
    unittest.main()
