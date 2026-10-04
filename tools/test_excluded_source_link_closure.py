import unittest
from tools.check_excluded_original_sources import compare_symbols, symbol_inventory


class ExcludedSourceLinkClosureTest(unittest.TestCase):
    def test_raw_symbols_keep_aliases_and_weak_definitions(self):
        parsed = symbol_inventory('         U missing\n00000000 T ctor1\n'
                                  '00000000 T ctor2\n00000000 W weak\narchive.o:\n')
        self.assertEqual(parsed, {'missing': 'U', 'ctor1': 'T', 'ctor2': 'T', 'weak': 'W'})
        result = compare_symbols({'missing': 'U', 'available': 'U'}, parsed,
                                 {'available': 'T', 'ctor1': 'T', 'ctor2': 'T', 'weak': 'T'})
        self.assertEqual(result['absent_symbol_candidates'], ['missing'])
        self.assertEqual(result['strong_definition_overlap_candidates'], ['ctor1', 'ctor2'])

    def test_local_or_undefined_entries_do_not_create_strong_overlap(self):
        result = compare_symbols({}, {'local': 't', 'undefined': 'U', 'weak': 'W'},
                                 {'local': 'T', 'undefined': 'T', 'weak': 'T'})
        self.assertEqual(result['strong_definition_overlap_candidates'], [])

    def test_unlinked_strong_definition_is_not_an_overlap(self):
        result = compare_symbols({}, {'new_owner': 'T'}, {})
        self.assertEqual(result['strong_definition_overlap_candidates'], [])


if __name__ == '__main__':
    unittest.main()
