import unittest
from tools.audit_script_command_table import compare, table_assignments


class ScriptCommandTableTests(unittest.TestCase):
    def test_comments_and_strings_do_not_register(self):
        source = '// EngineCommands.Missing = Missing;\nconst char*x="EngineCommands.Fake = Fake;";\nEngineCommands.Real=&Real;'
        self.assertEqual(table_assignments(source), {'Real': ['Real']})

    def test_missing_and_null_are_distinct(self):
        scripts = [{'owner': 'fixture.cpp', 'body': 'Commands->Missing(); Commands->Null(); Commands->Good();'}]
        result = compare(scripts, table_assignments('EngineCommands.Null=NULL; EngineCommands.Good=&Good;'))
        self.assertEqual(result['missing_assignments'], ['Missing'])
        self.assertEqual(result['unresolved_assignments'], ['Null'])
        self.assertFalse(result['compiled_registration_or_behavior_proven'])

    def test_conflicting_conditional_candidates_stay_unresolved(self):
        table = table_assignments('#if PLATFORM\nEngineCommands.Foo=A;\n#else\nEngineCommands.Foo=B;\n#endif')
        result = compare([{'owner': 'fixture.cpp', 'body': 'Commands->Foo();'}], table)
        self.assertEqual(result['unresolved_assignments'], ['Foo'])

    def test_unsupported_expression_is_not_function_proof(self):
        table = table_assignments('EngineCommands.Foo=choose();')
        result = compare([{'owner': 'fixture.cpp', 'body': 'Commands->Foo();'}], table)
        self.assertEqual(result['unresolved_assignments'], ['Foo'])

    def test_duplicate_calls_keep_all_source_owners(self):
        scripts = [{'owner': name, 'body': 'Commands->Foo(); Commands->Foo();'} for name in ('a.cpp', 'b.cpp')]
        result = compare(scripts, {'Foo': ['Foo']})
        self.assertEqual(result['used_commands'], 1)
        self.assertEqual(result['commands']['Foo']['owners'], ['a.cpp', 'b.cpp'])


if __name__ == '__main__':
    unittest.main()
