import unittest
from tools.audit_script_parameter_surface import surface


class ParameterSurfaceTests(unittest.TestCase):
    def test_cinematic_and_shared_apis_included(self):
        rows = surface('Get_Next_Parameter(); Get_Parameters_String(buf, size); Get_Command_Parameter(foo(1));')
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row['balanced_arguments'] for row in rows))

    def test_definitions_are_not_claimed_as_calls(self):
        rows = surface('int Get_Int_Parameter(int index) const { return 0; }')
        self.assertEqual(rows[0]['syntax_kind'], 'definition_candidate')

    def test_disabled_comments_strings_ignored(self):
        rows = surface('#if 0\nGet_Parameter("A");\n#endif\n// Get_Parameter(0)\nconst char* a="Get_Parameter(0)";')
        self.assertEqual(rows, [])


if __name__ == '__main__':
    unittest.main()
