import copy
import unittest

from audit_level_persist_closure import reconcile


class PersistClosureTests(unittest.TestCase):
    def setUp(self):
        self.levels = {'rows': [{'map': 'M01.mix', 'members': [{
            'member': 'M01.ldd', 'sha256': 'fixture', 'index_record': 0,
            'chunk_paths': [
                {'chunk_path': ['0x0000002A', '0x00100100'], 'count': 2,
                 'payload_bytes_sum': 8, 'first_offset': 8},
                {'chunk_path': ['0x0000002A', '0x00100101'], 'count': 2,
                 'payload_bytes_sum': 32, 'first_offset': 20}]}]}]}
        self.arm = {'persist_load_methods': [{'chunk_id': 42, 'class': 'Original'}]}
        self.host = {'rows': [{'chunk_id': 42, 'matches': True}]}

    def run_case(self, levels=None, arm=None, host=None):
        return reconcile(levels or self.levels, arm or self.arm, host or self.host)

    def test_matching_evidence_remains_unknown(self):
        result = self.run_case()
        self.assertEqual(result['totals']['candidate_instances'], 2)
        self.assertTrue(result['rows'][0]['arm_load_symbol_present'])
        self.assertTrue(result['rows'][0]['host_lookup_matches'])
        self.assertEqual(result['rows'][0]['status'], 'unknown')

    def test_leaf_ids_are_not_factories(self):
        self.levels['rows'][0]['members'][0]['chunk_paths'][0]['chunk_path'][-1] = '0x0000002A'
        self.assertEqual(self.run_case()['rows'], [])

    def test_missing_or_mismatched_data_is_a_risk(self):
        for count in (0, 1, 3):
            levels = copy.deepcopy(self.levels)
            levels['rows'][0]['members'][0]['chunk_paths'][1]['count'] = count
            result = self.run_case(levels=levels)
            self.assertEqual(result['rows'], [])
            self.assertEqual(len(result['risks']), 1)

    def test_pointer_tokens_remain_four_bytes(self):
        self.levels['rows'][0]['members'][0]['chunk_paths'][0]['payload_bytes_sum'] = 16
        self.assertEqual(self.run_case()['totals']['metadata_risks'], 1)

    def test_missing_symbol_and_lookup_are_separate(self):
        result = self.run_case(arm={'persist_load_methods': []}, host={'rows': []})
        self.assertEqual(result['totals']['without_arm_symbol'], 1)
        self.assertEqual(result['totals']['without_host_lookup'], 1)

    def test_duplicate_ancestry_rejected(self):
        member = self.levels['rows'][0]['members'][0]
        member['chunk_paths'].append(copy.deepcopy(member['chunk_paths'][0]))
        with self.assertRaises(ValueError):
            self.run_case()


if __name__ == '__main__':
    unittest.main()
