import struct
import unittest
from tools.diagnostics.w3d_animation_channel_audit import audit_w3d


def chunk(kind, data):
    return struct.pack('<II', kind, len(data)) + data


def motion(kind=0, pivot=1, first=0, last=1):
    return chunk(0x202, struct.pack('<6H2f', first, last, 1, kind, pivot, 0, 0., 1.))


class ChannelAuditTests(unittest.TestCase):
    def test_supported_and_bit_visibility(self):
        bit = chunk(0x203, struct.pack('<4HBB', 0, 1, 0, 1, 1, 3))
        self.assertEqual(audit_w3d(chunk(0x200, motion() + bit)), [])

    def test_unknown_and_duplicate_motion(self):
        result = audit_w3d(chunk(0x200, motion(15) + motion(0) + motion(0)))
        self.assertEqual(result[0]['reasons'], ['unsupported_raw_channel_type'])
        self.assertEqual(result[0]['data_bytes'], 8)
        self.assertEqual(result[1]['reasons'], ['replaces_owned_channel'])

    def test_invalid_frame_range(self):
        result = audit_w3d(chunk(0x200, motion(first=2, last=1)))
        self.assertEqual(result[0]['reasons'], ['invalid_frame_range_or_payload'])

    def test_truncated_headers_and_payloads(self):
        for data in (b'bad', chunk(0x200, b'bad'), chunk(0x200, chunk(0x203, bytes(8)))):
            with self.assertRaises(ValueError):
                audit_w3d(data)
        result = audit_w3d(chunk(0x200, chunk(0x202, struct.pack('<6H', 0, 1, 1, 0, 1, 0))))
        self.assertEqual(result[0]['reasons'], ['invalid_frame_range_or_payload'])


if __name__ == '__main__':
    unittest.main()
