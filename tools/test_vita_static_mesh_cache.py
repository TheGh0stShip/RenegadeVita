"""Execute the GPU-resident static mesh cache data model and pin its wiring."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp'


class StaticMeshCacheTests(unittest.TestCase):
    def test_cache_data_model(self):
        flags = ['-O2']
        if os.environ.get('RENEGADE_MESH_SANITIZE', '1') == '1':
            flags = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        with tempfile.TemporaryDirectory(prefix='renegade-static-mesh-cache-') as folder:
            binary = Path(folder) / 'test'
            subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror',
                            '-I' + str(ROOT / 'port/renderer/vita'),
                            str(ROOT / 'tools/vita_static_mesh_cache_test.cpp'),
                            '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_rigid_meshes_only_and_skin_keeps_immediate_path(self):
        source = RENDERER.read_text()
        submit = source[source.index('void Submit_Mesh(MeshClass &mesh'):
                        source.index('IndexedSubmissionResult Submit_Indexed_Triangles')]
        self.assertIn('if (!is_skin && Submit_Static_Mesh_Cache(', submit)
        # The per-frame path remains the fallback for every ineligible mesh.
        self.assertIn('\t} else\n#endif\n\tfor (int pass = 0; pass < base_pass_count;', submit)

    def test_eligibility_excludes_frame_dependent_inputs(self):
        source = RENDERER.read_text()
        build = source[source.index('bool Build_Static_Mesh_Streams('):
                       source.index('bool Static_Mesh_Entry_Current(')]
        self.assertIn('if (color.lighting) return false;', build)
        self.assertIn('Static_Mesh_Passthrough_Stage(coordinates[0])', build)
        self.assertIn('Static_Mesh_Passthrough_Stage(coordinates[1])', build)
        self.assertIn('snapshot.mapper[0] != NULL', build)
        self.assertIn('if (current_detail_stage && bound_textures[0] == NULL) return false;', build)
        current = source[source.index('bool Static_Mesh_Entry_Current('):
                         source.index('bool Upload_Static_Mesh_Entry(')]
        self.assertIn('Is_Alternate_Material_Description_Enabled()', current)
        self.assertIn('Static_Mesh_Snapshot_Equal', current)

    def test_lifetime_follows_original_registration(self):
        boundary = (ROOT / 'port/renderer/vita/ww3d_dx8_boundary.cpp').read_text()
        invalidate = boundary[boundary.index('void DX8MeshRendererClass::Invalidate()'):]
        invalidate = invalidate[:invalidate.index('\n}\n')]
        self.assertIn('RenegadeVitaRenderer::Invalidate_Static_Mesh_Cache();', invalidate)
        model = (ROOT / 'staging/ww3d2/meshmdl.cpp').read_text(errors='replace')
        reset = model[model.index('void MeshModelClass::Reset('):]
        self.assertIn('RenegadeVitaRenderer::Forget_Static_Mesh_Model(this);',
                      reset[:reset.index('Reset_Geometry(')])
        mesh = (ROOT / 'staging/ww3d2/mesh.cpp').read_text(errors='replace')
        self.assertEqual(mesh.count('RenegadeVitaRenderer::Forget_Static_Mesh_User_Lighting('), 3)
        free = mesh[mesh.index('void MeshClass::Free(void)'):]
        self.assertLess(free.index('Forget_Static_Mesh_User_Lighting'),
                        free.index('REF_PTR_RELEASE(Model);'))

    def test_array_and_immediate_layout_transitions_repatch(self):
        source = RENDERER.read_text()
        replay = source[source.index('void Replay_Static_Mesh_Entry('):
                        source.index('bool Submit_Static_Mesh_Cache(')]
        self.assertEqual(replay.count('vglRenegadeInvalidateVertexAttributes();'), 2)
        self.assertTrue(replay.lstrip('void Replay_Static_Mesh_Entry(const StaticMeshEntry &entry)\n{')
                        .split('glBindBuffer', 1)[0].count('vglRenegadeInvalidateVertexAttributes();') == 1)
        patch = (ROOT / 'port/renderer/vita/dependency-patches/'
                 'vitagl-attribute-invalidation.patch').read_text()
        self.assertIn('ffp_dirty_vert_attr = 0xFFFF;', patch)
        script = (ROOT / 'tools/build_vitagl_demo.sh').read_text()
        self.assertIn('-p1 < "$attribute_patch"', script)
        # Storage is allocated without data and filled only after mapping succeeds.
        upload = source[source.index('bool Upload_Static_Mesh_Entry('):
                        source.index('void Replay_Static_Mesh_Entry(')]
        self.assertNotIn('vertex_bytes), builder.Vertices().Data()', upload)
        self.assertIn('glBufferData(GL_ARRAY_BUFFER, static_cast<GLsizei>(vertex_bytes), NULL,', upload)
        self.assertIn('if (vertex_storage == NULL || index_storage == NULL)', upload)


if __name__ == '__main__':
    unittest.main()
