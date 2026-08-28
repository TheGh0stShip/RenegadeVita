import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaTextureProvenanceContractTests(unittest.TestCase):
    def test_renderer_statistics_expose_source_and_fallback_bind_counts(self):
        header = (ROOT / "port/renderer/vita/ww3d_vita_renderer.h").read_text(
            encoding="utf-8"
        )
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text(
            encoding="utf-8"
        )

        for needle in (
            "uint64_t texture_dds_loads;",
            "uint64_t texture_tga_loads;",
            "uint64_t texture_checkerboard_binds;",
            "void Record_Texture_DDS_Load();",
            "void Record_Texture_Targa_Load();",
            "void Record_Texture_Checkerboard_Bind();",
        ):
            self.assertIn(needle, header)

        for needle in (
            "++g_statistics.texture_dds_loads;",
            "++g_statistics.texture_tga_loads;",
            "++g_statistics.texture_checkerboard_binds;",
        ):
            self.assertIn(needle, renderer)

    def test_dx8_boundary_logs_successful_original_texture_sources(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )

        self.assertIn("void Log_Texture_Load(const char *source, const char *filename,", boundary)
        self.assertIn("texture loaded: source=%s name=%s size=%ux%u", boundary)
        self.assertIn("bytes=%llu checksum=%08X alpha=%u fallback=%u native=%u", boundary)
        self.assertIn("if (logged_count >= 24U || texture == NULL) return;", boundary)

        dds_function = boundary[boundary.index("IDirect3DTexture8 *Load_DDS_Texture"):]
        dds_success = dds_function[
            dds_function.index("texture->PixelChecksum = checksum;"):
            dds_function.index("return texture;")
        ]
        self.assertIn("RenegadeVitaRenderer::Record_Texture_DDS_Load();", dds_success)
        self.assertIn('Log_Texture_Load("dds", filename, texture);', dds_success)
        self.assertLess(
            dds_success.index("RenegadeVitaRenderer::Record_Texture_DDS_Load();"),
            dds_success.index('Log_Texture_Load("dds", filename, texture);'),
        )

        tga_function = boundary[boundary.index("IDirect3DTexture8 *Load_Targa_Texture"):]
        tga_success = tga_function[
            :tga_function.index("void Submit_Bound_Triangles")
        ]
        self.assertIn("if (texture != NULL && !texture->DiagnosticFallback)", tga_success)
        self.assertIn("RenegadeVitaRenderer::Record_Texture_Targa_Load();", tga_success)
        self.assertIn('Log_Texture_Load("tga", filename, texture);', tga_success)

    def test_checkerboard_binds_are_separate_from_invalid_binds(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )
        set_texture = boundary[boundary.index("HRESULT IDirect3DDevice8::SetTexture"):]
        set_texture = set_texture[:set_texture.index("void DX8Wrapper::Get_DX8_Texture_Stage_State_Value_Name")]

        self.assertIn("if (texture->DiagnosticFallback)", set_texture)
        self.assertIn("RenegadeVitaRenderer::Record_Texture_Checkerboard_Bind();", set_texture)
        self.assertIn(
            "RenegadeVitaRenderer::Bind_Texture_Stage(stage, texture->NativeTexture,",
            set_texture,
        )
        self.assertLess(
            set_texture.index("RenegadeVitaRenderer::Record_Texture_Checkerboard_Bind();"),
            set_texture.index(
                "RenegadeVitaRenderer::Bind_Texture_Stage(stage, texture->NativeTexture,"
            ),
        )

    def test_runtime_and_capture_carry_texture_provenance(self):
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        capture_header = (ROOT / "port/developer/a31_capture_telemetry.h").read_text(
            encoding="utf-8"
        )
        capture_source = (ROOT / "port/developer/a31_capture_telemetry.cpp").read_text(
            encoding="utf-8"
        )

        for needle in (
            "telemetry.texture_dds_loads = statistics.texture_dds_loads;",
            "telemetry.texture_tga_loads = statistics.texture_tga_loads;",
            "telemetry.texture_checkerboard_binds = statistics.texture_checkerboard_binds;",
            "loaded_dds/tga=%llu/%llu",
            "checker/checker_bind/invalid_bind=%llu/%llu/%llu",
        ):
            self.assertIn(needle, runtime)

        for needle in (
            "uint64_t texture_dds_loads;",
            "uint64_t texture_tga_loads;",
            "uint64_t texture_checkerboard_binds;",
        ):
            self.assertIn(needle, capture_header)

        for needle in (
            '\\"texture_dds_loads\\":%llu',
            '\\"texture_tga_loads\\":%llu',
            '\\"texture_checkerboard_binds\\":%llu',
            "r.texture_dds_loads",
            "r.texture_tga_loads",
            "r.texture_checkerboard_binds",
        ):
            self.assertIn(needle, capture_source)


if __name__ == "__main__":
    unittest.main()
