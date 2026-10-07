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
        }
        '''
        with tempfile.TemporaryDirectory(prefix='vita-crouch-') as d:
            cpp = Path(d) / 'crouch.cpp'
            binary = Path(d) / 'crouch'
            cpp.write_text(source)
            subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie',
                            '-I', str(ROOT / 'port/platform'), str(cpp), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
        source = DIRECTINPUT.read_text()
        flush = source[source.index('void DirectInput::Flush(void)'):]
        self.assertIn('g_crouch_latch.Reset();', flush[:flush.index('\n}\n')])
        # The latch samples the Action edge, so DIK_E must be produced first.
        self.assertLess(source.index('Set_Button(DIKeyboardButtons, DIK_E,'),
                        source.index('g_crouch_latch.Sample('))
        self.assertLess(source.index('g_crouch_latch.Sample('),
                        source.index('Set_Button(DIKeyboardButtons, DIK_LCONTROL,'))

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
