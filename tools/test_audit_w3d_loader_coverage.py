import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from tools.audit_w3d_loader_coverage import chunk_paths, scan


def chunk(kind, payload, nested=False):
    return struct.pack('<II', kind, len(payload) | (0x80000000 if nested else 0)) + payload


class W3dInventoryTest(unittest.TestCase):
    def test_original_root_owners_open_flag_clear_children(self):
        leaf=chunk(0x1f,b'header')
        for kind in (0,0x100,0x200):
            self.assertEqual([r[0] for r in chunk_paths(chunk(kind,leaf))],
                             [(kind,),(kind,0x1f)])
        # Box data is a fixed structure; never speculate that it contains chunks.
        self.assertEqual([r[0] for r in chunk_paths(chunk(0x740,leaf))],[(0x740,)])

    def test_parent_context_repetition_and_bounds(self):
        leaf = chunk(7, b'x')
        data = chunk(1, leaf * 2, True) + chunk(2, leaf, True)
        rows = chunk_paths(data)
        self.assertEqual([r[0] for r in rows], [(1,), (1, 7), (1, 7), (2,), (2, 7)])
        self.assertEqual(rows[2][1], 17)
        with self.assertRaises(ValueError):
            chunk_paths(chunk(1, leaf[:-1], True))

    def test_all_archives_and_duplicate_index_records(self):
        data = chunk(0x741, b'')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('M11.mix', 'always.dat', 'custom.dbs'):
                (root/name).write_bytes(data * 2)
            archive = SimpleNamespace(entry_records=[('same.W3D', 0, 0, len(data)),
                                                     ('same.W3D', 0, len(data), len(data))])
            with patch('tools.audit_w3d_loader_coverage.MixArchive', return_value=archive):
                result = scan(root)
            self.assertEqual(len(result['archives']), 3)
            self.assertEqual(result['totals']['w3d_members'], 6)
            self.assertEqual(result['totals']['chunk_occurrences'], 6)
            for row in result['archives']:
                self.assertEqual(row['w3d_files'], 2)
                self.assertEqual([r['index_record'] for r in row['members']], [0, 1])
                self.assertEqual(row['root_chunks']['0x00000741'], 2)
                self.assertEqual(row['chunk_paths'][0]['count'], 2)


if __name__ == '__main__':
    unittest.main()
