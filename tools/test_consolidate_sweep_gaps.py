import json
import unittest
from tools.consolidate_sweep_gaps import consolidate


class ConsolidationTest(unittest.TestCase):
    def test_review_is_provenance_and_conflicts_fail(self):
        data = {'total': 1, 'counts': {'missing': 1}, 'rows': [
            {'status': 'missing', 'symbol': 'D3DRS_ZBIAS', 'review': {
                'status': 'missing', 'original_owner': 'DX8Wrapper',
                'affected_scope': ['decals'], 'acceptance_open': 'native depth check'}}]}
        result = consolidate([('renderer', json.dumps(data).encode())])
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['rows'][0]['original_owner'], 'DX8Wrapper')
        self.assertEqual(result['rows'][0]['review_evidence_pointer'], '/rows/0/review')
        data['rows'][0]['review']['status'] = 'unknown'
        with self.assertRaises(ValueError):
            consolidate([('renderer', json.dumps(data).encode())])

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
