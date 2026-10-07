"""Static campaign-control coverage: every INPUT_FUNCTION a campaign needs must
be bound by the Vita default mapping to a logical key/axis that the Vita
DirectInput boundary actually produces, and every route that loads the retail
keyboard/mouse DEFAULT_INPUT.CFG must reapply that mapping."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / 'port/platform/a31_gameplay_boundary.cpp'
DIRECTINPUT = ROOT / 'port/platform/renegade_directinput.cpp'
INPUTCONFIGMGR = ROOT / 'staging/commando/inputconfigmgr.cpp'
STAGE = ROOT / 'tools/stage_sources.sh'
CONTRACT = ROOT / 'port/platform/renegade_vita_input_contract.h'
HOST_PROGRAM = ROOT / 'tools/host_a30_definitions/a31_interactive_main.cpp'
PATCH = 'commando-a37-default-input-profile-vita-mapping.patch'

# Functions the single-player campaign needs (see reports/VITA_CONTROLS.md).
CAMPAIGN_FUNCTIONS = (
    'MOVE_FORWARD', 'MOVE_BACKWARD', 'MOVE_LEFT', 'MOVE_RIGHT',
    'WEAPON_UP', 'WEAPON_DOWN', 'WEAPON_LEFT', 'WEAPON_RIGHT',
    'JUMP', 'CROUCH', 'ACTION', 'RELOAD_WEAPON',
    'NEXT_WEAPON', 'PREV_WEAPON',
    'FIRE_WEAPON_PRIMARY', 'FIRE_WEAPON_SECONDARY',
    'ZOOM_IN', 'ZOOM_OUT',
    'FIRST_PERSON_TOGGLE', 'MENU_TOGGLE', 'CYCLE_POG', 'QUICKSAVE',
)
SLIDERS = {
    'Input::SLIDER_JOYSTICK_UP', 'Input::SLIDER_JOYSTICK_DOWN',
    'Input::SLIDER_JOYSTICK_LEFT', 'Input::SLIDER_JOYSTICK_RIGHT',
    'Input::SLIDER_MOUSE_UP', 'Input::SLIDER_MOUSE_DOWN',
    'Input::SLIDER_MOUSE_LEFT', 'Input::SLIDER_MOUSE_RIGHT',
}
# Original Input::Set_Primary_Key_For_Function copies these bindings.
DERIVED = {'FIRE_WEAPON_SECONDARY': 'USE_WEAPON', 'JUMP': 'MOVE_UP', 'CROUCH': 'MOVE_DOWN'}


def function_body(text, name):
    start = text.index('void ' + name + '()')
    depth = 0
    for index in range(text.index('{', start), len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[start:index]
    raise AssertionError('unterminated ' + name)


def run_cpp(name, source):
    with tempfile.TemporaryDirectory(prefix='vita-' + name + '-') as d:
        cpp = Path(d) / (name + '.cpp')
        binary = Path(d) / name
        cpp.write_text(source)
        subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie',
                        '-I', str(ROOT / 'port/platform'), str(cpp), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


class CampaignControlCoverageTests(unittest.TestCase):
    def setUp(self):
        body = function_body(BOUNDARY.read_text(), 'A31_Interactive_Configure_Vita_Controls')
        self.primary = {}
        for function, key in re.findall(
                r'Set_Primary_Key_For_Function\(\s*INPUT_FUNCTION_(\w+)\s*,\s*([\w:]+)\s*\)', body):
            self.primary[function] = key
        source = DIRECTINPUT.read_text()
        self.keys = set(re.findall(r'Set_Button\(DIKeyboardButtons,\s*(DIK_\w+)', source))
        self.joystick = set()
        for index in re.findall(r'Set_Button\(DIJoystickButtons,\s*(\d)', source):
            self.joystick.add('DirectInput::BUTTON_JOYSTICK_' + 'AB'[int(index)])

    def test_every_campaign_function_reaches_a_produced_control(self):
        for function in CAMPAIGN_FUNCTIONS:
            with self.subTest(function=function):
                self.assertIn(function, self.primary, 'Vita mapping leaves retail keyboard key')
                key = self.primary[function]
                produced = key in SLIDERS or key in self.keys or key in self.joystick
                self.assertTrue(produced, f'{function} -> {key} is never produced on Vita')

    def test_retail_keyboard_aliases_are_cleared(self):
        # Retail binds MoveForward/Backward secondaries to the arrow keys the
        # D-pad produces, and TurnLeft/Right to Left/Right; those must not
        # double-drive movement or turning from zoom and weapon cycling.
        body = function_body(BOUNDARY.read_text(), 'A31_Interactive_Configure_Vita_Controls')
        for function in ('MOVE_FORWARD', 'MOVE_BACKWARD', 'ZOOM_IN', 'ZOOM_OUT',
                         'NEXT_WEAPON', 'PREV_WEAPON', 'ACTION', 'RELOAD_WEAPON'):
            with self.subTest(function=function):
                self.assertRegex(body, r'Set_Secondary_Key_For_Function\(\s*INPUT_FUNCTION_'
                                 + function + r'\s*,\s*0\s*\)')
        for function in ('TURN_LEFT', 'TURN_RIGHT', 'EVA_MISSION_OBJECTIVES_TOGGLE'):
            with self.subTest(function=function):
                self.assertEqual(self.primary.get(function), '0')

    def test_secondary_fire_also_drives_scope_and_remote_c4(self):
        # Sniper scope toggle and remote C4 detonation are the edge-triggered
        # UseWeapon function, which the original setter derives from
        # FireWeaponSecondary.
        self.assertEqual(DERIVED['FIRE_WEAPON_SECONDARY'], 'USE_WEAPON')
        text = (ROOT / 'staging/combat/input.cpp').read_text(encoding='latin-1')
        self.assertRegex(text, r'function_id == INPUT_FUNCTION_FIRE_WEAPON_SECONDARY \) \{\s*'
                         r'Set_Primary_Key_For_Function \( INPUT_FUNCTION_USE_WEAPON, key_id \);')

    def test_crouch_latch_keeps_hold_and_adds_solo_tap_toggle(self):
        source = r'''
        #include "renegade_vita_input_contract.h"
        #include <assert.h>
        using namespace RenegadeVitaInput;
        static const uint32_t F = 16667U;
        int main() {
            CrouchLatch c;
            // Hold: crouched while held, standing after a long release.
            for (int i = 0; i < 30; ++i) assert(c.Sample(true,false,false,true,F));
            assert(!c.Sample(false,false,false,true,F));
            // Solo tap latches; the stick hand/triggers do not consume it.
            assert(c.Sample(true,false,false,true,F));
            assert(c.Sample(true,false,false,true,F));
            assert(c.Sample(false,false,false,true,F));
            for (int i = 0; i < 100; ++i) assert(c.Sample(false,false,false,true,F));
            // Any Circle press while latched ends standing (tap or hold).
            assert(c.Sample(true,false,false,true,F));
            assert(!c.Sample(false,false,false,true,F));
            assert(c.Sample(true,false,false,true,F));
            assert(c.Sample(false,false,false,true,F) && c.Latched());
            for (int i = 0; i < 30; ++i) assert(c.Sample(true,false,false,true,F));
            assert(!c.Sample(false,false,false,true,F));
            // Circle+Cross (momentary crouch-jump) is not a solo tap.
            assert(c.Sample(true,true,false,true,F));
            assert(!c.Sample(false,false,false,true,F));
            // Action (vehicle entry, ladder, poke) releases the latch.
            c.Sample(true,false,false,true,F); c.Sample(false,false,false,true,F);
            assert(c.Latched());
            assert(!c.Sample(false,false,true,true,F));
            // Loss of ordinary gameplay input (dialog, chord, IME) releases it.
            c.Sample(true,false,false,true,F); c.Sample(false,false,false,true,F);
            assert(c.Latched());
            assert(!c.Sample(false,false,false,false,F));
            assert(!c.Sample(false,false,false,true,F));
            // A Circle press spanning focus loss never latches on return.
            assert(!c.Sample(true,false,false,false,F));
            assert(c.Sample(true,false,false,true,F));
            for (int i = 0; i < 30; ++i) c.Sample(true,false,false,true,F);
            assert(!c.Sample(false,false,false,true,F));
            // A hitch longer than the tap window is a hold, not a tap.
            assert(c.Sample(true,false,false,true,F));
            assert(c.Sample(true,false,false,true,250000U));
            assert(!c.Sample(false,false,false,true,F));
            // Closing a dialog/EVA with Circle: a press already down when
            // gameplay input returns is a hold, even if it ends inside the tap
            // window, and the next real tap still latches.
            assert(!c.Sample(false,false,false,false,F));
            assert(c.Sample(true,false,false,true,F));
            assert(c.Sample(true,false,false,true,F));
            assert(!c.Sample(false,false,false,true,F) && !c.Latched());
            assert(c.Sample(true,false,false,true,F));
            assert(c.Sample(false,false,false,true,F) && c.Latched());
            // Reset (Flush on level load/restart) also demands a Circle release.
            c.Reset();
            assert(c.Sample(true,false,false,true,F));
            assert(!c.Sample(false,false,false,true,F) && !c.Latched());
            // The release input clears a latch immediately...
            c.Sample(true,false,false,true,F); c.Sample(false,false,false,true,F);
            assert(c.Latched());
            assert(!c.Sample(false,false,false,true,F,true));
            // ...stays released when the condition ends...
            assert(!c.Sample(false,false,false,true,F) && !c.Latched());
            // ...keeps a held Circle as the original momentary key...
            assert(c.Sample(true,false,false,true,F,true));
            assert(c.Sample(true,false,false,true,F,true));
            // ...and a tap that happens while released never latches.
            assert(!c.Sample(false,false,false,true,F,true));
            assert(c.Sample(true,false,false,true,F,true));
            assert(!c.Sample(false,false,false,true,F));
            assert(!c.Latched());
            // A press spanning one released poll is consumed, not a tap.
            assert(c.Sample(true,false,false,true,F));
            assert(c.Sample(true,false,false,true,F,true));
            assert(!c.Sample(false,false,false,true,F) && !c.Latched());
            // Releasing a latch while Circle is pressed again to stand keeps
            // the key held until that press ends.
            c.Sample(true,false,false,true,F); c.Sample(false,false,false,true,F);
            assert(c.Latched());
            assert(c.Sample(true,false,false,true,F,true));
            assert(!c.Sample(false,false,false,true,F) && !c.Latched());
        }
        '''
        run_cpp('crouch', source)
        source = DIRECTINPUT.read_text()
        flush = source[source.index('void DirectInput::Flush(void)'):]
        self.assertIn('g_crouch_latch.Reset();', flush[:flush.index('\n}\n')])
        # The latch samples the Action edge, so DIK_E must be produced first.
        self.assertLess(source.index('Set_Button(DIKeyboardButtons, DIK_E,'),
                        source.index('g_crouch_latch.Sample('))
        self.assertLess(source.index('g_crouch_latch.Sample('),
                        source.index('Set_Button(DIKeyboardButtons, DIK_LCONTROL,'))

    def test_crouch_latch_releases_on_original_player_state(self):
        # Every condition that makes a latched crouch wrong must release it:
        # vehicle seat (action.cpp normalizes forward/left by the length of
        # (forward, left, MOVE_UP-MOVE_DOWN), so a held crouch key costs ~29%
        # throttle), script Control_Enable(false), cinematic, death, a new star
        # object after respawn/restart/load, beacon fire, and the locked
        # human state used by beacon arming and C4 placement.
        source = r'''
        #include "renegade_vita_input_contract.h"
        #include <assert.h>
        using namespace RenegadeVitaInput;
        static const uint32_t F = 16667U;

        static CrouchPlayerContext Star(uint32_t id = 7U, uintptr_t address = 0x1000U) {
            CrouchPlayerContext c = {};
            c.star_present = true;
            c.object_id = id;
            c.object_address = address;
            return c;
        }

        // One DirectInput::Read poll: gate first, then the latch it releases.
        struct Rig {
            CrouchContextGate gate;
            CrouchLatch latch;
            uint32_t reasons;
            Rig() : reasons(0U) {}
            bool Poll(const CrouchPlayerContext &c, bool circle, bool fire = false,
                      bool cross = false, bool enabled = true) {
                reasons = gate.Evaluate(c, fire);
                return latch.Sample(circle, cross, false, enabled, F, reasons != 0U);
            }
            void Latch(const CrouchPlayerContext &c) {
                Poll(c, false);
                assert(Poll(c, true));
                assert(Poll(c, false) && latch.Latched());
            }
        };

        int main() {
            // Context gate semantics.
            {
                CrouchContextGate g;
                CrouchPlayerContext none = {};
                assert(g.Evaluate(none, false) == CROUCH_RELEASE_NO_PLAYER);
                // First sight of a star, and an unchanged star, release nothing.
                assert(g.Evaluate(Star(), false) == 0U);
                assert(g.Evaluate(Star(), true) == 0U);
                // A different ID or a different object address is a new player.
                assert(g.Evaluate(Star(8U, 0x1000U), false) == CROUCH_RELEASE_NEW_PLAYER);
                assert(g.Evaluate(Star(8U, 0x2000U), false) == CROUCH_RELEASE_NEW_PLAYER);
                assert(g.Evaluate(Star(8U, 0x2000U), false) == 0U);
                // Losing the star forgets it; the next star is first sight again.
                assert(g.Evaluate(none, false) == CROUCH_RELEASE_NO_PLAYER);
                assert(g.Evaluate(Star(9U, 0x3000U), false) == 0U);
                g.Reset();
                assert(g.Evaluate(Star(1U, 0x1U), false) == 0U);
                // Each state flag maps to exactly its reason.
                struct Case { bool CrouchPlayerContext::*flag; uint32_t reason; };
                const Case cases[] = {
                    { &CrouchPlayerContext::in_vehicle, CROUCH_RELEASE_VEHICLE },
                    { &CrouchPlayerContext::control_disabled, CROUCH_RELEASE_CONTROL_DISABLED },
                    { &CrouchPlayerContext::cinematic, CROUCH_RELEASE_CINEMATIC },
                    { &CrouchPlayerContext::dead, CROUCH_RELEASE_DEAD },
                    { &CrouchPlayerContext::scripted_animation, CROUCH_RELEASE_SCRIPTED_ANIMATION },
                };
                for (const Case &k : cases) {
                    CrouchPlayerContext c = Star(1U, 0x1U);
                    c.*(k.flag) = true;
                    assert(g.Evaluate(c, false) == k.reason);
                    assert(g.Evaluate(c, true) == k.reason);
                }
                // Beacon fire needs both a Beacon weapon and the fire trigger.
                CrouchPlayerContext b = Star(1U, 0x1U);
                assert(g.Evaluate(b, true) == 0U);
                b.beacon_weapon = true;
                assert(g.Evaluate(b, false) == 0U);
                assert(g.Evaluate(b, true) == CROUCH_RELEASE_BEACON_FIRE);
            }

            // Each reason ends a latch, and a tap under it never re-latches.
            {
                struct Case { bool CrouchPlayerContext::*flag; };
                const Case cases[] = {
                    { &CrouchPlayerContext::in_vehicle },
                    { &CrouchPlayerContext::control_disabled },
                    { &CrouchPlayerContext::cinematic },
                    { &CrouchPlayerContext::dead },
                    { &CrouchPlayerContext::scripted_animation },
                };
                for (const Case &k : cases) {
                    Rig r;
                    CrouchPlayerContext ok = Star();
                    CrouchPlayerContext bad = ok;
                    bad.*(k.flag) = true;
                    r.Latch(ok);
                    assert(!r.Poll(bad, false));          // latch released at once
                    assert(!r.Poll(ok, false));           // and stays released
                    r.Latch(ok);                          // normal latching still works
                    assert(!r.Poll(bad, false));
                    // Tap under the condition: nothing latches, now or later.
                    assert(r.Poll(bad, true));            // momentary hold only
                    assert(!r.Poll(bad, false));
                    assert(!r.Poll(ok, false));
                    // A tap that spans the end of the condition is consumed.
                    assert(r.Poll(bad, true));
                    assert(r.Poll(ok, true));
                    assert(!r.Poll(ok, false));
                    // Held Circle keeps the original momentary crouch key.
                    for (int i = 0; i < 30; ++i) assert(r.Poll(bad, true));
                    assert(!r.Poll(bad, false));
                    r.Latch(ok);                          // recovers after the condition
                }
            }

            // New star object after respawn/restart/load.
            {
                Rig r;
                r.Latch(Star(7U, 0x1000U));
                assert(!r.Poll(Star(7U, 0x5000U), false));
                assert((r.reasons & CROUCH_RELEASE_NEW_PLAYER) != 0U);
                r.Latch(Star(7U, 0x5000U));
                assert(!r.Poll(Star(12U, 0x5000U), false));
                r.Latch(Star(12U, 0x5000U));
                // No star at all (between levels) also releases.
                assert(!r.Poll(CrouchPlayerContext(), false));
                assert(r.reasons == CROUCH_RELEASE_NO_PLAYER);
            }

            // Beacon: firing releases a latched crouch, other weapons do not.
            {
                Rig r;
                CrouchPlayerContext rifle = Star();
                CrouchPlayerContext beacon = rifle;
                beacon.beacon_weapon = true;
                r.Latch(rifle);
                assert(r.Poll(rifle, false, true));       // rifle fire keeps crouch
                assert(r.Poll(beacon, false, false));     // beacon held, not firing
                assert(!r.Poll(beacon, false, true));     // beacon fire stands up
                assert(!r.Poll(beacon, false, false));    // and stays standing
                r.Latch(beacon);
                assert(!r.Poll(beacon, false, true));
                // Tapping Circle while firing a beacon does not re-latch.
                assert(r.Poll(beacon, true, true));
                assert(!r.Poll(beacon, false, true));
                assert(!r.Poll(beacon, false, false));
                // A held Circle is still the original hold, beacon or not.
                assert(r.Poll(beacon, true, true));
            }

            // Vehicle entry followed by exit leaves the player standing, and a
            // tap inside the vehicle (L3-less handheld) does nothing.
            {
                Rig r;
                CrouchPlayerContext foot = Star();
                CrouchPlayerContext seat = foot;
                seat.in_vehicle = true;
                r.Latch(foot);
                for (int i = 0; i < 10; ++i) assert(!r.Poll(seat, false));
                assert(r.Poll(seat, true));
                assert(!r.Poll(seat, false));
                assert(!r.Poll(foot, false));
            }

            // Dialog/EVA closes (gameplay input lost) still resets everything.
            {
                Rig r;
                CrouchPlayerContext c = Star();
                r.Latch(c);
                assert(!r.Poll(c, false, false, false, false));
                r.gate.Reset();
                assert(!r.Poll(c, false));
                // Circle that closed the menu and ends inside the tap window.
                assert(!r.Poll(c, true, false, false, false));
                assert(r.Poll(c, true));
                assert(!r.Poll(c, false) && !r.latch.Latched());
                r.Latch(c);
            }
            return 0;
        }
        '''
        run_cpp('crouch-state', source)

    def test_crouch_release_is_sampled_before_the_latch_from_original_state(self):
        source = DIRECTINPUT.read_text()
        sample = source.index('A31_Interactive_Sample_Crouch_Player_Context(crouch_player)')
        latch = source.index('g_crouch_latch.Sample(')
        self.assertLess(sample, latch)
        self.assertLess(source.index('Set_Button(DIKeyboardButtons, DIK_E,'), latch)
        # Sampled only while ordinary gameplay input is active; otherwise the
        # gate is reset together with the latch.
        window = source[source.rindex('uint32_t crouch_release_reasons', 0, sample):latch]
        self.assertRegex(window, r'if \(ordinary_gameplay_input\) \{[\s\S]*?\} else \{\s*'
                         r'g_crouch_context_gate\.Reset\(\);')
        self.assertIn('(buttons & SCE_CTRL_RTRIGGER) != 0U', window)
        call = source[latch:source.index(';', source.index('crouch_release_reasons != 0U', latch))]
        self.assertIn('crouch_release_reasons != 0U', call)
        flush = source[source.index('void DirectInput::Flush(void)'):]
        self.assertIn('g_crouch_context_gate.Reset();', flush[:flush.index('\n}\n')])
        # A physically held Circle (or PSTV L3) is still the original momentary
        # key whatever the release state says.
        self.assertRegex(source, r'ordinary_gameplay_input && \(crouch_held \|\|[^;]*SCE_CTRL_L3\) != 0\)\)\);')
        # The sampler is declared with the contract and defined once, beside the
        # other Combat-aware boundary code; it only reads original star state.
        self.assertIn('bool A31_Interactive_Sample_Crouch_Player_Context(', CONTRACT.read_text())
        boundary = BOUNDARY.read_text()
        self.assertEqual(boundary.count('bool A31_Interactive_Sample_Crouch_Player_Context('), 1)
        body = boundary[boundary.index('bool A31_Interactive_Sample_Crouch_Player_Context('):]
        body = body[:body.index('\n}\n')]
        for needle in ('CombatManager::Get_The_Star()', 'star->Get_Vehicle()', 'star->Is_In_Vehicle()',
                       '!star->Is_Control_Enabled()', 'camera->Is_In_Cinematic()', 'star->Is_Dead()',
                       'star->Is_Destroyed()', 'star->Is_State_Locked()', 'WEAPON_HOLD_STYLE_BEACON',
                       'star->Get_ID()', 'reinterpret_cast<uintptr_t>(star)'):
            with self.subTest(needle=needle):
                self.assertIn(needle, body)
        for forbidden in ('Set_', 'Toggle', 'Control.', 'Controller'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, body)

    def test_crouch_release_signals_exist_in_original_combat(self):
        def read(path):
            return (ROOT / path).read_text(encoding='latin-1')
        soldier = read('staging/combat/soldier.h')
        for needle in (r'VehicleGameObj\s*\*\s*Get_Vehicle\( void \)',
                       r'bool\s+Is_In_Vehicle\( void \)\s*\{ return Get_State\(\) == HumanStateClass::IN_VEHICLE;',
                       r'bool\s+Is_Dead\( void \)', r'bool\s+Is_Destroyed\( void \)',
                       r'bool\s+Is_State_Locked\( void \)\s*\{ return HumanState\.Is_Locked\(\);'):
            with self.subTest(needle=needle):
                self.assertRegex(soldier, needle)
        self.assertRegex(read('staging/combat/smartgameobj.h'), r'bool\s+Is_Control_Enabled\( void \)')
        self.assertRegex(read('staging/combat/ccamera.h'),
                         r'bool\s+Is_In_Cinematic\( void \)\s*\{ return HostModel != NULL; \}')
        # Why a held crouch key slows a vehicle: Action normalizes forward/left
        # by the length of (forward, left, MoveUp-MoveDown) and MoveDown is the
        # crouch binding.
        action = read('staging/combat/action.cpp')
        self.assertIn('Input::Get_Amount( INPUT_FUNCTION_MOVE_UP ) - Input::Get_Amount( INPUT_FUNCTION_MOVE_DOWN )', action)
        self.assertRegex(action, r'Vector3 move\( forward_amount, left_amount, up_amount \);\s*'
                         r'float length = move\.Length\(\);\s*if \( length > 1 \) \{\s*'
                         r'forward_amount /= length;')
        # Beacon arming and C4 placement lock the human state with a scripted
        # animation; the beacon weapon itself only requires HumanState UPRIGHT,
        # a state separate from the crouch flag (so the beacon release is
        # insurance for the M13 ion beacon, not a reproduced game rule).
        self.assertIn('soldier->Set_Animation (Get_Definition ().ArmingAnimationName, true, 0);',
                      read('staging/combat/beacongameobj.cpp'))
        self.assertIn('HumanState.Start_Scripted_Animation( AnimationName, true, false );',
                      read('staging/combat/soldier.cpp'))
        self.assertRegex(soldier, r'bool\s+Is_Upright\( void \)\s*\{ return Get_State\(\) == HumanStateClass::UPRIGHT; \}')
        self.assertIn('CROUCHED_FLAG', read('staging/combat/humanstate.h'))
        self.assertIn('!Get_Owner()->As_SoldierGameObj()->Is_Upright()', read('staging/combat/weapons.cpp'))

    def test_host_interactive_program_expects_the_real_vita_bindings(self):
        # The host A3.1 program asserts the live bindings after
        # A31_Interactive_Configure_Vita_Controls(). Derive the effective
        # mapping from the boundary plus the original derived-key setters and
        # compare every primary/secondary expectation, so it cannot go stale
        # (it once expected scope/C4 detonate on Triangle/DIK_E).
        host = HOST_PROGRAM.read_text()
        start = host.index('A31_Interactive_Configure_Vita_Controls();')
        region = host[start:host.index('vita_controls_use_original_action_sliders', start)]
        body = function_body(BOUNDARY.read_text(), 'A31_Interactive_Configure_Vita_Controls')
        effective = dict(self.primary)
        for source_function, derived in DERIVED.items():
            if source_function in self.primary:
                effective.setdefault(derived, self.primary[source_function])
        secondary = dict(re.findall(
            r'Set_Secondary_Key_For_Function\(\s*INPUT_FUNCTION_(\w+)\s*,\s*([\w:]+)\s*\)', body))
        expected = re.findall(
            r'Get_Primary_Key_For_Function\(\s*INPUT_FUNCTION_(\w+)\s*\)\s*==\s*([\w:]+)', region)
        self.assertGreaterEqual(len(expected), 25)
        for function, key in expected:
            with self.subTest(primary=function):
                self.assertEqual(effective.get(function), key,
                                 f'host program expects {function} on {key}')
        for function, key in re.findall(
                r'Get_Secondary_Key_For_Function\(\s*INPUT_FUNCTION_(\w+)\s*\)\s*==\s*([\w:]+)', region):
            with self.subTest(secondary=function):
                self.assertEqual(secondary.get(function), key)
        pairs = dict(expected)
        # Triangle (DIK_E) is Action only; scope and remote C4 are the L trigger.
        self.assertEqual(pairs['ACTION'], 'DIK_E')
        self.assertEqual(pairs['USE_WEAPON'], 'DirectInput::BUTTON_JOYSTICK_A')
        self.assertEqual(pairs['FIRE_WEAPON_SECONDARY'], 'DirectInput::BUTTON_JOYSTICK_A')
        self.assertEqual(pairs['FIRE_WEAPON_PRIMARY'], 'DirectInput::BUTTON_JOYSTICK_B')
        self.assertEqual(pairs['CROUCH'], 'DIK_LCONTROL')
        self.assertEqual(pairs['MOVE_DOWN'], 'DIK_LCONTROL')
        self.assertNotIn('USE_WEAPON) == DIK_E', region)
        # The keys the host program expects are ones the DirectInput boundary
        # produces (L/R triggers are joystick buttons 0/1).
        self.assertIn('DirectInput::BUTTON_JOYSTICK_A', self.joystick)
        self.assertIn('DirectInput::BUTTON_JOYSTICK_B', self.joystick)

    def test_default_profile_load_reapplies_vita_mapping(self):
        text = INPUTCONFIGMGR.read_text(encoding='latin-1')
        load = text[text.index('InputConfigMgrClass::Load_Configuration (const InputConfigClass &config)'):]
        load = load[:load.index('\n}\n')]
        self.assertRegex(load, r'Input::Load_Configuration \(config\.Get_Filename \(\)\);\s*'
                         r'#if defined\(RENEGADE_VITA_PORT\)[\s\S]*?if \(config\.Is_Default \(\)\) \{\s*'
                         r'A31_Interactive_Configure_Vita_Controls \(\);')
        # The UI reload must observe the Vita bindings, not the retail ones.
        self.assertLess(load.index('A31_Interactive_Configure_Vita_Controls'),
                        load.index('Reload ()'))
        self.assertIn('#include "a31_interactive_runtime_policy.h"', text)
        stage = STAGE.read_text()
        self.assertEqual(stage.count(PATCH), 1)
        self.assertTrue((ROOT / 'port/patches' / PATCH).is_file())


if __name__ == '__main__':
    unittest.main()
