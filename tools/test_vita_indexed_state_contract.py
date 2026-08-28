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

    def test_original_dx8_render_state_bridge_restores_fog(self):
        header = (ROOT / "port/renderer/vita/ww3d_vita_renderer.h").read_text()
        contract = (ROOT / "port/renderer/vita/ww3d_vita_render_state_contract.h").read_text()
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        dx8_boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text()
        gameplay = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text()
        original_shader = (ROOT / "staging/ww3d2/shader.cpp").read_text(errors="replace")
        original_wrapper = (ROOT / "staging/ww3d2/Dx8Wrapper.h").read_text(errors="replace")
        host = (ROOT / "tools/host_a30_definitions/vita_render_state_contract_main.cpp").read_text()

        for needle in (
            "DX8Wrapper::Get_Current_Caps()->Is_Fog_Allowed()",
            "DX8Wrapper::Get_Fog_Enable()",
            "D3DRS_FOGENABLE,fm",
            "D3DRS_FOGCOLOR,fogColor",
        ):
            self.assertIn(needle, original_shader)
        for needle in (
            "Set_DX8_Render_State(D3DRS_FOGSTART",
            "Set_DX8_Render_State(D3DRS_FOGEND",
        ):
            self.assertIn(needle, original_wrapper)

        self.assertIn("bool Apply_DX8_Render_State(uint32_t state, uint32_t value);", header)
        for needle in (
            "struct FogStateContract",
            "Default_Fog_State()",
            "Decode_DX8_Float_Render_State",
            "Update_Fog_State_From_DX8_Render_State",
            "case D3DRS_FOGENABLE:",
            "case D3DRS_FOGCOLOR:",
            "case D3DRS_FOGSTART:",
            "case D3DRS_FOGEND:",
            "D3D_Color_Red_Unit",
            "D3D_Color_Green_Unit",
            "D3D_Color_Blue_Unit",
            "Update_Ambient_State_From_DX8_Render_State",
        ):
            self.assertIn(needle, contract)

        for needle in (
            "bool Apply_DX8_Render_State(uint32_t state, uint32_t value)",
            "Update_Fog_State_From_DX8_Render_State(state, value, g_fog_state)",
            "Update_Ambient_State_From_DX8_Render_State(state, value,",
            "glFogi(GL_FOG_MODE, GL_LINEAR);",
            "glFogf(GL_FOG_START, g_fog_state.start);",
            "glFogf(GL_FOG_END, g_fog_state.end);",
            "glFogfv(GL_FOG_COLOR, color);",
            "glEnable(GL_FOG);",
            "glDisable(GL_FOG);",
            "glLightModelfv(GL_LIGHT_MODEL_AMBIENT, color);",
            "Apply_Original_Fog_State(shader);",
            "first original DX8 fog state",
            "first original DX8 ambient state",
        ):
            self.assertIn(needle, renderer)
        self.assertIn("IsFogAllowed(true)", dx8_boundary)
        self.assertIn("HRESULT IDirect3DDevice8::SetRenderState", dx8_boundary)
        self.assertIn("RenegadeVitaRenderer::Apply_DX8_Render_State(", dx8_boundary)
        self.assertIn('"fog start state"', host)
        self.assertIn('"fog end state"', host)
        self.assertIn('"ambient color state"', host)
        self.assertNotIn("HRESULT IDirect3DDevice8::SetRenderState(D3DRENDERSTATETYPE, DWORD)\n{\n\treturn D3D_OK;\n}", gameplay)

    def test_vita_scene_restores_original_fog_fill_and_ambient_state(self):
        scene = (ROOT / "staging/ww3d2/scene.cpp").read_text(errors="replace")
        ww3d = (ROOT / "staging/ww3d2/ww3d.cpp").read_text(errors="replace")
        stage = (ROOT / "tools/stage_sources.sh").read_text()

        vita_scene = scene[
            scene.index("#if defined(RENEGADE_VITA_PORT)"):
            scene.index("#else", scene.index("#if defined(RENEGADE_VITA_PORT)"))
        ]
        self.assertIn("DX8Wrapper::Set_Fog(FogEnabled, FogColor, FogStart, FogEnd);", vita_scene)
        self.assertLess(
            vita_scene.index("DX8Wrapper::Set_Fog"),
            vita_scene.index("Customized_Render(rinfo);")
        )

        render_start = ww3d.index("WW3DErrorType WW3D::Render(SceneClass * scene")
        render_end = ww3d.index(
            "* WW3D::Render -- Render a single render object", render_start)
        render = ww3d[render_start:render_end]
        self.assertIn("switch(scene->Get_Polygon_Mode())", render)
        self.assertIn("D3DRS_FILLMODE,D3DFILL_POINT", render)
        self.assertIn("D3DRS_FILLMODE,D3DFILL_WIREFRAME", render)
        self.assertIn("D3DRS_FILLMODE,D3DFILL_SOLID", render)
        self.assertIn("Vector3 ambient = scene->Get_Ambient_Light();", render)
        self.assertIn("D3DRS_AMBIENT, DX8Wrapper::Convert_Color(ambient,0.0f)", render)
        self.assertIn("#if !defined(RENEGADE_VITA_PORT)\n\tTheDX8MeshRenderer.Set_Camera", render)
        self.assertNotIn("scene->Render(rinfo);\n\tFlush(rinfo);\n\treturn WW3D_ERROR_OK;\n#else", render)
        self.assertIn("ww3d2-a35-vita-scene-state.patch", stage)

    def test_direct_mesh_no_longer_fabricates_static_material_color_fallback(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        original = (ROOT / "staging/ww3d2/dx8renderer.cpp").read_text(
            encoding="utf-8", errors="replace"
        )
        function = renderer[
            renderer.index("void Submit_Mesh(MeshClass &mesh"):
            renderer.index("IndexedSubmissionResult Submit_Indexed_Triangles")
        ]

        self.assertNotIn("first static material black fallback", renderer)
        self.assertNotIn("Log_Static_Material_Fallback", renderer)
        self.assertNotIn("Is_Near_Black(final_color)", function)
        self.assertNotIn("fallback = Vector3(1.0f, 1.0f, 1.0f);", renderer)
        self.assertIn("DX8Wrapper::Set_Material(Peek_Material());", original)
        self.assertIn("DX8Wrapper::Set_Shader(Get_Shader());", original)
        self.assertIn("material->Get_Ambient(&material_ambient);", renderer)
        self.assertIn("material->Get_Emissive(&material_emissive);", renderer)
        self.assertIn("Vector3 final_color = vertex_color.final_color;", function)
        self.assertLess(
            function.index("Vector3 final_color = vertex_color.final_color;"),
            function.index("glColor4f(Clamp01(final_color.X)")
        )

    def test_direct_mesh_uses_original_material_lighting_sources(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        function = renderer[
            renderer.index("void Submit_Mesh(MeshClass &mesh"):
            renderer.index("IndexedSubmissionResult Submit_Indexed_Triangles")
        ]

        for needle in (
            '#include "lightenvironment.h"',
            "struct MaterialVertexColor",
            "Evaluate_Original_Material_Vertex_Color",
            "material->Get_Lighting()",
            "material->Get_Diffuse_Color_Source()",
            "material->Get_Ambient_Color_Source()",
            "material->Get_Emissive_Color_Source()",
            "Select_Material_Color_Source(diffuse_source",
            "Select_Material_Color_Source(ambient_source",
            "Select_Material_Color_Source(emissive_source",
            "light_environment->Get_Equivalent_Ambient()",
            "light_environment->Get_Light_Direction(light_index)",
            "light_environment->Get_Light_Diffuse(light_index)",
            "Compute_World_Space_Normal(world_transform,",
            "first original material lighting",
        ):
            self.assertIn(needle, renderer)

        self.assertIn("const unsigned *user_lighting =", function)
        self.assertIn("is_skin ? NULL : mesh.Get_User_Lighting_Array(false);", function)
        self.assertIn("user_lighting != NULL ? user_lighting :", function)
        self.assertIn("model->Get_Color_Array(0, false);", function)
        self.assertIn("first original user lighting color source", function)
        self.assertIn("const unsigned *color2 = model->Get_Color_Array(1, false);", function)
        self.assertIn("Evaluate_Original_Material_Vertex_Color(material, color1,", function)
        self.assertIn("render_info);", function)
        self.assertNotIn("if (diffuse_colors != NULL) {\n\t\t\t\t\tconst unsigned diffuse", function)

    def test_direct_mesh_color1_prefers_original_user_lighting_for_rigid_meshes(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        original = (ROOT / "staging/ww3d2/dx8renderer.cpp").read_text(
            encoding="utf-8", errors="replace"
        )
        function = renderer[
            renderer.index("void Submit_Mesh(MeshClass &mesh"):
            renderer.index("IndexedSubmissionResult Submit_Indexed_Triangles")
        ]
        original_split_table = original[
            original.index("class Vertex_Split_Table"):
            original.index("unsigned Get_Vertex_Count() const")
        ]

        self.assertIn("mesh->Get_User_Lighting_Array() != NULL", original_split_table)
        self.assertIn("return mesh->Get_User_Lighting_Array();", original_split_table)
        self.assertIn("return mmc->Get_Color_Array(index,false);", original_split_table)
        self.assertLess(
            function.index("mesh.Get_User_Lighting_Array(false)"),
            function.index("model->Get_Color_Array(0, false)")
        )
        self.assertIn("const unsigned *color1 =\n\t\t\tuser_lighting != NULL ? user_lighting :", function)
        self.assertIn("if (color1 == NULL && model->Get_DCG_Source(pass) == VertexMaterialClass::COLOR1)", function)
        self.assertIn("is_skin ? NULL : mesh.Get_User_Lighting_Array(false);", function)

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
        self.assertNotIn(
            "if (stage != 0U) RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);",
            boundary,
        )

    def test_texture_unsupported_stage_telemetry_excludes_supported_stage1(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text()
        recorder = renderer[
            renderer.index("void Record_Texture_Unsupported_Stage"):
            renderer.index("void Release_Texture")
        ]
        set_stage = boundary[
            boundary.index("HRESULT IDirect3DDevice8::SetTextureStageState"):
            boundary.index("HRESULT IDirect3DDevice8::SetTexture(")
        ]
        set_texture = boundary[
            boundary.index("HRESULT IDirect3DDevice8::SetTexture("):
            boundary.index("void DX8Wrapper::Get_DX8_Texture_Stage_State_Value_Name")
        ]

        self.assertIn("stage >= MeshMatDescClass::MAX_TEX_STAGES", recorder)
        self.assertIn("++g_statistics.texture_unsupported_stages;", recorder)
        self.assertNotIn("stage != 0U", recorder)
        self.assertIn("if (stage >= MAX_TEXTURE_STAGES) {", set_stage)
        self.assertIn("RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);", set_stage)
        self.assertLess(
            set_stage.index("RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);"),
            set_stage.index("return static_cast<HRESULT>(D3DERR_INVALIDCALL);"),
        )
        self.assertIn("if (stage >= MAX_TEXTURE_STAGES) {", set_texture)
        self.assertIn("RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);", set_texture)
        self.assertIn("retail stage-1 materials remain visible", set_stage)

    def test_addsmooth_uses_original_inverse_scale_combiner(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        original_header = (ROOT / "staging/ww3d2/shader.h").read_text(errors="replace")
        original_shader = (ROOT / "staging/ww3d2/shader.cpp").read_text(errors="replace")
        rgb = renderer[
            renderer.index("void Apply_GL_RGB_Texture_Op"):
            renderer.index("void Apply_GL_Alpha_Texture_Op")
        ]
        alpha = renderer[
            renderer.index("void Apply_GL_Alpha_Texture_Op"):
            renderer.index("uint32_t Original_Primary_Color_Op")
        ]

        self.assertIn("DETAILCOLOR_INVSCALE", original_header)
        self.assertIn("DETAILALPHA_INVSCALE", original_header)
        self.assertIn("local + (1-local)*other", original_header)
        self.assertIn("case ShaderClass::DETAILCOLOR_INVSCALE:", original_shader)
        self.assertIn("case ShaderClass::DETAILALPHA_INVSCALE:", original_shader)
        self.assertIn("cOp = D3DTOP_ADDSMOOTH;", original_shader)
        self.assertIn("aOp = D3DTOP_ADDSMOOTH;", original_shader)
        self.assertIn("void Set_Texture_Env_White_Constant()", renderer)
        self.assertIn("glTexEnvfv(GL_TEXTURE_ENV, GL_TEXTURE_ENV_COLOR, white);", renderer)

        self.assertIn("case D3DTOP_ADDSMOOTH:", rgb)
        self.assertIn("Set_Texture_Env_White_Constant();", rgb)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_INTERPOLATE);", rgb)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB, GL_CONSTANT);", rgb)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_RGB,", rgb)
        self.assertIn("To_GL_Texture_Argument(argument0));", rgb)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_SRC2_RGB,", rgb)
        self.assertIn("To_GL_Texture_Argument(argument1));", rgb)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND2_RGB, GL_SRC_COLOR);", rgb)
        self.assertNotIn("case D3DTOP_ADD:\n\tcase D3DTOP_ADDSMOOTH:", rgb)

        self.assertIn("case D3DTOP_ADDSMOOTH:", alpha)
        self.assertIn("Set_Texture_Env_White_Constant();", alpha)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_ALPHA, GL_INTERPOLATE);", alpha)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_ALPHA, GL_CONSTANT);", alpha)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_ALPHA,", alpha)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_SRC2_ALPHA,", alpha)
        self.assertIn("glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND2_ALPHA, GL_SRC_ALPHA);", alpha)
        self.assertNotIn("case D3DTOP_ADD:\n\tcase D3DTOP_ADDSMOOTH:", alpha)

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
