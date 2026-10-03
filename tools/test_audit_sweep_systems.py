import tempfile
from pathlib import Path
import unittest
from tools.audit_sweep_systems import dialogs, inventory, system_owners


class SystemsSweepTests(unittest.TestCase):
    def test_owner_case_and_selection_are_independent_of_map_mentions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / 'upstream/CnC_Renegade/Code/Combat/soldierobserver.cpp'
            p.parent.mkdir(parents=True)
            p.write_text('original fixture')
            source = p.relative_to(root).as_posix()
            link = {'upstream_rows': [{'source': source, 'staged_candidates': ['staging/combat/soldierobserver.cpp']}],
                    'rows': [{'source': 'staging/combat/soldierobserver.cpp',
                              'selected_for_target': False, 'map_mentions_object': True}]}
            row = next(r for r in system_owners(root, link) if r['name'] == 'innate_ai')
            self.assertEqual(len(row['owner_candidates']), 1)
            candidate = row['owner_candidates'][0]['staged_candidates'][0]
            self.assertFalse(candidate['selected_for_arm_target'])
            self.assertTrue(candidate['map_mentions_object'])
            self.assertEqual(row['status'], 'unknown')

    def test_dialog_declarations_ignore_comments_and_caption_strings(self):
        rows = dialogs('// IDD_FAKE DIALOG 0,0,1,1\nIDD_REAL DIALOGEX 0,0,1,1\nCAPTION "IDD_FAKE2 DIALOG"\n/* IDD_FAKE3 DIALOG */\nIDD_SECOND DIALOG DISCARDABLE 0,0,1,1\n')
        self.assertEqual([r['name'] for r in rows], ['IDD_REAL', 'IDD_SECOND'])
        self.assertEqual(dialogs('\n\n  IDD_REAL DIALOG 0,0,1,1\n')[0]['line'], 3)

    def test_all_dialogs_visible_even_when_templates_or_references_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root / 'upstream/CnC_Renegade/Code/Commando'
            original.mkdir(parents=True)
            (original / 'resource.h').write_text('#define IDD_ONE 100\n#define IDD_TWO 101\n')
            (original / 'dialogresource.h').write_text('')
            (original / 'test.rc').write_text('IDD_ONE DIALOG 0,0,1,1\nIDD_TWO DIALOG 0,0,1,1\n')
            staged = root / 'staging/commando'
            staged.mkdir(parents=True)
            (staged / 'test.cpp').write_text('make(IDD_ONE); // IDD_TWO\n#define IDD_TWO 101\n')
            templates = root / 'templates.inc'
            templates.write_text('static const unsigned char kDialog100[] = {};')
            result = inventory(root, templates)
            self.assertEqual((result['total'], result['present_in_retained_templates'], result['absent_from_retained_templates']), (2, 1, 1))
            self.assertEqual(len(result['rows'][0]['source_reference_candidates']), 1)
            self.assertEqual(result['rows'][1]['source_reference_candidates'][0]['reference_kind'], 'resource_definition')
            linked = inventory(root, templates, {'rows': [{'source': 'staging/commando/test.cpp', 'selected_for_target': True}]})
            self.assertEqual(len(linked['rows'][0]['selected_source_use_candidates']), 1)
            self.assertEqual(linked['rows'][1]['selected_source_use_candidates'], [])
            self.assertTrue(all(r['status'] == 'unknown' for r in result['rows']))
            self.assertEqual(result, inventory(root, templates))
