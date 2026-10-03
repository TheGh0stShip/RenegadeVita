import struct
import unittest
from tools.audit_level_chunk_inventory import summarize


class ChunkInventoryTest(unittest.TestCase):
    def test_local_ids_keep_parent_context_and_count(self):
        leaf = struct.pack('<II', 7, 1) + b'x'
        data = struct.pack('<II', 1, 0x80000000 | len(leaf)*2) + leaf*2
        data += struct.pack('<II', 2, 0x80000000 | len(leaf)) + leaf
        rows = summarize(data)
        local = [r for r in rows if len(r['chunk_path']) == 2]
        self.assertEqual([r['count'] for r in local], [2, 1])
        self.assertNotEqual(local[0]['chunk_path'], local[1]['chunk_path'])
        self.assertEqual(local[0]['first_offset'], 8)

    def test_bad_bounds_rejected(self):
        with self.assertRaises(ValueError):
            summarize(struct.pack('<II', 1, 99))
