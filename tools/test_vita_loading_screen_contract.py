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
        self.assertIn("statusText.Render();", loading_source)
        self.assertLess(
            loading_source.index("backdropText2.Render();"),
            loading_source.index("statusText.Render();"),
        )
        self.assertIn("Update_Status_Text();", loading_source)
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
        self.assertIn("Build_Original_Loading_Presentation_Rect()", runtime)
        self.assertIn("Apply_Original_Loading_Presentation_Rect", runtime)
        self.assertIn("RenegadeVitaRenderer::Set_Native_Presentation_Rect(", runtime)
        self.assertIn("RenegadeVitaRenderer::Reset_Native_Presentation_Rect();", runtime)
        self.assertIn('"A3.5 loading screen: original 640x480 presentation rect reason=%s', runtime)
        self.assertIn("presentation=%u,%u %ux%u aspect_preserved=1", runtime)
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
        self.assertLess(
            runtime.index('"loading_presenter_render"'),
            runtime.index("Commando_Render_Original_Loading_Screen(Screen, update_network);"),
        )
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
        self.assertIn("void Render_Original_Progress(const char *phase, bool update_network = true,", runtime)
        self.assertIn("SaveLoadStatus::Get_Status_Count();", runtime)
        self.assertIn("CombatManager::Set_Load_Progress(mirrored_progress);", runtime)
        self.assertIn("kLoadingProgressCatchupFrames = 3U", runtime)
        self.assertIn("LastMirroredLoadProgress != mirrored_progress", runtime)
        self.assertIn("sceDisplayWaitVblankStart();", runtime)
        self.assertIn("catchup_frames=%u", runtime)
        self.assertIn("Warm_Original_M00_Presentation_Cache", runtime)
        self.assertIn("Run_Visible_Startup_Precache_Phase", runtime)
        self.assertIn("kStartupPrecacheVisibleSteps = 6U", runtime)
        self.assertIn("kStartupPrecacheMinimumVisibleUs = 1000000ULL", runtime)
        self.assertIn("kStartupPrecacheRequiredReadBytes = 32768U", runtime)
        self.assertIn("kStartupPrecacheMovieReadBytes = 65536U", runtime)
        self.assertIn("kStartupPrecacheReceiptPath", runtime)
        self.assertIn("kM00CacheIndex", runtime)
        self.assertIn("kM01CacheIndex", runtime)
        self.assertIn("cache/m00-tutorial-mix-index-v1.txt", runtime)
        self.assertIn("cache/m01-mix-index-v1.txt", runtime)
        self.assertIn("a35-dev82-startup-precache.txt", runtime)
        self.assertIn("Pre-cache / pre-warm / pre-compute", runtime)
        self.assertIn("Required startup:      %u/%u", runtime)
        self.assertIn("Optional startup:      %u/%u", runtime)
        self.assertIn("Movie files:           %u/%u", runtime)
        self.assertIn("Cache indexes:         %u/%u (%u entries)", runtime)
        self.assertIn("Receipt: %s", runtime)
        self.assertIn("Startup_Index_Mix_Archive", runtime)
        self.assertIn("Startup_Write_Mix_Index_Cache", runtime)
        self.assertIn("Safe_Startup_Cache_Entry_Name", runtime)
        self.assertIn("Build_Filename_List(names)", runtime)
        self.assertIn("schema=renegade-vita-mix-index-v1", runtime)
        self.assertIn("Renegade_Resolve_Path(kVitaRoots", runtime)
        self.assertIn("Renegade_Inspect_Mix_Index_Cache", runtime)
        self.assertIn("struct A31StartupPrecacheFileSpec", runtime)
        self.assertIn("Startup_Touch_File(factory, startup_files[index]", runtime)
        self.assertIn("state.required_files_opened", runtime)
        self.assertIn("state.optional_files_opened", runtime)
        self.assertIn("state.movie_files_opened", runtime)
        self.assertIn("state.cache_indexes_written", runtime)
        self.assertIn("state.cache_entries_written", runtime)
        self.assertIn("Draw_Engine_Setup_Screen", runtime)
        self.assertIn("Original engine setup / frontend handoff", runtime)
        self.assertIn("This screen stays active until vitaGL owns display.", runtime)
        self.assertIn("Starting vitaGL renderer", runtime)
        self.assertLess(
            runtime.index(
                '"Starting original audio provider"'
            ),
            runtime.index("WWAudioClass application_audio(false);"),
        )
        self.assertLess(
            runtime.index('"Starting vitaGL renderer"'),
            runtime.index("psvDebugScreenFinish();"),
        )
        self.assertLess(
            runtime.index("psvDebugScreenFinish();"),
            runtime.index("ww3d_initialized = WW3D::Init(NULL, NULL, true)"),
        )
        self.assertIn("{ kAlwaysArchive, true, kStartupPrecacheRequiredReadBytes }", runtime)
        self.assertIn("{ kM00Archive, true, kStartupPrecacheRequiredReadBytes }", runtime)
        self.assertIn('"DATA\\\\MOVIES\\\\EA_WW.BIK"', runtime)
        self.assertIn('"DATA\\\\MOVIES\\\\R_INTRO.BIK"', runtime)
        self.assertIn('"IF_BACK01.W3D"', runtime)
        self.assertIn('"M00_Tutorial.lsd"', runtime)
        self.assertIn('"54251___.TTF"', runtime)
        self.assertIn('"ARI_____.TTF"', runtime)
        self.assertIn('"FONT12x16.TGA"', runtime)
        self.assertIn('"HUD_MAIN.TGA"', runtime)
        self.assertIn('"hud_6x4_Messages.tga"', runtime)
        self.assertIn('"POG_M00_1_01.tga"', runtime)
        self.assertIn("Validate_StyleMgr_Font_Glyphs", runtime)
        self.assertIn(
            '"A3.5 prewarm: startup-precache touch kind=%s name=%s opened=%d read_bytes=%u limit=%u movie=%d',
            runtime,
        )
        self.assertIn(
            '"A3.5 prewarm: startup-precache complete pass=%d archives=%u/%u entries=%u files=%u/%u required_files=%u/%u optional_files=%u/%u movie_files=%u/%u cache_indexes=%u/%u cache_entries=%u',
            runtime,
        )
        self.assertIn("m00_cache_ok", runtime)
        self.assertIn("state.required_files_opened == state.required_files_touched", runtime)
        self.assertIn("Write_Startup_Precache_Receipt(state,", runtime)
        self.assertLess(
            runtime.index("startup-precache visible hold remaining_ms=%llu"),
            runtime.index("Write_Startup_Precache_Receipt(state,"),
        )
        self.assertIn("first_missing_required=%s", runtime)
        self.assertIn("first_missing_optional=%s", runtime)
        self.assertIn("cache_indexes=%u/%u", runtime)
        self.assertIn("cache_entries=%u", runtime)
        self.assertIn("cache_issue=%s", runtime)
        self.assertIn("startup-precache visible hold remaining_ms=%llu", runtime)
        self.assertIn("visible_minimum_ms=%llu", runtime)
        self.assertNotIn("sceKernelDelayThread(300000)", runtime)
        self.assertNotIn("sceKernelDelayThread(250000)", runtime)
        self.assertNotIn("sceKernelDelayThread(180000)", runtime)
        self.assertNotIn("sceKernelDelayThread(450000)", runtime)
        self.assertIn("Flush_Debug_Status(3U);", runtime)
        startup_precache_call = runtime.index(
            "Run_Visible_Startup_Precache_Phase("
        )
        frontend_menu_call = runtime.index(
            "Run_Original_Frontend_Intro_And_Menu(frontend_menu_mode"
        )
        self.assertLess(startup_precache_call, frontend_menu_call)
        self.assertLess(
            startup_precache_call,
            runtime.index("WWAudioClass application_audio(false);"),
        )
        self.assertIn("psvDebugScreenFinish();", runtime[startup_precache_call:])
        self.assertIn(
            "A3.5 prewarm: FAIL startup precache/precompute phase before frontend",
            runtime,
        )
        self.assertIn("kLoadingPrewarmFrames = 1U", runtime)
        self.assertIn("kM00ScenePrewarmFrames = 60U", runtime)
        self.assertIn('"Prewarming loading cache"', runtime)
        self.assertIn('"Prewarming M00 scene cache"', runtime)
        self.assertIn("TextureLoader::Suspend_Texture_Load();", runtime)
        self.assertIn("TextureLoader::Continue_Texture_Load();", runtime)
        self.assertIn("CombatGameModeClass::Vita_Begin_Level_Load(", runtime)
        self.assertIn("CombatGameModeClass::Vita_Finalize_Loaded_Level(", runtime)
        self.assertIn("A31VitaScopedLoadingPresenterCallback", runtime)
        self.assertIn("g_active_loading_presenter", runtime)
        self.assertIn("A31_Vita_Render_Original_Loading_Callback", runtime)
        self.assertIn("synchronous-load callback armed", runtime)
        self.assertIn("synchronous-load callback disarmed", runtime)
        self.assertIn("synchronous-load callback ignored", runtime)
        self.assertIn(
            "A31VitaScopedLoadingPresenterCallback loading_callback(",
            runtime,
        )
        self.assertIn(
            "port/patches/combat-a35-vita-loading-progress-callback.patch",
            (ROOT / "tools/stage_sources.sh").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "VITA_LEVEL_LOAD_PRESENT(\"thread-entry\", 0);",
            (ROOT / "staging/combat/combat.cpp").read_text(
                encoding="utf-8", errors="replace"
            ),
        )
        self.assertIn(
            "VITA_LEVEL_LOAD_PRESENT(\"load-game-return\", 6);",
            (ROOT / "staging/combat/combat.cpp").read_text(
                encoding="utf-8", errors="replace"
            ),
        )
        self.assertIn('loading_presenter.Render_Original_Progress("post_load_processing");', runtime)
        self.assertIn('loading_presenter.Render_Original_Progress("post_load_level");', runtime)
        self.assertIn('loading_presenter.Render_Original_Progress("level_ready", true, 7);', runtime)
        self.assertIn("Make_Loading_Capture_State", runtime)
        self.assertIn('"original-loading-screen"', runtime)
        self.assertIn('"level-ready"', runtime)
        self.assertIn('"original-loading-screen-level-ready-t%llu"', runtime)
        self.assertIn("state.loading_visual_gate.active = true;", runtime)
        self.assertIn("state.loading_visual_gate.original_logical_width", runtime)
        self.assertIn("state.loading_visual_gate.original_logical_height", runtime)
        self.assertIn("state.loading_visual_gate.native_display_width = RenegadeVitaRenderer::DISPLAY_WIDTH;", runtime)
        self.assertIn("state.loading_visual_gate.native_display_height = RenegadeVitaRenderer::DISPLAY_HEIGHT;", runtime)
        self.assertIn("state.loading_visual_gate.native_presentation_x = rect.x;", runtime)
        self.assertIn("state.loading_visual_gate.native_presentation_y = rect.y;", runtime)
        self.assertIn("state.loading_visual_gate.native_presentation_width = rect.width;", runtime)
        self.assertIn("state.loading_visual_gate.native_presentation_height = rect.height;", runtime)
        self.assertIn("state.loading_visual_gate.logical_to_native_fullscreen =", runtime)
        self.assertIn("state.loading_visual_gate.aspect_preserved = true;", runtime)
        self.assertIn("state.loading_visual_gate.original_loading_screen_owner = true;", runtime)
        self.assertIn("state.loading_visual_gate.direct_vitagl_overlay_disabled = true;", runtime)
        self.assertIn("state.loading_visual_gate.loading_texture_v_flip_enabled = false;", runtime)
        self.assertIn("state.loading_visual_gate.gameplay_texture_v_unchanged = true;", runtime)
        self.assertNotIn("A31FrameHistory capture_history;", runtime)
        self.assertNotIn("A31FrameHistory loading_capture_history;", runtime)
        self.assertIn("new (std::nothrow) A31FrameHistory", runtime)
        self.assertIn("delete capture_history;", runtime)
        self.assertIn("capture_history->Reset();", runtime)
        self.assertIn("RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(capture_pixels, kCaptureBytes)", runtime)
        self.assertIn("Capture: %s candidate=%s phase=original-loading-screen reason=level-ready", runtime)
        self.assertLess(
            runtime.index('loading_presenter.Render_Original_Progress("level_ready", true, 7);'),
            runtime.index("phase=original-loading-screen reason=level-ready"),
        )
        capture_log_index = runtime.index("phase=original-loading-screen reason=level-ready")
        self.assertLess(
            capture_log_index,
            runtime.index("TextWindowClass::Initialize(CombatManager::Get_Background_Scene())"),
        )
        self.assertIn(
            "A31_Interactive_Apply_Render_Capabilities();",
            runtime[capture_log_index:],
        )
        prewarm_definition = runtime.index("void Warm_Original_M00_Presentation_Cache")
        prewarm_call = runtime.index("Warm_Original_M00_Presentation_Cache(loading_presenter);")
        level_ready_call = runtime.index('loading_presenter.Render_Original_Progress("level_ready", true, 7);')
        self.assertIn(
            "A31_Interactive_Apply_Render_Capabilities();",
            runtime[prewarm_definition:prewarm_call],
        )
        self.assertLess(prewarm_call, level_ready_call)
        scene_prewarm_definition = runtime.index(
            "bool Warm_Original_M00_Interactive_Presentation_Cache"
        )
        scene_prewarm_call = runtime.index(
            "if (!Warm_Original_M00_Interactive_Presentation_Cache(",
        )
        initialized_index = runtime.index("result.initialized = true;")
        input_loop_index = runtime.index("while (true)", initialized_index)
        self.assertIn(
            "A31_Interactive_Run_Render_Frame();",
            runtime[scene_prewarm_definition:scene_prewarm_call],
        )
        scene_prewarm = runtime[scene_prewarm_definition:scene_prewarm_call]
        self.assertIn(
            'Apply_Original_Gameplay_Render_Resolution("prewarm_m00_scene"',
            scene_prewarm,
        )
        self.assertIn("loading_overlay_frames=0", scene_prewarm)
        self.assertNotIn(
            'loading_presenter.Render_Original_Progress("prewarm_m00_scene"',
            scene_prewarm,
        )
        self.assertIn(
            '"A3.5 prewarm: m00-scene complete rendered=%d frames=%u',
            runtime[scene_prewarm_definition:scene_prewarm_call],
        )
        self.assertLess(scene_prewarm_call, initialized_index)
        self.assertLess(scene_prewarm_call, input_loop_index)
        post_capture_restore = runtime.index(
            'Apply_Original_Gameplay_Render_Resolution(\n\t\t\t\t\t"post-loading-capture"'
        )
        self.assertLess(capture_log_index, post_capture_restore)
        self.assertLess(
            post_capture_restore,
            runtime.index("TextWindowClass::Initialize(CombatManager::Get_Background_Scene())"),
        )
        gameplay_resolution_definition = runtime.index(
            "bool Apply_Original_Gameplay_Render_Resolution"
        )
        gameplay_resolution_body = runtime[
            gameplay_resolution_definition:runtime.index(
                "bool Apply_Original_Loading_Render_Resolution_For_Prewarm",
                gameplay_resolution_definition,
            )
        ]
        self.assertIn("RenegadeVitaRenderer::DISPLAY_WIDTH", gameplay_resolution_body)
        self.assertIn("RenegadeVitaRenderer::DISPLAY_HEIGHT", gameplay_resolution_body)
        self.assertNotIn("kOriginalLoadingLogicalWidth", gameplay_resolution_body)
        self.assertNotIn("kOriginalLoadingLogicalHeight", gameplay_resolution_body)
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

        main = (ROOT / "port/platform/vita/a30_main.cpp").read_text(
            encoding="utf-8"
        )
        header = (ROOT / "port/platform/vita/a31_vita_runtime.h").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime(\n\tint startup_screen_result = -1);",
            header,
        )
        self.assertIn("A31_Vita_Run_Interactive_Runtime(screen_result)", main)

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
        self.assertIn("g_boundary_viewport.Width = g_logical_viewport_width;", boundary)
        self.assertIn("RenegadeVitaRenderer::Apply_Viewport(g_boundary_viewport.X", boundary)
        self.assertIn("DX8Wrapper::Set_Device_Resolution logical=%dx%d", boundary)
        self.assertIn("logical_width", renderer)
        self.assertIn("logical_height", renderer)
        self.assertNotIn("bool flip_texture_v;", renderer_h)
        self.assertIn("const char *texture_names[2];", renderer_h)
        self.assertIn('prefix[] = "loadscreen_"', renderer)
        self.assertIn("Has_Loadscreen_Texture_Prefix(texture_name)", renderer)
        self.assertNotIn("Should_Flip_Submitted_Texture_V", renderer)
        self.assertIn("first gameplay passthrough texture V preserved", renderer)
        self.assertNotIn("(void)texture_name;", renderer)
        self.assertIn("first cached original ShaderClass state skip", renderer)
        self.assertIn("first cached original CameraClass viewport skip", renderer)
        self.assertIn("g_current_native_viewport_known", renderer)
        self.assertIn("Invalidate_Original_Shader_State_Cache();", renderer)
        self.assertIn("shader_state_overlap = true;", renderer)
        self.assertIn("vglSetShaderCachePath(shader_cache_path);", renderer)
        self.assertLess(
            renderer.index("vglSetShaderCachePath(shader_cache_path);"),
            renderer.index("const GLboolean resolution_fallback = vglInit"),
        )

        gameplay = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text(
            encoding="utf-8"
        )
        hud = (ROOT / "staging/combat/hud.cpp").read_text(
            encoding="utf-8", errors="replace"
        )
        stage_sources = (ROOT / "tools/stage_sources.sh").read_text(
            encoding="utf-8"
        )
        hud_header = (
            ROOT / "port/compatibility/include/a31_vita_hud_presentation.h"
        ).read_text(encoding="utf-8")
        combat_patch = (
            ROOT / "port/patches/combat-a35-vita-hud-presentation-boundary.patch"
        ).read_text(encoding="utf-8")
        stage = (ROOT / "tools/stage_sources.sh").read_text(encoding="utf-8")
        self.assertIn("A31_Vita_Begin_Original_HUD_Render", hud_header)
        self.assertIn("A31_Vita_End_Original_HUD_Render", hud_header)
        self.assertIn("A31GameplayHUDRenderPresentation", gameplay)
        self.assertLess(
            gameplay.index("CombatManager::Render();"),
            gameplay.index("A31ScopedGameplayHUDRender2DResolution hud_render_resolution;"),
        )
        self.assertLess(
            combat_patch.index("A31_Vita_Begin_Original_HUD_Render();"),
            combat_patch.index("HUDClass::Render();"),
        )
        self.assertLess(
            combat_patch.index("ScreenFadeManager::Render();"),
            combat_patch.index("A31_Vita_End_Original_HUD_Render();"),
        )
        self.assertIn("combat-a35-vita-hud-presentation-boundary.patch", stage)
        shader_apply_start = renderer.index("void Apply_Original_Shader_State")
        shader_apply = renderer[
            shader_apply_start:
            renderer.index("const ShaderStateContract state", shader_apply_start)
        ]
        self.assertLess(
            shader_apply.index("Apply_Original_Fog_State(shader);"),
            shader_apply.index("g_original_shader_state_known"),
        )
        self.assertNotIn("t = 1.0f - t;", renderer)
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
        validator_source = (ROOT / "tools/validate_vita_loading_capture.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("A31_CAPTURE_SCHEMA_VERSION = 4U", capture_header)
        self.assertIn("A31LoadingVisualGateTelemetry", capture_header)
        self.assertIn("native_presentation_x", capture_header)
        self.assertIn("native_presentation_width", capture_source)
        self.assertIn("aspect_preserved", capture_source)
        self.assertIn("loading_visual_gate", capture_source)
        self.assertIn("Loading visual gate: active=%d logical=%ux%u", capture_source)
        self.assertIn('"loading_visual_gate.logical_to_native_fullscreen"', compare_source)
        self.assertIn('"loading_visual_gate.native_presentation_width"', compare_source)
        self.assertIn('"loading_visual_gate.aspect_preserved"', compare_source)
        self.assertIn('"native_presentation_x": 117', validator_source)
        self.assertIn('"native_presentation_width": 725', validator_source)
        self.assertIn('"logical_to_native_fullscreen": False', validator_source)
        self.assertIn('"aspect_preserved": True', validator_source)

        self.assertIn("g_native_presentation_rect", renderer)
        self.assertIn("Set_Native_Presentation_Rect", renderer_h)
        self.assertIn("Reset_Native_Presentation_Rect", renderer_h)
        self.assertIn("g_native_presentation_rect.width", renderer)
        self.assertIn("g_native_presentation_rect.height", renderer)
        self.assertIn("native presentation rect: top_left=%u,%u", renderer)

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
        self.assertIn("${RENEGADE_STAGE}/commando/combatgmode.cpp", cmake)
        self.assertIn("${RENEGADE_STAGE}/commando/campaign.cpp", cmake)
        self.assertIn("${RENEGADE_STAGE}/wwui/menubackdrop.cpp", cmake)
        self.assertIn("${RENEGADE_STAGE}/wwui/stylemgr.cpp", cmake)
        self.assertIn("RENEGADE_A35_ORIGINAL_COMBATGMODE=1", cmake)
        self.assertIn("${RENEGADE_STAGE}/ww3d2/render2d.cpp", original_sources)
        self.assertIn("${RENEGADE_STAGE}/ww3d2/render2dsentence.cpp", original_sources)

    def test_render2d_dynamic_vertices_initialize_declared_fvf_fields(self):
        render2d = (ROOT / "staging/ww3d2/render2d.cpp").read_text(
            encoding="utf-8", errors="replace"
        )
        patch = (
            ROOT / "port/patches/ww3d2-a35-render2d-dynamic-fvf-init.patch"
        ).read_text(encoding="utf-8")
        stage_sources = (ROOT / "tools/stage_sources.sh").read_text(
            encoding="utf-8"
        )

        for source in (render2d, patch):
            self.assertIn("const Vector3 normal(0.0f,0.0f,1.0f);", source)
            self.assertIn("fi.Get_Normal_Offset()", source)
            self.assertIn("fi.Get_Tex_Offset(1)", source)
            self.assertIn("DX8Wrapper::Set_Texture(1,NULL);", source)
        self.assertIn("ww3d2-a35-render2d-dynamic-fvf-init.patch", stage_sources)

    def test_render2d_restores_previous_viewport_after_2d_pass(self):
        render2d = (ROOT / "staging/ww3d2/render2d.cpp").read_text(
            encoding="utf-8", errors="replace"
        )
        patch = (
            ROOT / "port/patches/ww3d2-a35-render2d-viewport-restore.patch"
        ).read_text(encoding="utf-8")
        stage_sources = (ROOT / "tools/stage_sources.sh").read_text(
            encoding="utf-8"
        )

        for source in (render2d, patch):
            self.assertIn("D3DVIEWPORT8 previous_viewport = { 0 };", source)
            self.assertIn("GetViewport(&previous_viewport)", source)
            self.assertIn("restore_viewport = true;", source)
            self.assertIn("DX8Wrapper::Set_Viewport(&previous_viewport);", source)
        self.assertLess(
            render2d.index("GetViewport(&previous_viewport)"),
            render2d.index("DX8Wrapper::Set_Viewport(&vp);"),
        )
        self.assertLess(
            render2d.index("DX8Wrapper::Draw_Triangles("),
            render2d.rindex("DX8Wrapper::Set_Viewport(&previous_viewport);"),
        )
        self.assertIn("ww3d2-a35-render2d-viewport-restore.patch", stage_sources)

    def test_gameplay_hud_uses_native_render2d_coordinates(self):
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        gameplay = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text(
            encoding="utf-8"
        )
        hud = (ROOT / "staging/combat/hud.cpp").read_text(
            encoding="utf-8", errors="replace"
        )
        stage_sources = (ROOT / "tools/stage_sources.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("kGameplayHUDLogicalWidth =", runtime)
        self.assertIn("kGameplayHUDLogicalHeight =", runtime)
        self.assertIn("RenegadeVitaRenderer::DISPLAY_WIDTH", runtime)
        self.assertIn("RenegadeVitaRenderer::DISPLAY_HEIGHT", runtime)
        runtime_helper = runtime[
            runtime.index("class A31VitaScopedGameplayHUDRender2DResolution"):
            runtime.index("void Copy_Renderer_Statistics")
        ]
        self.assertIn("Render2DClass::Set_Screen_Resolution(RectClass(0, 0,", runtime_helper)
        self.assertIn("kGameplayHUDLogicalWidth", runtime_helper)
        self.assertIn("kGameplayHUDLogicalHeight", runtime_helper)
        self.assertIn("native gameplay Render2D resolution", runtime_helper)
        self.assertNotIn("WW3D::Set_Device_Resolution", runtime_helper)

        for scope_name, call in (
            ("hud_init_resolution", "CombatManager::Init(render_hud);"),
            ("text_display_resolution", "text_display_mode.Init();"),
            (
                "hud_finalize_resolution",
                "CombatGameModeClass::Vita_Finalize_Loaded_Level(",
            ),
        ):
            self.assertLess(runtime.index(scope_name), runtime.index(call))

        self.assertIn('#include "render2d.h"', gameplay)
        self.assertIn("kA31GameplayHUDLogicalWidth =", gameplay)
        self.assertIn("kA31GameplayHUDLogicalHeight =", gameplay)
        self.assertIn("Build_A31_Gameplay_HUD_Presentation_Rect", gameplay)
        self.assertIn("Apply_A31_Gameplay_HUD_Presentation_Rect", gameplay)
        self.assertIn("Dev86/Dev87 physical returns showed target boxes", gameplay)
        self.assertIn("RenegadeVitaRenderer::DISPLAY_WIDTH", gameplay)
        self.assertIn("RenegadeVitaRenderer::DISPLAY_HEIGHT", gameplay)
        gameplay_helper = gameplay[
            gameplay.index("class A31GameplayHUDRenderPresentation"):
            gameplay.index("AudibleSoundClass *Find_Conversation_Speech_For_Diagnostics")
        ]
        self.assertIn("Render2DClass::Set_Screen_Resolution(RectClass(0, 0,", gameplay_helper)
        self.assertIn("Apply_A31_Gameplay_HUD_Presentation_Rect()", gameplay_helper)
        self.assertIn("RenegadeVitaRenderer::Reset_Native_Presentation_Rect_Quiet();", gameplay_helper)
        self.assertNotIn("WW3D::Set_Device_Resolution", gameplay_helper)
        self.assertNotIn("combat-a35-vita-target-overlay-ww3d-include.patch", stage_sources)
        self.assertNotIn("combat-a35-vita-target-overlay-native-scope.patch", stage_sources)
        self.assertIn("combat-a35-target-box-diagnostics.patch", stage_sources)
        self.assertNotIn("WW3D::Get_Device_Resolution(target_device_width", hud)
        self.assertNotIn("target_native_screen", hud)
        self.assertNotIn("TargetRenderer->Set_Coordinate_Range(target_screen);", hud)
        self.assertIn("box = Get_Target_Box( obj->As_PhysicalGameObj() );", hud)
        self.assertIn("RectClass\tscreen = Render2DClass::Get_Screen_Resolution();", hud)
        self.assertIn("A3.5 HUD target-box", hud)
        self.assertIn("WW3D::Get_Device_Resolution(device_width", hud)
        self.assertIn("COMBAT_CAMERA->Get_Aspect_Ratio()", hud)

        renderer_header = (ROOT / "port/renderer/vita/ww3d_vita_renderer.h").read_text(
            encoding="utf-8"
        )
        renderer = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("Set_Native_Presentation_Rect_Quiet", renderer_header)
        self.assertIn("Reset_Native_Presentation_Rect_Quiet", renderer_header)
        self.assertIn("Set_Native_Presentation_Rect_Internal", renderer)
        self.assertIn("if (log_change)", renderer)

        hud_scope = "A31ScopedGameplayHUDRender2DResolution hud_render_resolution;"
        self.assertLess(gameplay.index("CombatManager::Render();"), gameplay.index(hud_scope))
        self.assertLess(gameplay.index(hud_scope), gameplay.index("message_window->Render();"))
        self.assertLess(gameplay.index(hud_scope), gameplay.index("ObjectiveManager::Render_Viewer();"))
        self.assertLess(gameplay.index(hud_scope), gameplay.index("text_display->Render();"))

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
