import unittest
from tools.audit_script_call_defaults import arguments, declarations, generate_header, inactive_lines, strip_comments


class ScriptCallDefaults(unittest.TestCase):
    def test_comment_delimiters_do_not_consume_live_calls(self):
        text = '//****** old comment\nCommands->Find_Object(7);\n"/* preserved */"; /* gone */'
        clean = strip_comments(text)
        self.assertIn('Commands->Find_Object(7)', clean)
        self.assertIn('"/* preserved */"', clean)
        self.assertEqual(text.count('\n'), clean.count('\n'))

    def test_nested_expressions_and_literals_are_one_argument(self):
        values, end = arguments('obj, Vector3(1,2,3), "a,b", f({1,2}, x))tail', 0)
        self.assertEqual(values, ['obj', 'Vector3(1,2,3)', '"a,b"', 'f({1,2}, x)'])
        self.assertEqual('tail', 'obj, Vector3(1,2,3), "a,b", f({1,2}, x))tail'[end + 1:])

    def test_original_defaults_are_preserved(self):
        table = declarations('void (*Start_Conversation)(int id, int action = 0); '
                             'void (*Create_Conversation)(const char *name, float range = 0.0F);')
        self.assertEqual(table['Start_Conversation'], [None, '0'])
        self.assertEqual(table['Create_Conversation'], [None, '0.0F'])

    def test_only_literal_disabled_branches_are_proven(self):
        lines = inactive_lines('#if 0\ncall();\n#if SOMETHING\ncall();\n#endif\n#else\nlive();\n#endif\n')
        self.assertIn(2, lines)
        self.assertIn(4, lines)
        self.assertNotIn(7, lines)


if __name__ == '__main__':
    unittest.main()
