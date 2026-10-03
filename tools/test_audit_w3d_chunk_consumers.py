import unittest
from tools.audit_w3d_chunk_consumers import chunk_enum, references, reconcile, local_owner


class W3dConsumerTest(unittest.TestCase):
    def test_local_ids_require_exact_primitive_parent(self):
        self.assertEqual(local_owner(['0x741','0x1'])[1],'CHUNKID_SPHERE_DEF')
        self.assertEqual(local_owner(['0x742','0x4'])[1],'CHUNKID_INNER_SCALE_CHANNEL')
        self.assertEqual(local_owner(['0x741','0x2','0x03150809'])[1],'CHUNKID_VARIABLES')
        self.assertIsNone(local_owner(['0x0','0x1']))
        self.assertIsNone(local_owner(['0x741','0x1','0x03150809']))
    def test_implicit_values_and_comment_literal_masking(self):
        code='enum { W3D_CHUNK_MESH=0x0, W3D_CHUNK_NEXT, OBSOLETE_W3D_CHUNK_LAST=9 };'
        names=chunk_enum(code)
        self.assertEqual(names['W3D_CHUNK_NEXT'],1)
        refs=references('// case W3D_CHUNK_NEXT:\n"W3D_CHUNK_NEXT";\ncase W3D_CHUNK_NEXT: return W3D_CHUNK_MESH;',names)
        self.assertEqual([r['reference_kind'] for r in refs],['case_label','symbol_reference'])
        self.assertEqual(refs[0]['line'],3)
        with self.assertRaises(ValueError):
            chunk_enum('enum { W3D_CHUNK_MESH=BASE+1 };')

    def test_unmapped_ids_and_parent_paths_are_retained(self):
        paths=[{'chunk_path':['0x00000000','0x00000001'],'count':2,'first_member':'a.w3d',
                'first_index_record':0,'first_offset':8},
               {'chunk_path':['0x00000009'],'count':1,'first_member':'b.w3d',
                'first_index_record':1,'first_offset':0}]
        rows=reconcile({'archives':[{'archive':'M11.mix','chunk_paths':paths}]},
                       {'W3D_CHUNK_NEXT':1},[])
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['retail_paths'][0]['chunk_path'],paths[0]['chunk_path'])
        self.assertEqual(rows[1]['names'],[])
        self.assertTrue(all(r['status']=='unknown' for r in rows))
