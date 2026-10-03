import tempfile
from pathlib import Path
import unittest
from tools.audit_sweep_link import inventory, registration_candidates


class LinkInventoryTests(unittest.TestCase):
    def test_registration_candidates_mask_comments_and_literals(self):
        code = '''// DECLARE_SCRIPT(Fake, "")
const char *s = "DECLARE_SCRIPT(Fake2, x)";
DECLARE_SCRIPT(Actual, "parameters")
SimplePersistFactoryClass<Thing, CHUNK_THING> _factory;
DECLARE_DEFINITION_FACTORY(Thing, CLASS_THING, "Thing") _def;
DECLARE_NETWORKOBJECT_FACTORY(Event, NET_EVENT);
'''
        rows = registration_candidates(code)
        self.assertEqual([r['kind'] for r in rows], ['script', 'persist', 'definition', 'network'])
        self.assertEqual(rows[0]['arguments'], ['Actual'])
        self.assertEqual(rows[0]['line'], 3)

    def test_upstream_case_mapping_retains_unstaged_units(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'staging/scripts').mkdir(parents=True)
            (root / 'staging/scripts/mission08.cpp').write_text('')
            upstream = root / 'upstream/CnC_Renegade/Code/Scripts'
            upstream.mkdir(parents=True)
            (upstream / 'Mission08.cpp').write_text('')
            (upstream / 'Missing.cpp').write_text('')
            result = inventory(root, [], 'native', b'')
            self.assertEqual(result['upstream_total'], 2)
            self.assertEqual(result['upstream_without_staged_candidate'], 1)
            mapped = next(r for r in result['upstream_rows'] if r['source'].endswith('Mission08.cpp'))
            self.assertEqual(mapped['staged_candidates'], ['staging/scripts/mission08.cpp'])

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
