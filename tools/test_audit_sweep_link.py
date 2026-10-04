import tempfile
from pathlib import Path
import unittest
from tools.audit_sweep_link import inventory, registration_candidates, defined_symbols


class LinkInventoryTests(unittest.TestCase):
    def test_same_line_registrations_have_distinct_identities(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'staging').mkdir()
            (root / 'staging/a.cpp').write_text('DECLARE_SCRIPT(A, ""); DECLARE_SCRIPT(B, "");')
            result = inventory(root, [], 'native', b'')
            rows = result['registration_candidates']
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({row['id'] for row in rows}), 2)
            self.assertEqual([row['line'] for row in rows], [1, 1])
            self.assertLess(rows[0]['column'], rows[1]['column'])

    def test_manual_installation_forms_are_candidates(self):
        code = '''Register_Prototype_Loader(&_MeshLoader);
FunctionList.Add(new FogConsoleFunctionClass());
GameModeManager::Add(new CombatGameModeClass);
GameModeManager::Add(&frontend_combat_mode);
SaveLoadSystemClass::Register_Persist_Factory(this);
DefinitionFactoryMgrClass::Register_Factory(this);
// GameModeManager::Add(new Fake);
const char *s = "Register_Prototype_Loader(&Fake)";
'''
        rows = registration_candidates(code)
        self.assertEqual([r['kind'] for r in rows], ['prototype_install', 'console_install',
            'game_mode_install', 'game_mode_reference_install', 'manual_factory_call', 'manual_factory_call'])
        self.assertEqual(rows[0]['arguments'], ['_MeshLoader'])
        self.assertTrue(all(r['status'] == 'unknown' for r in rows))

    def test_header_candidate_has_unknown_target_membership(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'staging').mkdir()
            (root / 'staging/a.cpp').write_text('Register_Prototype_Loader(&_MeshLoader);')
            (root / 'staging/factory.H').write_text('DECLARE_SCRIPT(HeaderScript, "")')
            (root / 'staging/ignore.txt').write_text('DECLARE_SCRIPT(Ignored, "")')
            result = inventory(root, [], 'native', b'', b'81200000 B _MeshLoader\n')
            self.assertEqual(result['total'], 1)
            self.assertEqual(result['registration_source_total'], 2)
            self.assertEqual(result['registration_candidate_total'], 2)
            header = next(r for r in result['registration_candidates'] if r['kind'] == 'script')
            self.assertIsNone(header['selected_for_target'])
            self.assertEqual(result['unmatched_unselected_script_candidates'], 0)
            self.assertEqual(result['script_candidates_with_unknown_selection'], 1)
            prototype = next(r for r in result['registration_candidates'] if r['kind'] == 'prototype_install')
            self.assertEqual(prototype['expected_symbol'], '_MeshLoader')
            self.assertTrue(prototype['defined_symbol_matches'])
            self.assertFalse(prototype['registration_verified'])

    def test_port_replacement_calls_do_not_change_staged_unit_denominator(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'staging').mkdir()
            (root / 'staging/a.cpp').write_text('')
            (root / 'port').mkdir()
            (root / 'port/startup.cpp').write_text('GameModeManager::Add(new CombatGameModeClass);')
            db = [{'directory': folder, 'file': 'port/startup.cpp',
                   'output': 'CMakeFiles/native.dir/port/startup.cpp.obj'}]
            result = inventory(root, db, 'native', b'')
            self.assertEqual(result['total'], 1)
            self.assertEqual(result['registration_source_total'], 2)
            row = result['registration_candidates'][0]
            self.assertEqual(row['source'], 'port/startup.cpp')
            self.assertTrue(row['selected_for_target'])
            self.assertFalse(row['registration_verified'])

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
