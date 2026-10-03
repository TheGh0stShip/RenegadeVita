import struct
import unittest
from tools.audit_visibility_bounds import validate


def chunk(kind, data):
    return struct.pack('<II', kind, len(data)) + data


class VisibilityBoundsTest(unittest.TestCase):
    def test_serialized_width_size_and_sector_bounds(self):
        variables = b''.join(bytes((k, 4)) + struct.pack('<I', v) for k, v in ((0, 0x10001), (2, 64), (3, 2)))
        base = chunk(0x34500000, variables)
        table = chunk(0x34500002, chunk(1, struct.pack('<I', 3)) + chunk(3, b'abc'))
        self.assertEqual(validate(base + chunk(0x34500001, struct.pack('<I', 1)) + table)['findings'], [])
        self.assertIn('table_id_outside_sector_count', validate(base + chunk(0x34500001, struct.pack('<I', 2)) + table)['findings'])
        with self.assertRaises(ValueError):
            validate(base + chunk(0x34500001, b'x'))
