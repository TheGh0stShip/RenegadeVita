import unittest
from tools.audit_script_command_bodies import inspect, inventory


class CommandBodyTests(unittest.TestCase):
    def test_comments_strings_and_nested_braces(self):
        source = 'void F() { /* return 0; */ const char *s="return false;"; if (s) { G(); } }'
        row = inspect(source, 'F')
        self.assertTrue(row['resolved'])
        self.assertEqual(row['return_statements'], 0)
        self.assertEqual(row['call_name_candidates'], ['G'])

    def test_ambiguity_is_retained(self):
        row = inspect('void F(int x) {} void F(float x) {}', 'F')
        self.assertFalse(row['resolved'])
        self.assertEqual([c['parameters'] for c in row['definition_candidates']], ['int x', 'float x'])

    def test_suffix_and_qualified_methods_do_not_match(self):
        row = inspect('void Prefix_F() {} void Class::F() {} void F() { G(); }', 'F')
        self.assertTrue(row['resolved'])
        self.assertEqual(row['call_name_candidates'], ['G'])

    def test_body_changes_do_not_promote_status(self):
        header = 'typedef struct { void (*First)(); void (*Second)(); } ScriptCommands;'
        old = 'void F() { G(); } void H() {} void Init() { EngineCommands.First = F; EngineCommands.Second = H; }'
        new = old.replace('G();', '#if defined(RENEGADE_VITA_PORT)\nreturn;\n#endif\nG();')
        result = inventory(header, old, new)
        self.assertEqual(result['total'], 2)
        self.assertTrue(all(row['status'] == 'unknown' for row in result['rows']))
        self.assertEqual(result['body_comparison_counts'], {'body_changed': 1, 'body_equal': 1})
