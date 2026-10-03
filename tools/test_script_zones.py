import struct
import unittest
from tools.audit_script_zones import decode_bounds, decode_definition


def field(kind, payload):
    return bytes((kind, len(payload))) + payload


class ZoneDecoderTests(unittest.TestCase):
    def test_explicit_float32_basis_center_extent_layout(self):
        values = list(range(15))
        row = decode_bounds(field(1, struct.pack('<15f', *values)))
        self.assertEqual(row['basis'], list(range(9)))
        self.assertEqual(row['center'], [9, 10, 11])
        self.assertEqual(row['extent'], [12, 13, 14])

    def test_bounds_width_duplicates_and_nonfinite_rejected(self):
        good = field(1, struct.pack('<15f', *([0] * 15)))
        for data in (field(1, b'\0' * 59), good + good,
                     field(1, struct.pack('<15f', *([float('nan')] + [0] * 14)))):
            with self.assertRaises(ValueError):
                decode_bounds(data)

    def test_negative_extent_is_retained_as_finding(self):
        row = decode_bounds(field(1, struct.pack('<15f', *([0] * 12 + [-1, 2, 3]))))
        self.assertEqual(row['findings'], ['negative_extent'])

    def test_missing_definition_fields_remain_unknown(self):
        row = decode_definition(b'')
        self.assertIsNone(row['check_stars_only'])
        self.assertIsNone(row['zone_type'])

    def test_boolean_and_signed32_type_are_strict(self):
        row = decode_definition(field(3, b'\1') + field(4, struct.pack('<i', -1)))
        self.assertTrue(row['check_stars_only'])
        self.assertEqual(row['zone_type'], -1)
        for data in (field(3, b'\2'), field(3, b'\0\0'), field(4, b'\1'),
                     field(3, b'\1') + field(3, b'\0')):
            with self.assertRaises(ValueError):
                decode_definition(data)


if __name__ == '__main__':
    unittest.main()
