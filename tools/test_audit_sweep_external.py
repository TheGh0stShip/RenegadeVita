import unittest
from tools.audit_sweep_external import compare


class ReferenceTreeTest(unittest.TestCase):
    def test_union_includes_deletions_and_unchanged(self):
        tree = {'truncated': False, 'tree': [
            {'type': 'blob', 'path': 'same', 'sha': '1'},
            {'type': 'blob', 'path': 'changed', 'sha': '2'},
            {'type': 'blob', 'path': 'new', 'sha': '3'},
            {'type': 'tree', 'path': 'directory', 'sha': '4'}]}
        rows = compare({'same': '1', 'changed': '0', 'removed': '5'}, tree)
        self.assertEqual({r['source']: r['relation'] for r in rows},
                         {'same': 'same_blob', 'changed': 'different_blob',
                          'new': 'reference_only', 'removed': 'ea_only'})
        self.assertTrue(all(r['status'] == 'unknown' for r in rows))

    def test_rejects_truncated_or_duplicate_tree(self):
        with self.assertRaises(ValueError):
            compare({}, {'truncated': True, 'tree': []})
        row = {'type': 'blob', 'path': 'one', 'sha': '1'}
        with self.assertRaises(ValueError):
            compare({}, {'tree': [row, row]})
