"""TUT-R1-03 SCRIPT_THINK_COST: invariants behind the tutorial script-cost
conclusion, the RVSC1 script-cost watch line, and its log summariser.

Pure Python: reads staged/port sources and synthetic log lines only. No
compiler, game, device or retail data is used.
"""
from pathlib import Path
import importlib.util
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'upstream/CnC_Renegade/Code'
MISSION00 = ROOT / 'staging/scripts/Mission00.cpp'
OBSERVER_H = ROOT / 'staging/combat/gameobjobserver.h'
SCRIPTCOMMANDS = ROOT / 'staging/combat/scriptcommands.cpp'
SCRIPTZONE = ROOT / 'staging/combat/scriptzone.cpp'
LOOKUP = ROOT / 'port/developer/a35_script_lookup_telemetry.cpp'
RUNTIME = ROOT / 'port/platform/vita/a31_vita_runtime.cpp'
PROFILE = ROOT / 'port/platform/vita/renegade_vita_frame_profile.cpp'
REPORT_TOOL = ROOT / 'tools/tut1_script_cost_report.py'

# Script names saved in M00_Tutorial.mix plus the scripts the tutorial
# attaches at runtime (reports/M00_AGGRESSIVE_DISCOVERY.md).
M00_TOOLKIT_SCRIPTS = {
    'Test_DAK.cpp': 'M00_BUILDING_EXPLODE_NO_DAMAGE_DAK',
    'Toolkit_Powerup.cpp': 'M00_Soldier_Powerup_Grant',
    'Toolkit_Objects.cpp': 'M00_Disable_Transition',
    'Toolkit.cpp': 'M00_Disable_Physical_Collision_JDG',
}
OBSERVER_EVENTS = {
    'Get_Name', 'Attach', 'Detach', 'Created', 'Destroyed', 'Killed', 'Damaged',
    'Custom', 'Sound_Heard', 'Enemy_Seen', 'Action_Complete', 'Timer_Expired',
    'Animation_Complete', 'Poked', 'Entered', 'Exited',
}
# ScriptCommands whose cost scales with object count (a GameObjManager list
# walk or a physics-scene collection).
OBJECT_COLLECTION_COMMANDS = ('Find_Random_Simple_Object', 'Get_A_Star', 'Find_Closest_Soldier',
                      'Find_Nearest_Building_To_Pos', 'Find_Nearest_Building')


def script_blocks(source):
    """Map DECLARE_SCRIPT name -> body text (brace matched)."""
    blocks = {}
    for match in re.finditer(r'DECLARE_SCRIPT\s*\(\s*(\w+)\s*,', source):
        start = source.index('{', match.end())
        depth = 0
        for index in range(start, len(source)):
            if source[index] == '{':
                depth += 1
            elif source[index] == '}':
                depth -= 1
                if depth == 0:
                    blocks[match.group(1)] = source[start:index + 1]
                    break
    return blocks


def method_body(block, name):
    match = re.search(r'void\s+%s\s*\([^)]*\)\s*\{' % name, block)
    if match is None:
        return ''
    depth = 0
    for index in range(match.end() - 1, len(block)):
        if block[index] == '{':
            depth += 1
        elif block[index] == '}':
            depth -= 1
            if depth == 0:
                return block[match.end() - 1:index + 1]
    raise AssertionError('unterminated %s' % name)


