import struct
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.audit_nested_w3d_references import references, scan, summary


def chunk(kind, payload, nested=False):
    return struct.pack('<II', kind, len(payload) | (0x80000000 if nested else 0))+payload


class NestedReferences(unittest.TestCase):
    def test_later_maps_duplicate_names_and_dds_fallback(self):
        payload=chunk(0,chunk(0x32,b'TEX.TGA\0')+chunk(0x32,b'MISSING.TGA\0'),True)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            path=root/'M11.mix'
            path.write_bytes(payload*2)
            archive=SimpleNamespace(path=path,entries={'tex.dds':(0,0,0)},
                entry_records=[('same.W3D',0,0,len(payload)),('same.W3D',0,len(payload),len(payload))])
            with patch('tools.audit_nested_w3d_references.MixArchive',return_value=archive):
                result=scan(root)
            self.assertEqual(result['w3d_members'],2)
            self.assertEqual(result['reference_counts'],{'texture':4})
            self.assertEqual([r['index_record'] for r in result['member_receipts']],[0,1])
            rows={r['reference']:r for r in result['references']}
            self.assertEqual(rows['tex.tga']['occurrence_count'],2)
            self.assertTrue(rows['tex.tga']['filename_or_dds_available_anywhere'])
            self.assertFalse(rows['missing.tga']['filename_or_dds_available_anywhere'])
            self.assertEqual(rows['tex.tga']['chunk_paths'],[['0x00000000','0x00000032']])
            public=summary(result)
            self.assertEqual(public['total'],2)
            self.assertEqual(public['rows'][0]['reference_occurrences'],4)
            self.assertEqual(public['rows'][0]['unresolved_texture_occurrences'],2)
            self.assertEqual(len(public['rows'][0]['unresolved_texture_names']),1)

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
