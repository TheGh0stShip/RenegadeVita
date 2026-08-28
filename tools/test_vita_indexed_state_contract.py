import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaIndexedStateContractTests(unittest.TestCase):
    def test_deferred_sky_state_is_applied_before_indexed_geometry(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text()
        function = boundary[boundary.index("void Submit_Bound_Triangles"):]
        shader = function.index(
            "RenegadeVitaRenderer::Apply_Indexed_Shader_State(state.shader)")
        loop = function.index("for (unsigned stage = 0; stage < MAX_TEXTURE_STAGES; ++stage)")
        texture = function.index(
            "state.Textures[stage]->Apply_For_Platform_Boundary(stage)")
        fallback = function.index("RenegadeVitaRenderer::Bind_Texture(0U, false)")
        stage1_disable = function.index("RenegadeVitaRenderer::Disable_Texture_Stage(stage)")
        material = function.index("Apply_Indexed_Texture_Coordinate_State(state.material)")
        submit = function.index(
            "RenegadeVitaRenderer::Submit_Indexed_Triangles(submission)")
        self.assertLess(shader, loop)
        self.assertLess(loop, texture)
        self.assertLess(texture, submit)
        self.assertLess(fallback, submit)
        self.assertLess(stage1_disable, submit)
        self.assertLess(texture, material)
        self.assertLess(material, submit)
        self.assertIn("mapper->Apply(uv_source);", boundary)
        self.assertIn("D3DTSS_TEXCOORDINDEX", boundary)
        self.assertIn("D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_DISABLE", boundary)

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

    def test_alpha_test_uses_original_shader_reference(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        contract = (ROOT / "port/renderer/vita/ww3d_vita_render_state_contract.h").read_text()
        original = (ROOT / "staging/ww3d2/shader.cpp").read_text(errors="replace")
        host = (ROOT / "tools/host_a30_definitions/vita_render_state_contract_main.cpp").read_text()

        for needle in (
            "unsigned char alphareference = 0x60",
            "D3DRS_ALPHAREF,0xff - alphareference",
            "D3DRS_ALPHAFUNC,D3DCMP_LESSEQUAL",
            "D3DRS_ALPHAREF,alphareference",
            "D3DRS_ALPHAFUNC,D3DCMP_GREATEREQUAL",
        ):
            self.assertIn(needle, original)

        for needle in (
            "unsigned char alpha_reference;",
            "ShaderClass::DepthCompareType alpha_compare;",
            "const unsigned char reference = 0x60U;",
            "BLEND_FACTOR_ONE_MINUS_SRC_ALPHA",
            "state.alpha_compare = ShaderClass::PASS_LEQUAL;",
            "state.alpha_compare = ShaderClass::PASS_GEQUAL;",
        ):
            self.assertIn(needle, contract)

        self.assertIn("glAlphaFunc(To_GL_Depth_Function(state.alpha_compare),", renderer)
        self.assertIn("static_cast<float>(state.alpha_reference) / 255.0f", renderer)
        self.assertNotIn("glAlphaFunc(GL_GREATER, 0.0f);", renderer)
        self.assertIn('"inverse alpha cutout"', host)

    def test_textured_static_material_black_fallback_is_bounded_and_observable(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        self.assertIn("first static material black fallback", renderer)
        self.assertIn("!is_skin && bound_textures[0] != NULL && Is_Near_Black(diffuse)", renderer)
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

    def test_vita_boundary_applies_original_stage1_multitexture(self):
        header = (ROOT / "port/renderer/vita/ww3d_vita_renderer.h").read_text()
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text()

        for needle in (
            "bool Bind_Texture_Stage(uint32_t stage, uint32_t native_texture, bool valid);",
            "void Disable_Texture_Stage(uint32_t stage);",
            "bool Configure_Texture_Sampler_Stage(uint32_t stage, uint32_t native_texture,",
            "bool Apply_DX8_Texture_Stage_State(uint32_t stage, uint32_t color_op,",
        ):
            self.assertIn(needle, header)

        for needle in (
            "glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage))",
            "Emit_Original_Texture_Coordinate(1U, GL_TEXTURE1,",
            "model->Peek_Texture(triangle_index, pass, 1)",
            "model->Get_UV_Array(pass, 1)",
            "triangle_shader.Uses_Post_Detail_Texture()",
            "bound_textures[1]->Apply_For_Platform_Boundary(1U)",
            "Apply_Original_Texture_Stage_State(triangle_shader,",
            "first original MeshClass stage1 texture",
            "Apply_Original_Texture_Coordinate_State(current_material);",
        ):
            self.assertIn(needle, renderer)

        for needle in (
            "struct TextureStageCombinerState",
            "DWORD texcoord_index;",
            "DWORD texture_transform_flags;",
            "Apply_Texture_Stage_Transform(stage)",
            "state.Textures[stage]->Apply_For_Platform_Boundary(stage)",
            "RenegadeVitaRenderer::Bind_Texture_Stage(stage, texture->NativeTexture,",
            "Apply_Texture_Stage_Combiner(stage)",
            "Caps.MaxSimultaneousTextures = MAX_TEXTURE_STAGES;",
            "Caps.MaxTextureBlendStages = MAX_TEXTURE_STAGES;",
        ):
            self.assertIn(needle, boundary)

        self.assertNotIn(
            "if (stage != 0U) {\n"
            "\t\tRenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);\n"
            "\t\treturn D3D_OK;\n"
            "\t}",
            boundary,
        )

    def test_direct_mesh_submit_replays_original_material_mapper_state(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text()
        function = renderer[
            renderer.index("void Submit_Mesh(MeshClass &mesh"):
            renderer.index("IndexedSubmissionResult Submit_Indexed_Triangles")
        ]
        mapper_helper = renderer[
            renderer.index("void Apply_Original_Texture_Coordinate_State"):
            renderer.index("float Clamp01")
        ]

        self.assertIn('#include "dx8wrapper.h"', renderer)
        self.assertIn("TextureMapperClass *mapper = NULL;", mapper_helper)
        self.assertIn("mapper = material->Peek_Mapper(static_cast<int>(stage));", mapper_helper)
        self.assertIn("mapper->Apply(uv_source);", mapper_helper)
        self.assertIn("D3DTSS_TEXCOORDINDEX", mapper_helper)
        self.assertIn("D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_DISABLE", mapper_helper)
        self.assertIn("first original VertexMaterial mapper", mapper_helper)

        self.assertIn("VertexMaterialClass *current_material = NULL;", function)
        self.assertIn("const Vector2 *current_uvs[MeshMatDescClass::MAX_TEX_STAGES] = {};", function)
        self.assertIn("VertexMaterialClass *triangle_material =", function)
        self.assertIn("model->Peek_Material(static_cast<int>(group_triangle[0]), pass)", function)
        self.assertIn("triangle_material != current_material", function)
        self.assertIn("current_material = triangle_material;", function)
        self.assertIn("Resolve_UV_Array_For_Texture_State(model,", function)
        self.assertIn("model->Get_UV_Array_By_Index(uv_source);", renderer)
        self.assertIn("return fallback;", renderer)
        self.assertIn("uvs[vertex_index].X", renderer)
        self.assertIn("current_uvs[1] != NULL ? current_uvs[1] : current_uvs[0]", function)
        self.assertLess(
            function.index("current_material = triangle_material;"),
            function.index("Apply_Original_Texture_Coordinate_State(current_material);"),
        )
        self.assertIn("Apply_Original_Texture_Coordinate_State(NULL);", function)

        self.assertIn("case D3DTSS_TEXCOORDINDEX: sampler.texcoord_index = value; break;", boundary)
        self.assertIn(
            "case D3DTSS_TEXTURETRANSFORMFLAGS: sampler.texture_transform_flags = value; break;",
            boundary,
        )
        self.assertIn("glMatrixMode(GL_TEXTURE);", boundary)
        self.assertIn("glLoadMatrixf(&g_boundary_transforms[D3DTS_TEXTURE0 + stage].m[0][0]);", boundary)

    def test_direct_mesh_submit_evaluates_generated_texture_coordinates(self):
        header = (ROOT / "port/renderer/vita/d3d8.h").read_text()
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text()
        function = renderer[
            renderer.index("void Submit_Mesh(MeshClass &mesh"):
            renderer.index("IndexedSubmissionResult Submit_Indexed_Triangles")
        ]

        self.assertIn("RenegadeVita_Get_DX8_Texture_Coordinate_State", header)
        self.assertIn("RenegadeVita_Get_DX8_Texture_Coordinate_State", boundary)
        self.assertIn("*texcoord_index = sampler.texcoord_index;", boundary)
        self.assertIn(
            "*texture_transform_flags = sampler.texture_transform_flags;",
            boundary,
        )
        self.assertIn(
            "*texture_transform = g_boundary_transforms[D3DTS_TEXTURE0 + stage];",
            boundary,
        )

        for needle in (
            "struct OriginalTextureCoordinateState",
            "Capture_Original_Texture_Coordinate_State",
            "Reset_Texture_Matrix_Stage(stage);",
            "D3DTSS_TCI_CAMERASPACENORMAL",
            "D3DTSS_TCI_CAMERASPACEPOSITION",
            "D3DTSS_TCI_CAMERASPACEREFLECTIONVECTOR",
            "Compute_Camera_Space_Position",
            "Compute_Camera_Space_Normal",
            "Compute_Camera_Space_Reflection",
            "Apply_DX8_Texture_Transform",
            "glMultiTexCoord2f(texture_unit, s, t);",
            "first generated texture coordinates",
        ):
            self.assertIn(needle, renderer)

        self.assertIn(
            "current_texture_coordinates[MeshMatDescClass::MAX_TEX_STAGES]",
            function,
        )
        self.assertLess(
            function.index("Apply_Original_Texture_Coordinate_State(current_material);"),
            function.index("Capture_Original_Texture_Coordinate_State(stage,"),
        )
        self.assertLess(
            function.index("Capture_Original_Texture_Coordinate_State(stage,"),
            function.index("Apply_Original_Texture_Stage_State(triangle_shader,"),
        )
        self.assertIn(
            "Emit_Original_Texture_Coordinate(0U, GL_TEXTURE0,",
            function,
        )
        self.assertIn(
            "Emit_Original_Texture_Coordinate(1U, GL_TEXTURE1,",
            function,
        )

    def test_indexed_submit_replays_second_uv_and_generated_texcoords(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        function = renderer[
            renderer.index("IndexedSubmissionResult Submit_Indexed_Triangles"):
            renderer.index("void Reject_Indexed_Submission")
        ]

        for needle in (
            "const bool dynamic_two_uv_layout",
            "const uint32_t uv0_offset = 28U;",
            "const uint32_t uv1_offset = dynamic_two_uv_layout ? 36U : uv0_offset;",
            "memcpy(uv0, vertex + uv0_offset, 2U * sizeof(float));",
            "memcpy(uv1, vertex + uv1_offset, 2U * sizeof(float));",
            "Capture_Original_Texture_Coordinate_State(stage,",
            "Emit_Indexed_Texture_Coordinate(0U, GL_TEXTURE0,",
            "Emit_Indexed_Texture_Coordinate(1U, GL_TEXTURE1,",
        ):
            self.assertIn(needle, function)

        for needle in (
            "state.texcoord_index & 0xffffU",
            "uv_source == 1U ? uv1 : uv0",
            "Compute_Indexed_Camera_Space_Position",
            "Compute_Indexed_Camera_Space_Normal",
            "Compute_Indexed_Camera_Space_Reflection",
            "Apply_DX8_Texture_Transform(state, source_s, source_t, source_r, 1.0f,",
        ):
            self.assertIn(needle, renderer)

    def test_capture_state_uses_global_texture_statistics(self):
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        self.assertIn("void Copy_Renderer_Statistics(A31RendererTelemetry &telemetry)", runtime)
        self.assertIn("telemetry.texture_uploads = statistics.texture_uploads;", runtime)
        self.assertIn("telemetry.texture_binds = statistics.texture_binds;", runtime)
        self.assertIn("Copy_Renderer_Statistics(state.renderer);", runtime)


if __name__ == "__main__":
    unittest.main()
