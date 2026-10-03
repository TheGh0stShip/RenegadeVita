import tempfile
from pathlib import Path
import unittest
from tools.audit_sweep_systems import dialogs, inventory


class SystemsSweepTests(unittest.TestCase):
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
            (staged / 'test.cpp').write_text('make(IDD_ONE); // IDD_TWO\n')
            templates = root / 'templates.inc'
            templates.write_text('static const unsigned char kDialog100[] = {};')
            result = inventory(root, templates)
            self.assertEqual((result['total'], result['present_in_retained_templates'], result['absent_from_retained_templates']), (2, 1, 1))
            self.assertEqual(len(result['rows'][0]['source_reference_candidates']), 1)
            self.assertEqual(result['rows'][1]['source_reference_candidates'], [])
            self.assertTrue(all(r['status'] == 'unknown' for r in result['rows']))
            self.assertEqual(result, inventory(root, templates))
