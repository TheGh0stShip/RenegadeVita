import struct
import unittest
from tools.diagnostics.definition_factory_audit import definition_classes


def chunk(kind, data):
    return struct.pack('<II', kind, 0x80000000 | len(data)) + data


class DefinitionFactoryAuditTests(unittest.TestCase):
    def test_original_definition_manager_container(self):
        data = chunk(0x101, chunk(0x100, b'') + chunk(0x101,
            chunk(0x40121, b'opaque object') + chunk(0x40121, b'other') +
            chunk(0x40122, b''))) + chunk(0x102, b'other save subsystem')
        self.assertEqual(definition_classes(data), {0x40121: 2, 0x40122: 1})

    def test_empty_and_other_subsystem(self):
        self.assertEqual(definition_classes(b''), {})
        self.assertEqual(definition_classes(chunk(0x102, b'not a definition')), {})

    def test_nested_bounds_fail_closed(self):
        for data in (b'\x00', struct.pack('<II', 0x101, 100),
                     chunk(0x101, b'bad'), chunk(0x101, chunk(0x101, b'bad'))):
            with self.assertRaises(ValueError):
                definition_classes(data)


if __name__ == '__main__':
    unittest.main()
