import unittest
from tools.audit_level_spatial_presence import reconcile, SIGNATURES


class SpatialPresenceTest(unittest.TestCase):
    def test_same_leaf_under_wrong_owner_does_not_match(self):
        sig = SIGNATURES['visibility_tables']
        inventory = {'rows': [{'map': 'test', 'members': [{'member': 'test.lsd',
            'sha256': 'hash', 'index_record': 0, 'chunk_paths': [
                {'chunk_path': ['0xDEADBEEF', *sig[1:]], 'first_offset': 8, 'count': 1, 'payload_bytes_sum': 20}]}]}]}
        self.assertFalse(any(r['located'] for r in reconcile(inventory)))
        inventory['rows'][0]['members'][0]['chunk_paths'][0]['chunk_path'] = list(sig)
        rows = reconcile(inventory)
        self.assertTrue(rows[0]['located'])
        self.assertEqual(rows[0]['status'], 'unknown')
