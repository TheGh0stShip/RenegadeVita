import json
import unittest
from tools.consolidate_sweep_gaps import consolidate


class ConsolidationTest(unittest.TestCase):
    def test_nested_unknown_and_original_filter(self):
        data = {'total': 2, 'counts': {'unknown': 1, 'original_compiled': 1},
                'rows': [{'status': 'unknown', 'map': 'M09',
                          'nested': [{'status': 'missing', 'name': 'factory'}]},
                         {'status': 'original_compiled'}]}
        result = consolidate([('retail', json.dumps(data).encode())])
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['rows'][0]['inventory_pointer'], '/rows/0/nested/0')
        self.assertEqual(result['rows'][0]['affected_missions_modes'], ['M09'])
        self.assertEqual(result['rows'][1]['severity'], 'unclassified')

    def test_denominator_and_status_mismatch_fail(self):
        for data in ({'total': 2, 'rows': [], 'counts': {}},
                     {'total': 1, 'rows': [{'status': 'unknown'}], 'counts': {'missing': 1}}):
            with self.assertRaises(ValueError):
                consolidate([('scripts', json.dumps(data).encode())])
