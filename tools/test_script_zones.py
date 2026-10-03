import struct
import unittest
from tools.audit_script_zones import decode_bounds, decode_definition, scan


def field(kind, payload):
    return bytes((kind, len(payload))) + payload


def chunk(kind, payload, nested=False):
    return struct.pack('<II', kind, len(payload) | (0x80000000 if nested else 0)) + payload


def factory(body):
    return chunk(123, chunk(0x100100, struct.pack('<I', 0xf1234567)) +
                 chunk(0x100101, body, True), True)


class ZoneDecoderTests(unittest.TestCase):
    def test_valid_instance_preserves_unsigned_disk_ids(self):
        identity = field(2, struct.pack('<I', 0xf0000001)) + field(3, struct.pack('<I', 100376))
        bounds = field(1, struct.pack('<15f', *([1, 0, 0, 0, 1, 0, 0, 0, 1] +
                                             [10, -20, 30, 1, 2, 3])))
        rows = scan(factory(chunk(910991407, identity) + chunk(922991807, bounds)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['definition_id'], 0xf0000001)
        self.assertEqual(rows[0]['instance_id'], 100376)
        self.assertEqual(rows[0]['center'], [10, -20, 30])
        self.assertEqual(rows[0]['findings'], [])
        with self.assertRaisesRegex(ValueError, 'duplicate zone field'):
            scan(factory(chunk(910991407, identity + field(3, struct.pack('<I', 99))) +
                         chunk(922991807, bounds)))

    def test_valid_definition_retains_false_filter_and_signed_type(self):
        identity = field(1, struct.pack('<I', 0xf0000001)) + field(3, b'SyntheticZone\0')
        variables = field(3, b'\0') + field(4, struct.pack('<i', -1)) + field(5, b'\1')
        rows = scan(factory(chunk(0x100, identity) + chunk(1111991133, variables)), definitions=True)
        self.assertEqual(rows, [{'definition_id': 0xf0000001, 'check_stars_only': False,
                                'environment_zone': True, 'zone_type': -1}])

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
