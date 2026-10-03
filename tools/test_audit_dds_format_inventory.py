import struct
import unittest
import tempfile
from pathlib import Path

from audit_dds_format_inventory import audit, inspect_header
from make_ttfs_fixture import make_mix


class DDSHeaderTest(unittest.TestCase):
    def test_duplicate_names_keep_both_index_records(self):
        # A valid authored MIX with two same-name records and different payloads.
        import zlib
        name = b'duplicate.dds\0'
        crc = zlib.crc32(name[:-1].upper())
        index = struct.pack('<I', 2) + struct.pack('<III', crc, 12, 4) + struct.pack('<III', crc, 16, 4)
        names = struct.pack('<I', 2) + bytes([len(name)]) + name + bytes([len(name)]) + name
        data = struct.pack('<4sII', b'MIX1', 20, 48) + b'DDS DDS ' + index + names
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'duplicate.mix').write_bytes(data)
            result = audit(root)
        self.assertEqual(result['totals']['dds_members'], 2)
        self.assertEqual([r['index_record'] for r in result['rows']], [0, 1])
        self.assertEqual(result['archives'][0]['unique_names'], 1)
        self.assertEqual(len({r['row_id'] for r in result['rows']}), 2)
        self.assertEqual(len(result['archives'][0]['sha256']), 64)
        self.assertEqual(result['rows'][0]['status'], 'unknown')

    def test_archive_scan_retains_invalid_members_and_archive_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'fixture.mix').write_bytes(make_mix({'bad.dds': b'DDS '}))
            (root / 'broken.dat').write_bytes(b'bad')
            result = audit(root)
        self.assertEqual(result['totals']['by_format'], {'invalid': 1})
        self.assertEqual(result['rows'][0]['member'], 'bad.dds')
        self.assertEqual(len(result['archive_errors']), 1)
        self.assertFalse(result['complete'])

    def test_explicit_little_endian_fourcc_and_dimensions(self):
        data = bytearray(128)
        data[:4] = b'DDS '
        struct.pack_into('<I', data, 4, 124)
        struct.pack_into('<II', data, 12, 16, 32)
        struct.pack_into('<I', data, 76, 32)
        struct.pack_into('<I', data, 80, 4)
        data[84:88] = b'DXT3'
        result = inspect_header(bytes(data))
        self.assertEqual((result['width'], result['height'], result['format']), (32, 16, 'DXT3'))

    def test_short_and_invalid_header_rejected(self):
        for data in (b'', bytes(128), b'DDS ' + bytes(124)):
            with self.assertRaises(ValueError):
                inspect_header(data)
