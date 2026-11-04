import tempfile
import json
import unittest
from pathlib import Path

from tools.inventory_remaining_original_sources import inventory


class InventoryTests(unittest.TestCase):
    def test_configured_selection_excludes_other_targets_and_is_not_link_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / 'upstream/CnC_Renegade/Code/Combat'
            code.mkdir(parents=True)
            (root / 'cmake').mkdir()
            (root / 'staging/combat').mkdir(parents=True)
            (root / 'CMakeLists.txt').write_text('# combat/unselected.cpp\n')
            for name in ('selected', 'unselected', 'probe'):
                (code / (name + '.cpp')).write_text('int owner;\n')
            commands = root / 'compile_commands.json'
            commands.write_text(json.dumps([
                {'directory': str(root), 'file': 'staging/combat/selected.cpp',
                 'output': 'CMakeFiles/Game.dir/staging/combat/selected.cpp.obj'},
                {'directory': str(root), 'file': 'staging/combat/probe.cpp',
                 'output': 'CMakeFiles/Other.dir/staging/combat/probe.cpp.obj'}]))
            result = inventory(root, commands, 'Game')
            rows = {r['original']: r for r in result['rows']}
            self.assertEqual(len(rows['Combat/selected.cpp']['configured_target_outputs']), 1)
            for name in ('unselected', 'probe'):
                self.assertEqual(rows[f'Combat/{name}.cpp']['configured_target_outputs'], [])
            self.assertTrue(all(r['linked'] is None for r in rows.values()))
            with self.assertRaises(ValueError):
                inventory(root, commands, 'Missing')

    def test_project_paths_preserve_membership_without_claiming_linkage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / 'upstream/CnC_Renegade/Code'
            (code / 'Combat').mkdir(parents=True)
            (root / 'cmake').mkdir()
            (root / 'CMakeLists.txt').write_text('# combat/unit.cpp\n')
            (root / 'cmake/scripts.cmake').write_text('${RENEGADE_SCRIPT_SOURCE}/Mission00.cpp\n')
            (code / 'Scripts').mkdir()
            (code / 'Scripts/Mission00.cpp').write_text('int mission;\n')
            (code / 'Combat/unit.cpp').write_text('int owner;\n')
            (code / 'Combat/tool.CPP').write_text('int tool;\n')
            (code / 'Combat/Combat.dsp').write_text('SOURCE=".\\UNIT.cpp"\n')
            result = inventory(root)
            self.assertEqual(result['total'], 3)
            rows = {r['original']: r for r in result['rows']}
            unit = rows['Combat/unit.cpp']
            self.assertEqual(unit['released_project_membership'], ['Combat/Combat.dsp'])
            self.assertEqual(unit['manifest_literal_mentions'], ['CMakeLists.txt'])
            self.assertIsNone(unit['linked'])
            self.assertEqual(rows['Combat/tool.CPP']['released_project_membership'], [])
            self.assertEqual(rows['Scripts/Mission00.cpp']['manifest_literal_mentions'],
                             ['cmake/scripts.cmake'])


if __name__ == '__main__':
    unittest.main()
