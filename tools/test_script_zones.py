import struct
import unittest
from tools.audit_script_zones import decode_bounds, decode_definition, scan


def field(kind, payload):
    return bytes((kind, len(payload))) + payload


class ZoneDecoderTests(unittest.TestCase):
    def test_basis_quality_and_zero_extents_are_only_leads(self):
        identity = [1, 0, 0, 0, 1, 0, 0, 0, 1]
        row = decode_bounds(field(1, struct.pack('<15f', *(identity + [0, 0, 0, 1, 1, 1]))))
        self.assertEqual(row['findings'], [])
        scaled = identity[:]
        scaled[0] = 2
        row = decode_bounds(field(1, struct.pack('<15f', *(scaled + [0, 0, 0, 0, 1, 1]))))
        self.assertEqual(row['findings'], ['zero_extent', 'basis_orthogonality_lead'])

    def test_variable_bytes_without_factory_are_not_zones(self):
        payload = field(1, struct.pack('<15f', *([0] * 15)))
        self.assertEqual(scan(struct.pack('<II', 922991807, len(payload)) + payload), [])

    def test_ambiguous_factory_variables_rejected(self):
        def chunk(kind, payload, nested=False):
            return struct.pack('<II', kind, len(payload) | (0x80000000 if nested else 0)) + payload
        payload = field(1, struct.pack('<15f', *([0] * 15)))
        variables = chunk(922991807, payload)
        factory = chunk(123, chunk(0x100100, struct.pack('<I', 1)) +
                        chunk(0x100101, variables + variables, True), True)
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            scan(factory)
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
        self.assertIn('negative_extent', row['findings'])

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
