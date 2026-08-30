import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaSkinSubmissionContractTests(unittest.TestCase):
    def test_vita_boundary_preserves_original_skin_deformation_and_transform(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text(
            encoding="utf-8"
        )
        original = (ROOT / "staging/ww3d2/dx8renderer.cpp").read_text(
            encoding="utf-8", errors="replace"
        )
        self.assertIn(
            "mesh.Get_Deformed_Vertices(g_deformed_skin_vertices,\n"
            "\t\t\tg_deformed_skin_normals);",
            renderer,
        )
        self.assertIn("if (is_skin) original_world_transform.Make_Identity();", renderer)
        self.assertIn("vertices = g_deformed_skin_vertices;", renderer)
        self.assertLess(
            renderer.index("mesh.Get_Deformed_Vertices"),
            renderer.index("glVertex3f(vertices[vertex_index].X"),
        )
        self.assertIn("mesh->Get_Deformed_Vertices(loc,norm);", original)
        self.assertIn("Set world identity (for skin)", original)

    def test_vita_boundary_uses_original_material_color_with_textured_skin_passthrough(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("const unsigned *diffuse_colors = model->Get_DCG_Array(pass);", renderer)
        self.assertIn("model->Peek_Material(static_cast<int>(vertex_index), pass)", renderer)
        self.assertIn("Evaluate_Original_Material_Vertex_Color(material, color1,", renderer)
        self.assertIn("material->Get_Diffuse(&material_diffuse);", renderer)
        self.assertIn("glColor4f(Clamp01(final_color.X)", renderer)
        self.assertIn("is_skin ? NULL : mesh.Get_User_Lighting_Array(false);", renderer)
        self.assertIn(
            "if (is_skin && bound_textures[0] != NULL &&\n"
            "\t\t\t\t\ttriangle_shader.Get_Texturing() == ShaderClass::TEXTURING_ENABLE)",
            renderer,
        )
        self.assertIn("first textured skin color pass-through", renderer)
        self.assertIn("final_color = Vector3(1.0f, 1.0f, 1.0f);", renderer)
        self.assertNotIn("0.35f + 0.35f * (normal.X + 1.0f)", renderer)

    def test_skinned_gameplay_atlas_uvs_are_not_v_flipped(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Should_Flip_Submitted_Texture_V", renderer)
        self.assertNotIn("first loading texture V correction", renderer)
        self.assertNotIn("t = 1.0f - t;", renderer)
        self.assertIn("first skinned gameplay passthrough texture V preserved", renderer)
        self.assertIn("g_logged_first_skin_passthrough_texture_v_preserved", renderer)


if __name__ == "__main__":
    unittest.main()
