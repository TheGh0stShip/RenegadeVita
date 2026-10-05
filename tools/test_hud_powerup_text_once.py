"""Powerup HUD labels are built once per icon instead of every frame."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HUD = ROOT / 'staging/combat/hud.cpp'
PATCH = 'combat-a36-powerup-text-once.patch'


def section(source, start, end):
    first = source.index(start)
    return source[first:source.index(end, first)]


def port_only(text):
    """Keep the lines a RENEGADE_VITA_PORT build compiles (#if 0 and #else
    branches of the port guard are dropped)."""
    kept, stack = [], []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#if'):
            stack.append(not stripped.startswith('#if 0'))
            continue
        if stripped.startswith('#else') and stack:
            stack[-1] = not stack[-1]
            continue
        if stripped.startswith('#endif') and stack:
            stack.pop()
            continue
        if all(stack):
            kept.append(line)
    return '\n'.join(kept)


class HudPowerupTextOnceTests(unittest.TestCase):
    def test_labels_built_at_add_and_redrawn_per_frame(self):
        source = HUD.read_text(errors='replace')
        add = section(source, 'static\tvoid\tPowerup_Add(', 'void \tPowerup_Reset(')
        self.assertIn('data->NameRenderer->Build_Sentence( data->Name );', add)
        self.assertIn('data->NumberRenderer->Build_Sentence( num );', add)
        update = port_only(section(source, 'static\tvoid\tPowerup_Update( void )',
                                   'static\tvoid\tPowerup_Render( void )'))
        self.assertNotIn('Build_Sentence', update)
        self.assertEqual(update.count('->Reset_Polys();'), 3)
        render = section(source, 'static\tvoid\tPowerup_Render( void )', '** Weapon Display')
        self.assertIn('LeftPowerupIconList[i]->NameRenderer->Render();', render)
        self.assertIn('RightPowerupIconList[i]->NumberRenderer->Render();', render)
        icon = section(source, 'struct PowerupIconStruct {', '};')
        self.assertIn('delete NameRenderer;', icon)
        self.assertIn('delete NumberRenderer;', icon)

    def test_patch_registered_once(self):
        stage = (ROOT / 'tools/stage_sources.sh').read_text()
        self.assertEqual(stage.count(PATCH), 1)
        self.assertTrue((ROOT / 'port/patches' / PATCH).is_file())


if __name__ == '__main__':
    unittest.main()
