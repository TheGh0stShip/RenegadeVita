import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaLoadingScreenContractTests(unittest.TestCase):
    def test_direct_runtime_uses_original_campaign_backdrop_and_model_progress(self):
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        original = (ROOT / "staging/commando/combatgmode.cpp").read_text(
            encoding="utf-8", errors="replace"
        )
        loading_source = (ROOT / "staging/commando/loadingscreen.cpp").read_text(
            encoding="utf-8", errors="replace"
        )
        loading_header = (ROOT / "staging/commando/loadingscreen.h").read_text(
            encoding="utf-8", errors="replace"
        )

        self.assertIn("class LoadingScreenClass", original)
        self.assertIn("#include \"loadingscreen.h\"", original)
        self.assertIn("class LoadingScreenClass", loading_header)
        self.assertIn("MenuBackDropClass\tbackdrop;", loading_header)
        self.assertIn("backdrop.Render();", loading_source)
        self.assertIn("backdropText.Render();", loading_source)
        self.assertIn("backdropText2.Render();", loading_source)
        self.assertIn("backdrop.Set_Animation_Percentage( LoadPercentageDrawn );", loading_source)
        self.assertLess(
            loading_source.index("backdrop.Set_Animation_Percentage( LoadPercentageDrawn );"),
            loading_source.index("backdrop.Render();"),
        )
        self.assertIn("loading_screen.Render(true);", original)
        self.assertIn("Commando_Create_Original_Loading_Screen", loading_source)
        self.assertIn("Commando_Render_Original_Loading_Screen", loading_source)
        self.assertIn("Commando_Destroy_Original_Loading_Screen", loading_source)
        self.assertIn("Commando_Original_Loading_Screen_Has_Backdrop_Model", loading_source)
        self.assertIn("#include \"a31_console_stub.h\"", loading_source)
        self.assertIn("update_network ? &cNetwork::Update : NULL", loading_source)
        self.assertIn("CombatManager::Set_Load_Progress(0);", original)
        self.assertIn("last_count = CombatManager::Get_Load_Progress();", loading_source)
        self.assertIn("SaveLoadStatus::Reset_Status_Count();", loading_source)
        self.assertIn("case 6:\treturn 17.6f / TOTAL;", loading_source)

        self.assertIn('#include "campaign.h"', runtime)
        self.assertIn('#include "menubackdrop.h"', runtime)
        self.assertIn('#include "render2d.h"', runtime)
        self.assertIn('#include "render2dsentence.h"', runtime)
        self.assertIn('#include "stylemgr.h"', runtime)
        self.assertIn('#include "translatedb.h"', runtime)
        self.assertIn("Load_Strings_Database_For_Loading_Screen()", runtime)
        self.assertIn('StyleMgrClass::Initialize_From_INI(kStyleManagerIni)', runtime)
        self.assertIn("kCncMultiplayerLoadBackdropNumber = 94", runtime)
        self.assertIn("kOriginalLoadingLogicalWidth = 640.0f", runtime)
        self.assertIn("kOriginalLoadingLogicalHeight = 480.0f", runtime)
        self.assertIn("class A31VitaScopedLoadingRenderResolution", runtime)
        self.assertIn("WW3D::Get_Device_Resolution(PreviousWidth, PreviousHeight", runtime)
        self.assertIn("WW3D::Set_Device_Resolution(", runtime)
        self.assertIn("static_cast<int>(kOriginalLoadingLogicalWidth)", runtime)
        self.assertIn("static_cast<int>(kOriginalLoadingLogicalHeight)", runtime)
        self.assertIn("A31VitaScopedLoadingRenderResolution loading_render_resolution;", runtime)
        self.assertIn("extern void *Commando_Create_Original_Loading_Screen(void);", runtime)
        self.assertIn("extern void Commando_Render_Original_Loading_Screen(void *screen, bool update_network);", runtime)
        self.assertIn("extern void Commando_Destroy_Original_Loading_Screen(void *screen);", runtime)
        self.assertIn("CampaignManager::Init();", runtime)
        self.assertIn("CampaignManager::Select_Backdrop_Number(kCncMultiplayerLoadBackdropNumber)", runtime)
        self.assertIn("CampaignManager::Get_Backdrop_Description_Count()", runtime)
        self.assertIn("CampaignManager::Get_Backdrop_Description(index)", runtime)
        self.assertIn("Screen = Commando_Create_Original_Loading_Screen();", runtime)
        self.assertIn("Commando_Original_Loading_Screen_Has_Backdrop_Model(Screen)", runtime)
        self.assertIn("Commando_Render_Original_Loading_Screen(Screen, update_network);", runtime)
        self.assertIn("Commando_Destroy_Original_Loading_Screen(Screen);", runtime)
        self.assertNotIn("BackdropText.Set_Texture_Size_Hint(256)", runtime)
        self.assertNotIn("BackdropText2.Set_Texture_Size_Hint(256)", runtime)
        self.assertNotIn("BackdropText.Render();", runtime)
        self.assertNotIn("BackdropText2.Render();", runtime)
        self.assertNotIn("Backdrop.Set_Model(selected_model);", runtime)
        self.assertNotIn("Backdrop.Set_Animation(anim_name);", runtime)
        self.assertNotIn("Backdrop.Render();", runtime)
        self.assertNotIn("Backdrop.Set_Animation_Percentage(LoadPercentageDrawn);", runtime)
        self.assertIn("CombatManager::Set_Load_Progress(0);", runtime)
        self.assertIn("void Render_Original_Progress(const char *phase, bool update_network = true)", runtime)
        self.assertIn('loading_presenter.Render_Original_Progress("post_load_processing");', runtime)
        self.assertIn('loading_presenter.Render_Original_Progress("post_load_level");', runtime)
        self.assertIn('loading_presenter.Render_Original_Progress("level_ready");', runtime)
        self.assertIn("Make_Loading_Capture_State", runtime)
        self.assertIn('"original-loading-screen"', runtime)
        self.assertIn('"level-ready"', runtime)
        self.assertIn('"original-loading-screen-level-ready-t%llu"', runtime)
        self.assertIn("state.loading_visual_gate.active = true;", runtime)
        self.assertIn("state.loading_visual_gate.original_logical_width", runtime)
        self.assertIn("state.loading_visual_gate.original_logical_height", runtime)
        self.assertIn("state.loading_visual_gate.native_display_width = RenegadeVitaRenderer::DISPLAY_WIDTH;", runtime)
        self.assertIn("state.loading_visual_gate.native_display_height = RenegadeVitaRenderer::DISPLAY_HEIGHT;", runtime)
        self.assertIn("state.loading_visual_gate.logical_to_native_fullscreen", runtime)
        self.assertIn("state.loading_visual_gate.original_loading_screen_owner = true;", runtime)
        self.assertIn("state.loading_visual_gate.direct_vitagl_overlay_disabled = true;", runtime)
        self.assertIn("state.loading_visual_gate.loading_texture_v_flip_enabled = true;", runtime)
        self.assertIn("state.loading_visual_gate.gameplay_texture_v_unchanged = true;", runtime)
        self.assertNotIn("A31FrameHistory capture_history;", runtime)
        self.assertNotIn("A31FrameHistory loading_capture_history;", runtime)
        self.assertIn("new (std::nothrow) A31FrameHistory", runtime)
        self.assertIn("delete capture_history;", runtime)
        self.assertIn("capture_history->Reset();", runtime)
        self.assertIn("RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(capture_pixels, kCaptureBytes)", runtime)
        self.assertIn("Capture: %s candidate=%s phase=original-loading-screen reason=level-ready", runtime)
        self.assertLess(
            runtime.index('loading_presenter.Render_Original_Progress("level_ready");'),
            runtime.index("phase=original-loading-screen reason=level-ready"),
        )
        self.assertLess(
            runtime.index("phase=original-loading-screen reason=level-ready"),
            runtime.index("A31_Interactive_Apply_Render_Capabilities();"),
        )
        self.assertNotIn("Present_Fraction", runtime)
        self.assertNotIn("0.985f", runtime)
        self.assertNotIn("0.995f", runtime)
        self.assertIn("direct_vitagl_tiles=0", runtime)
        self.assertIn("progress_owner=original_LoadingScreenClass", runtime)
        self.assertLess(
            runtime.index("A31VitaScopedLoadingRenderResolution loading_render_resolution;"),
            runtime.index("A31VitaLoadingPresenter loading_presenter;"),
        )
        self.assertIn("StyleMgrClass::Shutdown();", runtime)
        self.assertIn("TranslateDBClass::Shutdown();", runtime)
        self.assertIn("CampaignManager::Shutdown();", runtime)
        self.assertLess(
            runtime.index("CampaignManager::Shutdown();"),
            runtime.index("CombatManager::Shutdown();"),
        )
        self.assertLess(
            runtime.index("CombatManager::Shutdown();"),
            runtime.index("StyleMgrClass::Shutdown();"),
        )

        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )
        renderer_h = (ROOT / "port/renderer/vita/ww3d_vita_renderer.h").read_text(
            encoding="utf-8"
        )
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("bool DX8Wrapper::Set_Device_Resolution", boundary)
        self.assertIn("Render2DClass::Set_Screen_Resolution(RectClass(0, 0,", boundary)
        self.assertIn("g_logical_viewport_width", boundary)
        self.assertIn("g_logical_viewport_height", boundary)
        self.assertIn("logical_width", renderer)
        self.assertIn("logical_height", renderer)
        self.assertNotIn("bool flip_texture_v;", renderer_h)
        self.assertIn("const char *texture_names[2];", renderer_h)
        self.assertIn('prefix[] = "loadscreen_"', renderer)
        self.assertIn("Has_Loadscreen_Texture_Prefix(texture_name)", renderer)
        self.assertIn("source_t = 1.0f - source_t;", renderer)
        self.assertIn("submission.texture_names[stage]", boundary)
        self.assertIn("submission.texture_names[0]", renderer)
        self.assertIn("submission.texture_names[1]", renderer)
        self.assertNotIn("1.0f - uvs[vertex_index].Y", renderer)
        self.assertNotIn("submission.flip_texture_v ? 1.0f - uv[1] : uv[1]", renderer)
        self.assertNotIn("submission.flip_texture_v =", boundary)
        self.assertIn("targa.Header.ImageDescriptor ^= TGAIDF_YORIGIN;", boundary)
        self.assertLess(
            boundary.index("targa.Header.ImageDescriptor ^= TGAIDF_YORIGIN;"),
            boundary.index("targa.Load(filename, TGAF_IMAGE, false)"),
        )
        self.assertNotIn("targa.Close();\n\tif (targa.Load(filename, TGAF_IMAGE, false)", boundary)
        self.assertIn("Filename_Has_Extension", boundary)
        self.assertIn('Filename_Has_Extension(filename, ".tga")', boundary)
        self.assertIn("Load_DDS_Texture(filename, mip_level_count,", boundary)
        self.assertIn("return Load_Targa_Texture(filename, mip_level_count);", boundary)
        self.assertIn("IDirect3DSurface8 *surface = DX8Wrapper::_Create_DX8_Surface(filename);", boundary)
        self.assertIn("IDirect3DTexture8 *texture = DX8Wrapper::_Create_DX8_Texture(surface,", boundary)
        self.assertIn("if (texture != NULL || dds_available) return texture;", boundary)
        self.assertIn("texture->SourceFormat = WW3DFormat_To_D3DFormat(dds.Get_Format());", boundary)
        self.assertNotIn("texture->SourceFormat = static_cast<uint32_t>(dds.Get_Format());", boundary)
        self.assertLess(
            boundary.index("Load_DDS_Texture(filename, mip_level_count,"),
            boundary.index('Filename_Has_Extension(filename, ".tga")'),
        )
        self.assertIn("RenegadeVitaRenderer::Record_Texture_Decode();", boundary)
        capture_header = (ROOT / "port/developer/a31_capture_telemetry.h").read_text(
            encoding="utf-8"
        )
        capture_source = (ROOT / "port/developer/a31_capture_telemetry.cpp").read_text(
            encoding="utf-8"
        )
        compare_source = (ROOT / "tools/compare_capture_bundles.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("A31_CAPTURE_SCHEMA_VERSION = 4U", capture_header)
        self.assertIn("A31LoadingVisualGateTelemetry", capture_header)
        self.assertIn("loading_visual_gate", capture_source)
        self.assertIn("Loading visual gate: active=%d logical=%ux%u", capture_source)
        self.assertIn('"loading_visual_gate.logical_to_native_fullscreen"', compare_source)

        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn('MATCHES "VGL_MEM_PHYCONT[ \\t\\r\\n]*,"', cmake)
        self.assertIn('MATCHES "VGL_MEM_SLOW[ \\t\\r\\n]*,"', cmake)
        self.assertNotIn('MATCHES "VGL_MEM_PHYCONT"', cmake)
        self.assertNotIn('MATCHES "VGL_MEM_SLOW"', cmake)

    def test_direct_runtime_rejects_the_failed_tile_overlay_path(self):
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        renderer_h = (ROOT / "port/renderer/vita/ww3d_vita_renderer.h").read_text(
            encoding="utf-8"
        )
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text(
            encoding="utf-8"
        )

        forbidden = [
            "kMultiplayerCncLoadTextures",
            "BackdropTextures",
            "Draw_Loading_Backdrop",
            "Draw_Loading_Progress_Bar",
            "Draw_Loading_Tile",
            "Draw_Textured_Screen_Rect",
            "native_tiled textures=loadscreen_cnc_1..4.dds",
        ]
        for needle in forbidden:
            self.assertNotIn(needle, runtime)
            self.assertNotIn(needle, renderer_h)
            self.assertNotIn(needle, renderer)

    def test_vita_source_closure_contains_original_loading_owners(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        original_sources = (ROOT / "cmake/A31OriginalSources.cmake").read_text(
            encoding="utf-8"
        )

        self.assertIn("${RENEGADE_STAGE}/commando/loadingscreen.cpp", cmake)
        self.assertIn("${RENEGADE_STAGE}/commando/campaign.cpp", cmake)
        self.assertIn("${RENEGADE_STAGE}/wwui/menubackdrop.cpp", cmake)
        self.assertIn("${RENEGADE_STAGE}/wwui/stylemgr.cpp", cmake)
        self.assertIn("${RENEGADE_STAGE}/ww3d2/render2d.cpp", original_sources)
        self.assertIn("${RENEGADE_STAGE}/ww3d2/render2dsentence.cpp", original_sources)

    def test_host_loading_backdrop_probe_uses_original_asset_owner(self):
        host_cmake = (ROOT / "tools/host_a30_definitions/CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        probe = (
            ROOT / "tools/host_a30_definitions/loading_backdrop_contract_main.cpp"
        ).read_text(encoding="utf-8")

        self.assertIn("a35_loading_backdrop_contract", host_cmake)
        self.assertIn("${RENEGADE_A22_ORIGINAL_SOURCES}", host_cmake)
        self.assertIn("if_lvl94load.w3d", probe)
        for texture in (
            "loadscreen_cnc_1.tga",
            "loadscreen_cnc_2.tga",
            "loadscreen_cnc_3.tga",
            "loadscreen_cnc_4.tga",
        ):
            self.assertIn(texture, probe)
        self.assertIn("WW3DAssetManager asset_manager", probe)
        self.assertIn("asset_manager.Load_3D_Assets(*file)", probe)
        self.assertIn("model->Peek_Texture(polygon, 0, 0)", probe)
        self.assertIn("Has_Full_Tile_UV_Span", probe)
        self.assertIn("\"required loadscreen texture has full-tile UV coverage\"", probe)

    def test_fast_build_symbol_gate_tracks_original_loading_owner(self):
        fast_build = (ROOT / "tools/build_fast_candidate.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("MenuBackDropClass::Render()", fast_build)
        self.assertIn("CampaignManager::Select_Backdrop_Number(int)", fast_build)
        self.assertNotIn("RenegadeVitaRenderer::Draw_Loading_Progress_Bar(float)", fast_build)


if __name__ == "__main__":
    unittest.main()
