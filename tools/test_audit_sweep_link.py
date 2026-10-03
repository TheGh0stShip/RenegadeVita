import tempfile
from pathlib import Path
import unittest
from tools.audit_sweep_link import inventory, registration_candidates, defined_symbols


class LinkInventoryTests(unittest.TestCase):
    def test_defined_symbols_reject_undefined_and_keep_duplicate_addresses(self):
        result = defined_symbols(b'81700000 B _Example\n81700004 b _Example\n U _Absent\n00000000 U _Absent2\n81200000 T a function()\n')
        self.assertEqual(len(result['_Example']), 2)
        self.assertNotIn('_Absent', result)
        self.assertNotIn('_Absent2', result)
        self.assertIn('a function()', result)

    def test_numeric_persist_load_symbol_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = inventory(root, [], 'native', b'',
                               b'81000000 W SimplePersistFactoryClass<Thing, 123>::Load(ChunkLoadClass&)\n')
            self.assertEqual(result['persist_load_methods'][0]['chunk_id'], 123)
            self.assertEqual(result['persist_load_methods'][0]['class'], 'Thing')

    def test_registrar_symbol_presence_does_not_prove_registration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'staging').mkdir()
            (root / 'staging/test.cpp').write_text('DECLARE_SCRIPT(Example, "")\nSimplePersistFactoryClass<X, CHUNK_X> _Factory;\nDECLARE_DEFINITION_FACTORY(X, CLASS_X, "X") _DifferentDefName;\nDECLARE_NETWORKOBJECT_FACTORY(Event, NET_EVENT);')
            result = inventory(root, [], 'native', b'', b'81700000 B _ExampleRegistrant\n81700004 b _Factory\n81700008 B _DifferentDefName\n8170000c B EventFactory\n')
            self.assertEqual(result['registration_candidates_with_defined_symbol'], 4)
            self.assertTrue(all(not r['registration_verified'] for r in result['registration_candidates']))
            self.assertTrue(all(r['status'] == 'unknown' for r in result['registration_candidates']))

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
