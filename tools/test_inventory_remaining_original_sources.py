import tempfile
import unittest
from pathlib import Path

from tools.inventory_remaining_original_sources import inventory


class InventoryTests(unittest.TestCase):
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