def function_body(source, signature):
    start = source.index(signature)
    open_brace = source.index('{', start)
    depth = 0
    for index in range(open_brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[open_brace:index + 1]
    raise AssertionError('unterminated ' + signature)


def split_args(text):
    args, depth, current = [], 0, ''
    for char in text:
        if char == ',' and depth == 0:
            args.append(current.strip())
            current = ''
            continue
        depth += char == '('
        depth -= char == ')'
        current += char
    args.append(current.strip())
    return args


def start_timer_calls(block):
    calls = []
    for match in re.finditer(r'Commands->Start_Timer\s*\(', block):
        depth, index = 1, match.end()
        while depth:
            depth += block[index] == '('
            depth -= block[index] == ')'
            index += 1
        calls.append(split_args(block[match.end():index - 1]))
    return calls


def load_report_tool():
    spec = importlib.util.spec_from_file_location('tut1_script_cost_report', REPORT_TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TutorialScriptCadenceTests(unittest.TestCase):
    def test_observer_interface_has_no_per_frame_callback(self):
        header = OBSERVER_H.read_text()
        callbacks = set(re.findall(r'virtual\s+(?:const\s+char\s*\*|void)\s+(\w+)\s*\(', header))
        self.assertEqual(callbacks, OBSERVER_EVENTS)
        upstream = UPSTREAM / 'Combat/gameobjobserver.h'
        if upstream.is_file():
            self.assertEqual(upstream.read_bytes(), OBSERVER_H.read_bytes())

    def test_tutorial_mission_scripts_have_no_fast_repeating_timers(self):
        blocks = {name: body for name, body in script_blocks(MISSION00.read_text()).items()
                  if name.startswith('MTU_')}
        self.assertIn('MTU_Tutorial_Controller', blocks)
        self.assertIn('MTU_Trigger_Zone', blocks)
        literal, computed = [], set()
        for name, body in blocks.items():
            for args in start_timer_calls(body):
                self.assertEqual(len(args), 4, (name, args))
                duration = args[2]
                number = re.fullmatch(r'([0-9]+(?:\.[0-9]*)?)f?', duration)
                if number:
                    literal.append((name, args[3], float(number.group(1))))
                else:
                    computed.add(re.sub(r'\s+', '', duration))
        self.assertGreater(len(literal), 20)
        self.assertTrue(all(duration >= 0.1 for _, _, duration in literal), literal)
        fast = {(name, timer) for name, timer, duration in literal if duration < 1.0}
        self.assertEqual(fast, {('MTU_Commando', 'MTU_TIMER_COMMANDO_CAMERA_01'),
                                ('MTU_Commando', 'MTU_TIMER_COMMANDO_CAMERA_02')})
        # The 0.1 s camera timers are one-shots started from Custom, never
        # re-armed from their own expiry.
        self.assertNotIn('Start_Timer', method_body(blocks['MTU_Commando'], 'Timer_Expired'))
        self.assertEqual(computed, {'(10+Get_Int_Random(0,20))'})

    def test_attached_toolkit_scripts_are_event_only(self):
        for filename, script in M00_TOOLKIT_SCRIPTS.items():
            blocks = script_blocks((ROOT / 'staging/scripts' / filename).read_text(errors='replace'))
            self.assertIn(script, blocks, filename)
            self.assertNotIn('Start_Timer', blocks[script], script)
            self.assertNotIn('Find_Object', blocks[script], script)

    def test_tutorial_scripts_use_no_object_collection_commands(self):
        commands = SCRIPTCOMMANDS.read_text()
        for command in OBJECT_COLLECTION_COMMANDS:
            signature = re.search(r'GameObject\s*\*\s*%s\s*\(' % command, commands)
            self.assertIsNotNone(signature, command)
            body = function_body(commands, signature.group(0))
            self.assertTrue('->Head()' in body or 'Collect_Objects' in body or
                            'Find_Nearest_Building_To_Pos' in body, command)
        source = MISSION00.read_text()
        used = set(re.findall(r'Commands->(\w+)', ''.join(
            body for name, body in script_blocks(source).items() if name.startswith('MTU_'))))
        self.assertFalse(used & set(OBJECT_COLLECTION_COMMANDS),
                         used & set(OBJECT_COLLECTION_COMMANDS))
        self.assertIn('Find_Object', used)

    def test_find_object_is_one_id_scan_plus_gated_record(self):
        body = function_body(SCRIPTCOMMANDS.read_text(), 'GameObject * Find_Object( int obj_id )')
        self.assertEqual(body.count('GameObjManager::Find_ScriptableGameObj'), 1)
        self.assertEqual(body.count('A35_Script_Lookup_Record'), 1)

    def test_star_zone_without_observers_returns_before_any_scan(self):
        body = function_body(SCRIPTZONE.read_text(), 'void\tScriptZoneGameObj::Think()')
        early = body.index('if ( Get_Observers().Count() == 0 && Get_Definition().ZoneType != TYPE_CTF )')
        self.assertLess(early, body.index('WWPROFILE( "ScriptZone Think" )'))
        self.assertLess(body.index('return;', early), body.index('InsideList.Head()'))


class LookupTelemetryGateTests(unittest.TestCase):
    def test_disabled_lookup_hooks_return_before_the_mutex(self):
        source = LOOKUP.read_text()
        for signature in ('void A35_Script_Lookup_Record(', 'void A35_Script_Lookup_Set_Context('):
            body = function_body(source, signature)
            gate = body.index('epoch == 0U')
            self.assertLess(gate, body.index('return;'))
            self.assertLess(body.index('return;'), body.index('pthread_mutex_lock'))

    def test_lookup_collection_requires_the_coverage_flag(self):
        runtime = RUNTIME.read_text()
        flag = runtime.index('"ux0:data/renegade/user/config/script-coverage.flag"')
        reset = runtime.index('A35_Campaign_Flight_Reset(', flag)
        window = runtime[flag:reset + 400]
        self.assertIn('const bool lookup_enabled = lookup_request != NULL;', window)
        self.assertIn('load_source, lookup_enabled);', window)


class ScriptCostWatchTests(unittest.TestCase):
    def setUp(self):
        self.source = PROFILE.read_text()

    def watched_names(self):
        block = self.source[self.source.index('const char *const kScriptCostScopes[] = {'):]
        block = block[:block.index('};')]
        return re.findall(r'"([^"]+)"', block)

    def test_watch_is_off_by_default_and_parsed_like_other_rv_flags(self):
        self.assertIn('bool g_renegade_script_cost_active = false;', self.source)
        configure = function_body(self.source, 'void Renegade_Frame_Profile_Configure(void)')
        self.assertIn('fopen("ux0:data/renegade/user/config/script-cost-v1.flag", "rb")', configure)
        self.assertIn('size == 8U', configure)
        self.assertIn('memcmp(value, "RVSC1 ", 6U) == 0', configure)
        self.assertIn("value[7] == '\\n' && value[6] == '1'", configure)
        self.assertLess(configure.index('bool script_cost_enabled = false;'),
                        configure.index('script-cost-v1.flag'))
        self.assertIn('g_renegade_script_cost_active = script_cost_enabled;', configure)
        # Only an enabled watch adds log lines.
        self.assertIn('if (script_cost_enabled) {\n\t\tA30_Vita_Log("A3.6 script-cost: configured',
                      configure)

    def test_watch_leaves_scope_entry_and_exit_untouched(self):
        for signature in ('uint64_t Renegade_Frame_Profile_Begin(const char *name)',
                          'void Renegade_Frame_Profile_End(uint64_t token)',
                          'void Renegade_Frame_Profile_End_Frame(uint32_t frame_us)'):
            body = function_body(self.source, signature)
            self.assertNotIn('script_cost', body.lower(), signature)
            self.assertNotIn('kScriptCostScopes', body, signature)

    def test_watch_reports_before_the_window_reset(self):
        report = function_body(self.source, 'void Report_Window()')
        call = report.index('if (g_renegade_script_cost_active) Report_Script_Cost_Window();')
        self.assertLess(call, report.index('g_slots[index].window_us = 0U;'))
        self.assertLess(call, report.index('g_window_frames = 0U;'))

    def test_watched_scopes_are_original_combat_scopes(self):
        names = self.watched_names()
        self.assertEqual(len(names), len(set(names)))
        combat = ''.join(path.read_text(errors='replace')
                         for path in sorted((ROOT / 'staging/combat').glob('*.cpp')))
        for name in names:
            self.assertRegex(combat, r'(?:WWPROFILE|RENEGADE_SCRIPT_COST_SCOPE)\(\s*"%s"\s*\)'
                             % re.escape(name), name)
        mangled = {name.replace(' ', '_') for name in names}
        tool = load_report_tool()
        self.assertTrue(set(tool.SCRIPT_LAYER_SCOPES) <= mangled)
        self.assertIn('CombatManager_Think', mangled)


class ScriptCostScopePatchTests(unittest.TestCase):
    PATCH = ROOT / 'port/patches/combat-tut1-script-cost-scopes.patch'
    COMBAT = ROOT / 'staging/combat/combat.cpp'
    HEADER = ROOT / 'port/compatibility/include/renegade_vita_script_cost.h'
    THINK = 'void \tCombatManager::Think()'

    @staticmethod
    def calls(body):
        return re.findall(r'\b(\w+(?:::|->)\w+)\s*\(', body)

    def later_combat_patches(self):
        stage = (ROOT / 'tools/stage_sources.sh').read_text()
        line = '-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/%s"' % self.PATCH.name
        rest = stage[stage.index(line) + len(line):]
        return re.findall(r'-d "\$rv_stage/combat" -p1 < "\$rv_root/port/patches/([^"]+)"', rest)

    def test_patch_is_registered_once_after_every_other_combat_patch(self):
        stage = (ROOT / 'tools/stage_sources.sh').read_text()
        line = '-d "$rv_stage/combat" -p1 < "$rv_root/port/patches/%s"' % self.PATCH.name
        self.assertEqual(stage.count(line), 1)
        # Only later tutorial-round patches may follow; every pre-round combat
        # patch is applied first.
        for later in self.later_combat_patches():
            self.assertTrue(later.startswith('combat-tut1-'), later)

    def test_staged_file_is_the_patch_result_and_call_order_is_unchanged(self):
        import shutil
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory(prefix='tut1-script-cost-') as folder:
            shutil.copy(self.COMBAT, folder)
            # Peel later tutorial-round combat.cpp patches off first, newest first.
            for later in reversed(self.later_combat_patches()):
                later_path = ROOT / 'port/patches' / later
                if '+++ b/combat.cpp' not in later_path.read_text():
                    continue
                peeled = subprocess.run(['patch', '--batch', '-R', '-F0', '-p1', '-d', folder,
                                         '-i', str(later_path)], text=True, capture_output=True)
                self.assertEqual(peeled.returncode, 0, later + peeled.stdout + peeled.stderr)
            result = subprocess.run(['patch', '--batch', '-R', '-F0', '-p1', '-d', folder,
                                     '-i', str(self.PATCH)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            before = function_body((Path(folder) / 'combat.cpp').read_text(), self.THINK)
        after = function_body(self.COMBAT.read_text(), self.THINK)
        self.assertEqual(self.calls(before), self.calls(after))
        self.assertNotIn('RENEGADE_SCRIPT_COST_SCOPE', before)
        for name, call in (('Objective Update', 'ObjectiveManager::Update( TimeManager'),
                           ('Conversation Think', 'ConversationMgrClass::Think();'),
                           ('Spawn Update', 'SpawnManager::Update();')):
            self.assertEqual(after.count(call), 1, call)
            self.assertIn('{\tRENEGADE_SCRIPT_COST_SCOPE( "%s" );\n\t%s' % (name, call), after)
        self.assertEqual(after.count('RENEGADE_SCRIPT_COST_SCOPE'), 3)

    def test_scopes_compile_out_off_vita_and_need_both_switches(self):
        combat = self.COMBAT.read_text()
        guard = combat.index('#if defined(RENEGADE_VITA_PORT) && defined(RENEGADE_VITA_FRAME_PROFILE)')
        block = combat[guard:combat.index('#endif', guard)]
        self.assertIn('#include "renegade_vita_script_cost.h"', block)
        self.assertIn('#else\n#define RENEGADE_SCRIPT_COST_SCOPE( name )\n', block)
        header = self.HEADER.read_text()
        self.assertIn('g_renegade_script_cost_active && g_renegade_frame_profile_active ?\n'
                      '\t\t\tRenegade_Frame_Profile_Begin(name) : 0U', header)
        self.assertIn('if (Token != 0U) Renegade_Frame_Profile_End(Token);', header)
        self.assertIn('#define RENEGADE_SCRIPT_COST_SCOPE(name) do {} while (0)', header)


class ScriptCostReportToolTests(unittest.TestCase):
    def setUp(self):
        self.tool = load_report_tool()

    def watch_line(self, window, frames, frame_us, scopes):
        source = PROFILE.read_text()
        header = re.search(r'"(A3\.6 script-cost: version=1 [^"]+)"', source).group(1)
        entry = re.search(r'Appendf\(line, sizeof\(line\), length, "(=%llu/%\.1f)",\n'
                          r'\t\t\tstatic_cast<unsigned long long>\(window_us', source).group(1)
        text = header.replace('%llu', '%d').replace('%u', '%d') % (window, frames, frame_us)
        for name, (us, calls) in scopes:
            text += ' ' + name.replace(' ', '_') + entry.replace('%llu', '%d') % (us, calls)
        return text

    def test_watch_line_from_source_format_is_summarised(self):
        scopes = [('CombatManager Think', (3000, 1.0)), ('Game Obj Think', (1500, 1.0)),
                  ('Post Think', (600, 1.0)), ('Objective Update', (5, 1.0)),
                  ('Conversation Think', (60, 1.0)), ('Spawn Update', (10, 1.0)),
                  ('ScriptZone Think', (40, 31.0)),
                  ('Star Enter', (25, 31.0)), ('All Enter', (0, 0.0)),
                  ('Scriptable PostThink', (35, 70.0)), ('Smart Think', (900, 22.0)),
                  ('See', (50, 1.3))]
        lines = ['noise', self.watch_line(1, 120, 30000, scopes),
                 self.watch_line(2, 120, 25000, [(n, (us * 2, c)) for n, (us, c) in scopes])]
        summary = self.tool.summarize(lines)
        self.assertEqual(summary['script_cost_windows'], 2)
        # ScriptZone + Scriptable PostThink + Conversation + Objective + Spawn;
        # nested Star Enter and AI perception (See) are not added.
        self.assertEqual(summary['script_layer_us_per_frame']['median'], (150 + 300) / 2)
        self.assertAlmostEqual(summary['script_layer_share_of_combat']['median'], 0.05)
        self.assertAlmostEqual(summary['scopes']['ScriptZone_Think']['calls_per_frame_median'], 31.0)
        self.assertNotIn('original_script_scopes_upper_bound_us_per_frame', summary)

    def test_pacing_deltas_reconstruct_windows_and_skip_repeats(self):
        def pacing(frames, combat):
            return ('A4 campaign pacing: frames=%d avg_us time/input/path/control/network/'
                    'combat/other=1/2/3/4/5/%d/6 clock_real/sim/drift_ms=1/1/0' % (frames, combat))
        lines = [pacing(120, 1000), pacing(120, 1000), pacing(240, 1500), pacing(360, 2000),
                 pacing(120, 900)]  # restart: new baseline, no negative window
        windows = self.tool.parse_pacing_windows(lines)
        self.assertEqual([(w['start'], w['end']) for w in windows], [(120, 240), (240, 360)])
        self.assertEqual([w['combat'] for w in windows], [2000.0, 3000.0])
        combat, source = self.tool.parse_combat_windows(lines)
        self.assertEqual(source, 'pacing_delta')
        lines.append('A4 combat casts: frames=480 window=120 combat_avg_us=2750 soldiers_awake/'
                     'hibernating_per_frame=10.0/2.0 per_frame ray_cull/ray_region/aabox_cull/'
                     'aabox_region/obbox_cull/obbox_region=1.0/1.0/1.0/1.0/1.0/1.0')
        self.assertEqual(self.tool.parse_combat_windows(lines), ([2750], 'combat_casts'))

    def test_rank_bound_without_watch_line_and_object_census(self):
        lines = [
            'A4 mission object summary: phase=GameObjManager::Load total=74 physical=35 smart=22 '
            'scriptable=70 soldiers=22 vehicles=0 simple=5 powerups=8 script_zones=31 '
            'cinematics=0 observer_refs=81 cinematic_freeze=0 first_load=1',
            'A3.6 frame-profile: version=2 window=3 frames=120 avg_frame_us=30000 '
            'worst_frame_us=40000 worst_frame_index=7 scopes_per_frame=900 timed_per_frame=200 '
            'exact_calls=2 sample=1/16 clock_ns=300 est_clock_us=120 overflow=0 inclusive=1 '
            'top avg_us/calls_per_frame: Vita_Render=20000/1.0 CombatManager_Think=3000/1.0 '
            'Smart_Think=900/22.0 Scriptable_PostThink=120/70.0',
            'A3.5 perf: frames=240 rolling_samples=120 avg_fps=30.0 frame_us min/p50/p95/p99/'
            'max=1/2/3/4/5 slow_over_16_7ms=0 slow_over_20ms=0 slow_over_33ms=0 '
            'slow_over_50ms=0 stage_us sync/sim/render=2/3500/26000 draws meshes=1',
        ]
        summary = self.tool.summarize(lines)
        census = summary['object_summaries'][0]
        self.assertEqual((census['total'], census['script_zones'], census['scriptable']), (74, 31, 70))
        # ScriptZone Think is unlisted: bounded by the smallest listed scope;
        # RVSC1-only scopes are not bounded without the watch line.
        self.assertEqual(summary['original_script_scopes_upper_bound_us_per_frame']['median'], 240)
        self.assertEqual(summary['sim_us_per_frame']['median'], 3500)
        self.assertEqual(summary['render_us_per_frame']['median'], 26000)


if __name__ == '__main__':
    unittest.main()
