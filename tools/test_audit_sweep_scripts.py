import unittest
from tools.audit_sweep_scripts import command_slots, function_symbols


class ScriptSweepTests(unittest.TestCase):
    def test_function_candidates_keep_overloads_and_reject_data_or_member_names(self):
        symbols = {'Foo(int)': [{'address': '1', 'type': 'T'}],
                   'Foo(float)': [{'address': '2', 'type': 't'}],
                   'FooData()': [{'address': '3', 'type': 'T'}],
                   'Class::Foo(int)': [{'address': '4', 'type': 'T'}],
                   'Foo()': [{'address': '5', 'type': 'B'}]}
        self.assertEqual([row['symbol'] for row in function_symbols(['Foo'], symbols)],
                         ['Foo(float)', 'Foo(int)'])
    def test_only_command_structure_slots_not_other_callbacks(self):
        code = '''void (*Outside)(int);
typedef struct {
unsigned int Version;
// void (*Fake)(int);
void ( * First )(int value = 0);
bool (*Second)(const char *name);
} ScriptCommands;
void (*After)(int);
'''
        rows = command_slots(code)
        self.assertEqual([r['name'] for r in rows], ['First', 'Second'])
        self.assertEqual([r['line'] for r in rows], [5, 6])

    def test_missing_structure_fails_explicitly(self):
        with self.assertRaises(ValueError):
            command_slots('void (*Outside)(int);')
