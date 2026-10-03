import struct
import unittest

from tools.audit_prelit_material_candidates import inspect_prelit, select_prelit


def chunk(kind, payload, container=False):
    return struct.pack('<II', kind, len(payload) | (0x80000000 if container else 0)) + payload


def mesh(flags, wrappers):
    header = struct.pack('<II', 0x40002, flags) + bytes(32)
    return chunk(0, chunk(0x1f, header) + wrappers, True)


class PrelitCandidates(unittest.TestCase):
    def test_quality_fallthrough_does_not_select_higher_mode(self):
        self.assertEqual(select_prelit(0x0e000000, 2), 0x26)
        self.assertEqual(select_prelit(0x0a000000, 1), 0x24)
        self.assertIsNone(select_prelit(0x08000000, 0))
        self.assertEqual(select_prelit(0x01000000, 2), 0x23)
        self.assertIsNone(select_prelit(0, 2))
        with self.assertRaises(ValueError):
            select_prelit(0x0f000000, 3)

    def test_unflagged_pass_and_selected_wrapper_only(self):
        ids = chunk(0x39, struct.pack('<I', 0))
        repeated = chunk(0x38, ids + ids)
        single = chunk(0x38, ids)
        data = mesh(0x06000000, chunk(0x24, repeated) + chunk(0x25, single))
        rows = inspect_prelit(data, 1)
        self.assertFalse(rows[0]['passes'][0]['alternate_material_candidate'])
        vertex = inspect_prelit(data, 0)[0]
        self.assertTrue(vertex['passes'][0]['alternate_material_candidate'])
        self.assertFalse(vertex['loader_execution_proven'])

    def test_ambiguous_missing_and_truncated_containers(self):
        wrapper = chunk(0x24, b'')
        self.assertEqual(inspect_prelit(mesh(0x02000000, wrapper * 2), 0)[0]['passes'], [])
        self.assertTrue(inspect_prelit(mesh(0x02000000, b''), 0)[0]['findings'])
        self.assertTrue(inspect_prelit(mesh(0x08000000, b''), 0)[0]['findings'])
        with self.assertRaises(ValueError):
            inspect_prelit(mesh(0x02000000, chunk(0x24, chunk(0x38, b'bad'))), 0)


if __name__ == '__main__':
    unittest.main()
