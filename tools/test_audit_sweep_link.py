import tempfile
from pathlib import Path
import unittest
from tools.audit_sweep_link import inventory


class LinkInventoryTests(unittest.TestCase):
    def test_target_selection_and_map_mentions_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'staging').mkdir()
            for name in ('a.cpp', 'b.CPP', 'c.c', 'header.h'):
                (root / 'staging' / name).write_text('')
            db = [{'directory': folder, 'file': 'staging/a.cpp',
                   'output': 'CMakeFiles/native.dir/staging/a.cpp.obj'},
                  {'directory': folder, 'file': 'staging/b.CPP',
                   'output': 'CMakeFiles/host.dir/staging/b.CPP.obj'},
                  {'directory': folder, 'file': 'staging/c.c',
                   'output': 'CMakeFiles/native.dir/staging/c.c.obj'}]
            result = inventory(root, db, 'native',
                               b'Discarded input sections\nCMakeFiles/native.dir/staging/a.cpp.obj')
            self.assertEqual((result['total'], result['selected'], result['map_mentioned']), (3, 2, 1))
            self.assertEqual(result['counts'], {'unknown': 3})
            self.assertFalse(result['complete'])
            self.assertTrue(all(not r['registration_verified'] for r in result['rows']))
            self.assertEqual(len({r['id'] for r in result['rows']}), 3)
            self.assertEqual(result, inventory(root, db, 'native',
                             b'Discarded input sections\nCMakeFiles/native.dir/staging/a.cpp.obj'))
