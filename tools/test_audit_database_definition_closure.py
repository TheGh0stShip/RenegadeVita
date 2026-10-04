import unittest

from audit_database_definition_closure import reconcile


class DatabaseDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.persist = {'rows': [{'chunk_id': 42, 'chunk_id_hex': '0x0000002A',
                                 'candidate_instances': 7, 'arm_classes': ['Original']}]}
        self.definitions = {'rows': [{'class_id': 99, 'classes': ['Original'],
                                     'matches': True, 'arm_symbol_present': True}]}

    def test_distinguishes_persistence_and_class_ids(self):
        row = reconcile(self.persist, self.definitions)['rows'][0]
        self.assertEqual(row['persistence_chunk_id'], 42)
        self.assertEqual(row['definition_class_ids'], [99])
        self.assertEqual(row['status'], 'unknown')

    def test_unmapped_is_retained(self):
        result = reconcile(self.persist, {'rows': []})
        self.assertEqual(result['totals']['unmapped'], 1)
        self.assertFalse(result['rows'][0]['all_host_definition_lookups_match'])

    def test_conflicting_class_ids_are_ambiguous(self):
        self.definitions['rows'].append({'class_id': 100, 'classes': ['Original'],
                                        'matches': False, 'arm_symbol_present': False})
        row = reconcile(self.persist, self.definitions)['rows'][0]
        self.assertTrue(row['class_id_mapping_ambiguous'])
        self.assertFalse(row['all_host_definition_lookups_match'])
        self.assertFalse(row['all_arm_definition_symbols_present'])


if __name__ == '__main__':
    unittest.main()
