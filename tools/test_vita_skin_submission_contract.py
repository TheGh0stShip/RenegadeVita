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

    def test_vita_boundary_uses_original_material_color_not_normal_debug_tint(self):
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("const unsigned *diffuse_colors = model->Get_DCG_Array(pass);", renderer)
        self.assertIn("model->Peek_Material(static_cast<int>(vertex_index), pass)", renderer)
        self.assertIn("Evaluate_Original_Material_Vertex_Color(material, color1,", renderer)
        self.assertIn("material->Get_Diffuse(&material_diffuse);", renderer)
        self.assertIn("glColor4f(Clamp01(final_color.X)", renderer)
        self.assertIn("is_skin ? NULL : mesh.Get_User_Lighting_Array(false);", renderer)
        self.assertNotIn("0.35f + 0.35f * (normal.X + 1.0f)", renderer)


if __name__ == "__main__":
    unittest.main()
