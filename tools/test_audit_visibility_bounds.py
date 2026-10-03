import struct
import unittest
import hashlib
from tools.audit_visibility_bounds import validate, audit_candidate, matching_chunks
from tools.audit_level_spatial_presence import SIGNATURES


def chunk(kind, data):
    return struct.pack('<II', kind, len(data)) + data


class VisibilityBoundsTest(unittest.TestCase):
    def test_repeated_chunks_and_parent_context_reconcile(self):
        variables = b''.join(bytes((k, 4)) + struct.pack('<I', v)
                             for k, v in ((0, 0x10001), (2, 64), (3, 2)))
        leaf = chunk(0x4700, chunk(0x34500000, variables))
        def parent(kind, payload):
            return struct.pack('<II', kind, len(payload) | 0x80000000) + payload
        data = parent(0x20000, parent(0x4433220, leaf * 2) +
                      parent(0x4433221, leaf))
        nodes = matching_chunks(data, SIGNATURES['visibility_tables'])
        candidate = {'member_sha256': hashlib.sha256(data).hexdigest(),
                     'count': 2, 'first_offset': nodes[0].offset,
                     'payload_bytes_sum': sum(len(n.data) for n in nodes)}
        rows = audit_candidate(data, candidate)
        self.assertEqual(len(rows), 2)
        self.assertEqual([r['offset'] for r in rows], [16, 16 + len(leaf)])
        self.assertTrue(all(r['findings'] == [] for r in rows))
        with self.assertRaises(ValueError):
            audit_candidate(data, dict(candidate, count=1))
        with self.assertRaises(ValueError):
            audit_candidate(data + b'x', candidate)

    def test_serialized_width_size_and_sector_bounds(self):
        variables = b''.join(bytes((k, 4)) + struct.pack('<I', v) for k, v in ((0, 0x10001), (2, 64), (3, 2)))
        base = chunk(0x34500000, variables)
        table = chunk(0x34500002, chunk(1, struct.pack('<I', 3)) + chunk(3, b'abc'))
        self.assertEqual(validate(base + chunk(0x34500001, struct.pack('<I', 1)) + table)['findings'], [])
        self.assertIn('table_id_outside_sector_count', validate(base + chunk(0x34500001, struct.pack('<I', 2)) + table)['findings'])
        with self.assertRaises(ValueError):
            validate(base + chunk(0x34500001, b'x'))

    def test_duplicate_variables_and_unknown_table_children_remain_visible(self):
        variables = b''.join(bytes((k, 4)) + struct.pack('<I', v)
                             for k, v in ((0, 0x10001), (2, 64), (3, 2), (3, 2)))
        table = chunk(0x34500002, chunk(1, struct.pack('<I', 3)) +
                      chunk(3, b'abc') + chunk(99, b''))
        result = validate(chunk(0x34500000, variables) +
                          chunk(0x34500001, struct.pack('<I', 1)) + table)
        self.assertEqual(result['findings'], ['duplicate_visibility_variable',
                                             'unknown_compressed_table_chunk'])
