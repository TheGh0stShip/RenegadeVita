import importlib.util
import unittest

from sweep_cpp_functions import function_inventory


@unittest.skipUnless(importlib.util.find_spec('tree_sitter') and
                     importlib.util.find_spec('tree_sitter_cpp'), 'Pinned sweep parser not installed')
class CppFunctionInventoryTest(unittest.TestCase):
    def test_constructors_inline_templates_operators(self):
        text = ('namespace N { struct X { X() {} ~X() {} '
                'int operator()(int x) const { return x; } }; '
                'template<class T> T f(T x) { return x; } }')
        result = function_inventory(text)
        self.assertFalse(result['root_has_error'])
        self.assertEqual(len(result['functions']), 4)
        self.assertEqual(result['functions'][0]['scope'], 'N::X')

    def test_literal_and_conditional_returns_are_signals_not_stub_verdicts(self):
        result = function_inventory('int f(int x) { if (!x) return 0; return x; }')
        row = result['functions'][0]
        self.assertEqual(row['signals'], ['literal_return', 'nonfinal_return_candidate'])
        self.assertEqual(row['literal_returns'][0]['expression'], '0')

    def test_lambda_return_not_counted_as_outer_return(self):
        result = function_inventory('int f() { auto l=[]() { return 0; }; return l(); }')
        self.assertEqual(len(result['functions']), 2)
        self.assertEqual(result['functions'][0]['literal_returns'], [])
        self.assertEqual(result['functions'][1]['literal_returns'][0]['expression'], '0')

    def test_comments_and_raw_strings_do_not_invent_functions(self):
        result = function_inventory('const char *f() { /* void fake() {} */ '
                                    'return R"xx(void imaginary() {})xx"; }')
        self.assertEqual(len(result['functions']), 1)
        self.assertFalse(result['root_has_error'])

    def test_parse_failure_is_retained(self):
        result = function_inventory('int f( { return 0; }')
        self.assertTrue(result['root_has_error'])
        self.assertTrue(result['parse_errors'])

    def test_empty_and_marked_functions(self):
        result = function_inventory('void f() {} void g() { /* TODO unsupported */ }')
        self.assertEqual(result['functions'][0]['signals'], ['empty_body'])
        self.assertIn('unsupported_or_todo_marker', result['functions'][1]['signals'])

    def test_defaulted_and_deleted_are_definitions_without_parse_failure(self):
        result = function_inventory('struct X { X() = default; X(const X&) = delete; };')
        self.assertEqual(result['parse_errors'], [])
        self.assertEqual([r['body_kind'] for r in result['functions']],
                         ['default_method_clause', 'delete_method_clause'])
        self.assertEqual(result['functions'][0]['scope'], 'X')

    def test_call_provenance_is_syntax_not_resolved_reachability(self):
        result = function_inventory('void f() { Owner::Run(); ptr->Stop(); (*callback)(); '
                                    'auto l=[]() { Hidden(); }; l(); }')
        calls = result['functions'][0]['calls']
        self.assertEqual([r['callee'] for r in calls],
                         ['Owner::Run', 'ptr->Stop', '(*callback)', 'l'])
        self.assertEqual(result['functions'][1]['calls'][0]['callee'], 'Hidden')


if __name__ == '__main__':
    unittest.main()
