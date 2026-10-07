"""Execute the deformed-skin cache data model and pin its invalidation wiring.

The cache lets a queued skin material pass reuse the base pass output of
MeshClass::Get_Deformed_Vertices. The harness proves every reuse is bitwise
identical to a fresh deformation; the source checks pin the original hooks
and input set that the invalidation argument depends on.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp'
CACHE = ROOT / 'port/renderer/vita/ww3d_vita_skin_deform_cache.h'


def _function(source, signature):
    start = source.index(signature)
    end = source.index('\n}\n', start)
    return source[start:end + 2]


class SkinDeformCacheTests(unittest.TestCase):
    def test_cache_data_model(self):
        flags = ['-O2']
        if os.environ.get('RENEGADE_MESH_SANITIZE', '1') == '1':
            flags = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        with tempfile.TemporaryDirectory(prefix='renegade-skin-deform-cache-') as folder:
            binary = Path(folder) / 'test'
            subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror',
                            '-I' + str(ROOT / 'port/renderer/vita'),
                            str(ROOT / 'tools/vita_skin_deform_cache_test.cpp'),
                            '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_deformation_inputs_are_model_arrays_and_pivot_transforms(self):
        mesh = (ROOT / 'staging/ww3d2/mesh.cpp').read_text(errors='replace')
        fetch = _function(mesh, 'void\tMeshClass::Get_Deformed_Vertices(Vector3 *dst_vert, Vector3 *dst_norm)')
        self.assertIn('Model->get_deformed_vertices(dst_vert,dst_norm,Container->Get_HTree());', fetch)
        model = (ROOT / 'staging/ww3d2/meshmdl.cpp').read_text(errors='replace')
        deform = _function(model, 'void MeshModelClass::get_deformed_vertices(Vector3 *dst_vert, '
                                  'Vector3 *dst_norm,const HTreeClass * htree)')
        self.assertIn('Vector3 * src_vert = Vertex->Get_Array();', deform)
        self.assertIn('Vector3 * src_norm = VertexNorm->Get_Array();', deform)
        # The lazily recomputing normal accessor variant is compiled out, and
        # the renderer validates dirty normals before every skin submission.
        self.assertIn('#if (OPTIMIZE_VNORMS)', deform)
        for folder in ('staging/ww3d2', 'staging/wwmath', 'port/renderer/vita'):
            for path in (ROOT / folder).glob('*.h'):
                self.assertNotIn('#define OPTIMIZE_VNORMS', path.read_text(errors='replace'), str(path))
        geometry = (ROOT / 'staging/ww3d2/meshgeometry.h').read_text(errors='replace')
        self.assertIn('#define OPTIMIZE_VNORM_RAM\t\t\t\t0', geometry)
        source = RENDERER.read_text()
        submit = source[source.index('static void Submit_Mesh_Internal(MeshClass &mesh'):]
        self.assertLess(submit.index('const Vector3 *normals = model->Get_Vertex_Normal_Array();'),
                        submit.index('Fetch_Cached_Deformed_Skin(mesh, model, render_info,'))
        self.assertIn('uint16 * bonelink = VertexBoneLink->Get_Array();', deform)
        self.assertIn('const Matrix3D & tm = htree->Get_Transform(bonelink[vi]);', deform)
        self.assertEqual(deform.count('htree->'), 1)

    def test_model_hooks_precede_every_geometry_change(self):
        model = (ROOT / 'staging/ww3d2/meshmdl.cpp').read_text(errors='replace')
        reset = _function(model, 'void MeshModelClass::Reset(')
        self.assertLess(reset.index('RenegadeVitaRenderer::Forget_Static_Mesh_Model(this);'),
                        reset.index('Reset_Geometry('))
        destructor = _function(model, 'MeshModelClass::~MeshModelClass(void)')
        self.assertIn('Reset(0,0,0);', destructor)
        assign = _function(model, 'MeshModelClass & MeshModelClass::operator = (')
        self.assertLess(assign.index('Forget_Static_Mesh_Model(this);'),
                        assign.index('MeshGeometryClass::operator = (that);'))
        unique = _function(model, 'void MeshModelClass::Make_Geometry_Unique()')
        self.assertLess(unique.index('Vita_Invalidate_Static_Cache();'),
                        unique.index('REF_PTR_SET(Vertex,unique_verts);'))
        invalidate = _function(model, 'void MeshModelClass::Vita_Invalidate_Static_Cache(void)')
        self.assertIn('RenegadeVitaRenderer::Forget_Static_Mesh_Model(this);', invalidate)
        mesh = (ROOT / 'staging/ww3d2/mesh.cpp').read_text(errors='replace')
        for signature in ('void MeshClass::Scale(float scale)',
                          'void MeshClass::Scale(float scalex, float scaley, float scalez)'):
            scale = _function(mesh, signature)
            self.assertLess(scale.index('Model->Make_Geometry_Unique();'),
                            scale.index('Model->Scale(sc);'))
        source = RENDERER.read_text()
        forget = _function(source, 'void Forget_Static_Mesh_Model(const void *model)')
        # Active on every build, not only the Vita static-mesh configuration.
        self.assertLess(forget.index('g_skin_deform_cache.Forget_Model(model);'),
                        forget.index('#if defined(__vita__)'))

    def test_renderer_reuses_only_verified_deformations(self):
        source = RENDERER.read_text()
        fetch = _function(source, 'bool Fetch_Cached_Deformed_Skin(')
        self.assertIn('if (!g_skin_deform_cache_enabled) return false;', fetch)
        self.assertIn('const HTreeClass *htree = container != NULL ? container->Get_HTree() : NULL;', fetch)
        self.assertIn('return &htree->Get_Transform(pivot);', fetch)
        # Every submission first tries a verified reuse; only submissions that
        # another one of the same mesh follows store their deformation.
        self.assertIn('if (g_skin_deform_cache.Find(&mesh, model, vertex_count,\n'
                      '\t\thtree->Num_Pivots(), transform_at, &vertices, &normals)) {\n'
                      '\t\treturn true;\n\t}', fetch)
        self.assertIn('if (!material_pass && !Skin_Material_Pass_Follows(mesh, render_info)) return false;',
                      fetch)
        self.assertLess(fetch.index('g_skin_deform_cache.Find('),
                        fetch.index('g_skin_deform_cache.Reserve('))
        self.assertLess(fetch.index('g_skin_deform_cache.Reserve('),
                        fetch.index('mesh.Get_Deformed_Vertices(deformed_vertices, deformed_normals);'))
        self.assertLess(fetch.index('mesh.Get_Deformed_Vertices(deformed_vertices, deformed_normals);'),
                        fetch.index('g_skin_deform_cache.Commit(model->Get_Vertex_Bone_Links(),'))
        submit = source[source.index('static void Submit_Mesh_Internal(MeshClass &mesh'):]
        submit = submit[:submit.index('const bool procedural_pass = material_pass != NULL;')]
        self.assertIn('if (is_skin && Fetch_Cached_Deformed_Skin(mesh, model, render_info,\n'
                      '\t\tmaterial_pass != NULL, vertex_count, vertices, normals)) {', submit)
        # Statistics are unchanged by reuse; the original scratch path remains.
        self.assertEqual(submit.count('++g_statistics.skinned_mesh_submissions;'), 2)
        self.assertIn('} else if (is_skin) {\n\t\tif (!Ensure_Deformed_Skin_Scratch(vertex_count)) {', submit)
        self.assertIn('mesh.Get_Deformed_Vertices(g_deformed_skin_vertices,\n\t\t\tg_deformed_skin_normals);',
                      submit)

    def test_store_predicate_matches_original_material_pass_queueing(self):
        mesh = (ROOT / 'staging/ww3d2/mesh.cpp').read_text(errors='replace')
        render = _function(mesh, 'void MeshClass::Render(RenderInfoClass & rinfo)')
        vita = render[render.index('#if defined(RENEGADE_VITA_PORT)'):render.index('#else')]
        self.assertLess(vita.index('RenegadeVitaRenderer::Submit_Mesh(*this, rinfo);'),
                        vita.index('TheDX8MeshRenderer.Queue_Material_Pass(matpass, this, skin, delayed)'))
        self.assertIn('if ((!Is_Translucent()) || matpass->Is_Enabled_On_Translucent_Meshes()) {', vita)
        source = RENDERER.read_text()
        follows = _function(source, 'bool Skin_Material_Pass_Follows(')
        self.assertIn('render_info.Peek_Additional_Pass(index);', follows)
        self.assertIn('(!mesh.Is_Translucent() || pass->Is_Enabled_On_Translucent_Meshes())', follows)

    def test_bounded_storage_and_runtime_switch(self):
        cache = CACHE.read_text()
        self.assertIn('MAX_ENTRIES = 32,', cache)
        self.assertIn('MAX_VERTICES = 8192,', cache)
        self.assertIn('MAX_BONES = 1024,', cache)
        self.assertIn('memcmp(stored.transform, transform_at(stored.pivot),', cache)
        self.assertNotIn('~SkinDeformCache', cache)
        source = RENDERER.read_text()
        release = _function(source, 'void Release_Deformed_Skin_Scratch()')
        self.assertIn('g_skin_deform_cache.Release();', release)
        # Off unless the campaign renderer's flag reader enables it.
        self.assertIn('bool g_skin_deform_cache_enabled = false;', source)
        mode = _function(source, 'void Read_Skin_Deform_Cache_Mode()')
        self.assertIn('g_skin_deform_cache_enabled = true;', mode)
        self.assertIn('ux0:data/renegade/user/config/skin-deform-cache-v1.flag', mode)
        self.assertIn('memcmp(value, "RVSD1 ", 6U) == 0', mode)
        init = source[source.index('bool Initialize()'):]
        self.assertIn('Read_Static_Mesh_Cache_Mode();\n\tRead_Skin_Deform_Cache_Mode();', init)
        self.assertIn('Log_Static_Mesh_Cache_Statistics();\n\t\t\tLog_Skin_Deform_Cache_Statistics();',
                      source)


if __name__ == '__main__':
    unittest.main()
