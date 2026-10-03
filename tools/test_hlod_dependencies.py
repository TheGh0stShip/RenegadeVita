import struct
import unittest

from tools.audit_hlod_dependencies import inspect_hlod
from tools.test_prelit_material_candidates import chunk


def name(value, width):
    return value.encode('ascii') + bytes(width - len(value))


def array(kind, names):
    return chunk(kind, chunk(0x703, struct.pack('<If', len(names), 1.0)) +
                 b''.join(chunk(0x704, struct.pack('<I', i) + name(n, 32))
                          for i, n in enumerate(names)))


def hlod(arrays, count=1):
    return chunk(0x700, chunk(0x701, struct.pack('<II', 0x10000, count) +
                             name('RIG', 16) + name('TREE', 16)) + arrays)


class HlodDependencies(unittest.TestCase):
    def test_lods_aggregates_and_repeated_names_preserved(self):
        data = hlod(array(0x702, ['RIG.BODY', 'RIG.BODY']) +
                    array(0x702, ['RIG.LOW']) + array(0x705, ['ATTACH']) +
                    chunk(0x706, b'proxy data'), 2)
        row = inspect_hlod(data)[0]
        self.assertEqual(row['hierarchy_name'], 'TREE')
        self.assertEqual([o['name'] for o in row['arrays'][0]['objects']], ['RIG.BODY'] * 2)
        self.assertEqual(row['arrays'][2]['kind'], 'aggregate')
        self.assertFalse(row['runtime_resolution_proven'])

    def test_counts_and_fixed_widths_are_not_guessed(self):
        with self.assertRaises(ValueError):
            inspect_hlod(hlod(array(0x702, []), 2))
        with self.assertRaises(ValueError):
            inspect_hlod(hlod(chunk(0x702, chunk(0x703, struct.pack('<If', 1, 1.0)))))
        with self.assertRaises(ValueError):
            inspect_hlod(hlod(chunk(0x702, chunk(0x703, struct.pack('<If', 1, 1.0)) +
                              chunk(0x704, bytes(35)))))
        with self.assertRaises(ValueError):
            inspect_hlod(hlod(chunk(0x702, chunk(0x703, struct.pack('<If', 1, 1.0)) +
                              chunk(0x704, bytes(4) + b'X' * 32))))
        self.assertEqual(inspect_hlod(chunk(0x200, b'not an HLOD')), [])
