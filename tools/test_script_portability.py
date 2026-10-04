import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
from tools.audit_script_portability import findings, inventory


class ScriptPortabilityTests(unittest.TestCase):
    def test_all_units_and_headers_including_missing_staged_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=root/'upstream/CnC_Renegade/Code/Scripts'
            staged=root/'staging/scripts'
            original.mkdir(parents=True);staged.mkdir(parents=True)
            (original/'Scripts.dsp').write_text('fixture')
            (original/'mission08.cpp').write_text('int value;')
            (original/'shared.h').write_text('char *value;')
            (staged/'mission08.cpp').write_text('int value = 0;')
            with patch('tools.audit_script_portability.dsp_sources',return_value=['mission08.cpp']):
                result=inventory(root)
            self.assertEqual((result['total'],result['dsp_units'],result['directory_headers'],result['staged_present']), (2,1,1,1))
            self.assertEqual(result['rows'][0]['name'],'mission08.cpp')
            self.assertFalse(result['rows'][1]['staged_present'])
            self.assertEqual(result['original_categories'],{'bare_scalar_declaration':2,'plain_char_declaration':1})
            self.assertEqual(result['staged_categories'],{})

    def test_comments_and_strings_do_not_make_findings(self):
        self.assertEqual(findings('// stricmp(a,b);\n/* for(int i=0;;) */\n"sizeof(int)";'), [])

    def test_template_names_and_parameter_types_are_not_comparisons_or_casts(self):
        self.assertEqual(findings('T *SList<T>::Remove_Head(void);\ntypedef const char* (*FN)(int);'), [])

    def test_address_integer_and_pointer_casts_are_retained_separately(self):
        rows=findings('(int)&area; (int *)param;')
        self.assertEqual({r['category'] for r in rows},
                         {'integer_cast','address_to_integer_cast','scalar_pointer_cast'})
        self.assertTrue(all(r['status']=='unknown' for r in rows))

    def test_categories_are_candidates_with_locations(self):
        source = 'DECLARE_SCRIPT(Example)\nchar *p;\nif (*p <= 32) {}\nstricmp(a,b);\n(int)p; sizeof(p);\nfor(int i=0;i<1;++i){}\nint value;'
        rows = findings(source)
        self.assertEqual({r['category'] for r in rows},
                         {'plain_char_declaration','bare_scalar_declaration','dereference_order_comparison',
                          'case_insensitive_lookup','integer_cast','size_expression','loop_local_declaration'})
        self.assertTrue(all(r['status']=='unknown' for r in rows))
        self.assertTrue(all(r['preceding_script_declaration_candidate']=='Example' for r in rows))
        self.assertEqual(next(r['line'] for r in rows if r['category']=='case_insensitive_lookup'),4)

    def test_explicit_signed_char_is_not_plain_char(self):
        for source in ('signed char value = 0;', 'unsigned  char value = 0;', 'signed\nchar value = 0;'):
            self.assertEqual(findings(source), [])

    def test_no_defect_verdict_from_bare_or_loop_declarations(self):
        rows = findings('int member;\nfor(int i=0;i<3;++i){}')
        self.assertEqual([r['category'] for r in rows], ['bare_scalar_declaration','loop_local_declaration'])
        self.assertTrue(all(r['preceding_script_declaration_candidate'] is None for r in rows))

    def test_bare_declaration_location_does_not_include_preceding_blank_lines(self):
        rows=findings('\n\n  int value;')
        self.assertEqual(rows[0]['line'],3)


if __name__ == '__main__':
    unittest.main()
