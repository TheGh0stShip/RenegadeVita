import struct
import unittest
from tools.audit_nested_w3d_references import references


def chunk(kind, payload, nested=False):
    return struct.pack('<II', kind, len(payload) | (0x80000000 if nested else 0))+payload


class NestedReferences(unittest.TestCase):
    def test_nested_texture_and_model(self):
        data = chunk(0x700, chunk(0x704, struct.pack('<I', 7)+b'BODY'.ljust(32,b'\0')), True)
        data += chunk(0, chunk(0x32, b'VEHICLE.TGA\0'), True)
        self.assertEqual(references(data), [('hlod_subobject','body'),('texture','vehicle.tga')])

    def test_truncated_child(self):
        with self.assertRaises(ValueError):
            references(chunk(0, struct.pack('<II',0x32,99), True))

    def test_bad_disk_width(self):
        with self.assertRaises(ValueError):
            references(chunk(0x704,b'x'*40))

    def test_leaf_not_recursed(self):
        self.assertEqual(references(chunk(0x123,b'x'*11)),[])
