import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaIndexedStateContractTests(unittest.TestCase):
    def test_deferred_sky_state_is_applied_before_indexed_geometry(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text()
        function = boundary[boundary.index("void Submit_Bound_Triangles"):]
        shader = function.index(
            "RenegadeVitaRenderer::Apply_Indexed_Shader_State(state.shader)")
        texture = function.index(
            "state.Textures[0]->Apply_For_Platform_Boundary(0U)")
        fallback = function.index("RenegadeVitaRenderer::Bind_Texture(0U, false)")
        submit = function.index(
            "RenegadeVitaRenderer::Submit_Indexed_Triangles(submission)")
        self.assertLess(shader, texture)
        self.assertLess(texture, submit)
        self.assertLess(fallback, submit)

    def test_indexed_state_application_is_observable(self):
        header = (ROOT / "port/renderer/vita/ww3d_vita_renderer.h").read_text()
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        self.assertIn("uint64_t indexed_state_applications;", header)
        self.assertIn("++g_statistics.indexed_state_applications;", renderer)

    def test_gradient_disable_uses_texture_replace_not_black_diffuse_modulation(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        original = (ROOT / "staging/ww3d2/shader.cpp").read_text(errors="replace")
        self.assertIn("case ShaderClass::GRADIENT_DISABLE:", original)
        self.assertIn("cOp = D3DTOP_SELECTARG1;", original)
        self.assertIn("cArg1 = D3DTA_TEXTURE;", original)
        self.assertIn("case ShaderClass::GRADIENT_DISABLE:", renderer)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE);", renderer)
        self.assertLess(
            renderer.index("glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE);"),
            renderer.index("if (state.alpha_test)")
        )

    def test_textured_static_material_black_fallback_is_bounded_and_observable(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        self.assertIn("first static material black fallback", renderer)
        self.assertIn("!is_skin && bound_texture != NULL && Is_Near_Black(diffuse)", renderer)
        self.assertIn("material->Get_Ambient(&ambient);", renderer)
        self.assertIn("material->Get_Emissive(&emissive);", renderer)
        self.assertIn("fallback = Vector3(1.0f, 1.0f, 1.0f);", renderer)

    def test_direct_mesh_submit_renders_original_base_passes(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        function = renderer[
            renderer.index("void Submit_Mesh(MeshClass &mesh"):
            renderer.index("IndexedSubmissionResult Submit_Indexed_Triangles")
        ]
        self.assertIn("const int base_pass_count = pass_count > 0 ? pass_count : 1;", function)
        self.assertIn("for (int pass = 0; pass < base_pass_count; ++pass)", function)
        self.assertIn("model->Peek_Texture(triangle_index, pass, 0)", function)
        self.assertIn("model->Get_Shader(triangle_index, pass)", function)
        self.assertIn("model->Get_UV_Array(pass, 0)", function)
        self.assertIn("model->Get_DCG_Array(pass)", function)
        self.assertIn("model->Peek_Material(static_cast<int>(vertex_index), pass)", function)
        self.assertNotIn("model->Peek_Texture(triangle_index, 0, 0)", function)
        self.assertNotIn("model->Get_Shader(triangle_index, 0)", function)

    def test_capture_state_uses_global_texture_statistics(self):
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        self.assertIn("void Copy_Renderer_Statistics(A31RendererTelemetry &telemetry)", runtime)
        self.assertIn("telemetry.texture_uploads = statistics.texture_uploads;", runtime)
        self.assertIn("telemetry.texture_binds = statistics.texture_binds;", runtime)
        self.assertIn("Copy_Renderer_Statistics(state.renderer);", runtime)


if __name__ == "__main__":
    unittest.main()
