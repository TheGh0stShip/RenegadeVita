import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class A4OriginalFrontendContractTests(unittest.TestCase):
    def test_cmake_selects_original_frontend_and_boundary_sources(self):
        cmake = (ROOT / "CMakeLists.txt").read_text()
        host_cmake = (ROOT / "tools" / "host_a30_definitions" / "CMakeLists.txt").read_text()

        self.assertIn("option(RENEGADE_A4_ORIGINAL_FRONTEND", cmake)
        for token in (
            "${RENEGADE_STAGE}/wwui/dialogmgr.cpp",
            "${RENEGADE_STAGE}/wwui/wwuiinput.cpp",
            "${RENEGADE_STAGE}/wwui/menudialog.cpp",
            "${RENEGADE_STAGE}/wwui/menubackdrop.cpp",
            "${RENEGADE_STAGE}/commando/renegadedialogmgr.cpp",
            "${RENEGADE_STAGE}/commando/dlgmainmenu.cpp",
            "${RENEGADE_STAGE}/commando/dialogtests.cpp",
            "${RENEGADE_STAGE}/commando/dlgloadspgame.cpp",
            "${RENEGADE_STAGE}/commando/mainmenutransition.cpp",
            "${RENEGADE_STAGE}/commando/gamemode.cpp",
            "${RENEGADE_STAGE}/commando/gamemenu.cpp",
            "${RENEGADE_STAGE}/commando/movie.cpp",
            "${RENEGADE_STAGE}/combat/savegame.cpp",
            "port/platform/renegade_dialog_resource_provider.cpp",
            "port/platform/a4_frontend_lifecycle_boundary.cpp",
            "port/platform/a4_binkmovie_boundary.cpp",
        ):
            self.assertIn(token, cmake)

        for token in (
            "RENEGADE_A4_ORIGINAL_FRONTEND=1",
            "RENEGADE_A4_ORIGINAL_GAMEMODE=1",
            "RENEGADE_A4_ORIGINAL_MOVIE_OWNER=1",
            "RENEGADE_VITA_FRONTEND_SINGLEPLAYER=1",
            "RENEGADE_VITA_A4_FRONTEND_PORT_SOURCES=6",
        ):
            self.assertIn(token, cmake)
            self.assertIn(token, host_cmake)

        self.assertIn("${RV_STAGE}/commando/movie.cpp", host_cmake)
        self.assertIn("${RV_ROOT}/port/platform/a4_binkmovie_boundary.cpp", host_cmake)

    def test_frontend_staging_patches_are_deterministic_and_original_owner_scoped(self):
        stage_sources = (ROOT / "tools" / "stage_sources.sh").read_text()
        gameinit_patch = (
            ROOT / "port" / "patches" / "commando-a4-gameinitmgr-frontend-start-latch.patch"
        ).read_text()
        movie_patch = (
            ROOT / "port" / "patches" / "commando-a4-movie-vita-provider-boundary.patch"
        ).read_text()
        staged_gameinit = (ROOT / "staging" / "commando" / "gameinitmgr.cpp").read_text()
        staged_movie = (ROOT / "staging" / "commando" / "movie.cpp").read_text()

        for patch_name in (
            "commando-a4-gameinitmgr-frontend-start-latch.patch",
            "commando-a4-movie-vita-provider-boundary.patch",
            "a4-post-movie-mainmenu-hardening.patch",
        ):
            self.assertIn(patch_name, stage_sources)
            self.assertIn("--fuzz=0 --no-backup-if-mismatch", stage_sources)

        latch_index = gameinit_patch.index("A4_Frontend_Latch_Start_Game")
        return_index = gameinit_patch.index("return ;", latch_index)
        self.assertLess(latch_index, return_index)
        self.assertIn('#include "a4_frontend_lifecycle_boundary.h"', gameinit_patch)
        self.assertIn("A4_Frontend_Latch_Start_Game(map_name, teamChoice, clanID)", staged_gameinit)

        self.assertIn("MovieGameModeClass::Start_Movie", movie_patch)
        self.assertIn("Play_Movie( filename );", movie_patch)
        self.assertIn("RENEGADE_A4_ORIGINAL_FRONTEND", staged_movie)
        self.assertIn("Play_Movie( filename );", staged_movie)

    def test_controller_navigation_maps_to_wwui_without_breaking_gameplay_keys(self):
        directinput = (ROOT / "port" / "platform" / "renegade_directinput.cpp").read_text()
        lifecycle = (ROOT / "port" / "platform" / "a4_frontend_lifecycle_boundary.cpp").read_text()
        header = (ROOT / "port" / "platform" / "a4_frontend_lifecycle_boundary.h").read_text()
        controls_doc = (ROOT / "docs" / "CONTROLS.md").read_text()

        self.assertIn('#include "a4_frontend_lifecycle_boundary.h"', directinput)
        self.assertIn("const bool frontend_menu_navigation = A4_Frontend_Is_Menu_Loop_Active();", directinput)
        self.assertIn("const bool gameplay_input_active = !frontend_menu_navigation;", directinput)
        for key_name, sce_button in (
            ("VK_UP", "SCE_CTRL_UP"),
            ("VK_DOWN", "SCE_CTRL_DOWN"),
            ("VK_LEFT", "SCE_CTRL_LEFT"),
            ("VK_RIGHT", "SCE_CTRL_RIGHT"),
        ):
            self.assertIn(f"Set_Virtual_Key({key_name},", directinput)
            self.assertIn(f"frontend_menu_navigation && (buttons & {sce_button}) != 0", directinput)

        for token in (
            "Set_Virtual_Key(VK_RETURN, (buttons & SCE_CTRL_CROSS) != 0);",
            "Set_Virtual_Key(VK_ESCAPE, (buttons & SCE_CTRL_CIRCLE) != 0);",
            "Set_Virtual_Key(VK_TAB, (buttons & SCE_CTRL_SELECT) != 0);",
            "CursorPos.X = front_touch.x;",
            "CursorPos.Y = front_touch.y;",
            "Set_Button(DIMouseButtons, DirectInput::BUTTON_MOUSE_LEFT & 0xFF",
            "front touch feeds original mouse cursor and left click",
            "gameplay_input_active && back_touch.down",
            "gameplay_input_active && (buttons & SCE_CTRL_UP) != 0",
            "gameplay_input_active && (buttons & SCE_CTRL_DOWN) != 0",
            "gameplay_input_active && (buttons & SCE_CTRL_LEFT) != 0",
            "gameplay_input_active && (buttons & SCE_CTRL_RIGHT) != 0",
            "gameplay_input_active && (buttons & SCE_CTRL_CROSS) != 0",
            "gameplay_input_active && (buttons & SCE_CTRL_CIRCLE) != 0",
            "gameplay_input_active && (buttons & SCE_CTRL_TRIANGLE) != 0",
            "gameplay_input_active && (buttons & SCE_CTRL_SQUARE) != 0",
            "gameplay_input_active && (buttons & SCE_CTRL_LTRIGGER) != 0",
            "gameplay_input_active && (buttons & SCE_CTRL_RTRIGGER) != 0",
            "gameplay_input_active ? left.x.logical : 0",
            "gameplay_input_active ? left.y.logical : 0",
            "DirectInput::Read first entry captured=%d",
            "DirectInput::Read first controller buttons=%08X",
            "DirectInput::Read first touch front/back=%d/%d",
            "DirectInput::Read first complete",
        ):
            self.assertIn(token, directinput)
        self.assertIn("Set_Button(DIKeyboardButtons, DIK_ESCAPE, (buttons & SCE_CTRL_START) != 0);", directinput)

        self.assertIn("A4_Frontend_Pump_WWUI_Key_Transitions", header)
        self.assertIn("g_frontend_key_dispatcher.ProcessMessage(NULL, message", lifecycle)
        self.assertIn("WM_KEYDOWN", lifecycle)
        self.assertIn("WM_KEYUP", lifecycle)
        self.assertIn("D-pad navigates the original WWUI focus", controls_doc)
        self.assertIn("Front touch", controls_doc)
        self.assertIn("mouse cursor", controls_doc)
        self.assertIn("Rear touch pad", controls_doc)
        self.assertIn("First-person / third-person camera toggle", controls_doc)

    def test_main_menu_tutorial_handoff_reaches_existing_original_m00_route(self):
        dialogtests = (ROOT / "staging" / "commando" / "dialogtests.cpp").read_text()
        gameinit = (ROOT / "staging" / "commando" / "gameinitmgr.cpp").read_text()
        runtime = (ROOT / "port" / "platform" / "vita" / "a31_vita_runtime.cpp").read_text()
        host = (ROOT / "tools" / "host_a30_definitions" / "a31_interactive_main.cpp").read_text()

        self.assertIn("GameInitMgrClass::Start_Game (TUTORIAL_MAP_NAME, -1, 0);", dialogtests)
        handoff_index = runtime.index("const bool frontend_tutorial_selected")
        direct_route_index = runtime.index("GameInitMgrClass::Initialize_SP();", handoff_index)
        self.assertLess(handoff_index, direct_route_index)
        self.assertIn("Run_Original_Frontend_Intro_And_Menu", runtime)
        self.assertLess(
            runtime.index("A4_Frontend_Begin_Menu_Loop();"),
            runtime.index("Input::Menu_Enable(true);"),
        )
        self.assertLess(
            runtime.index("Input::Menu_Enable(true);"),
            runtime.index("Input::Update();"),
        )
        self.assertLess(
            runtime.index("Input::Update();"),
            runtime.index("Input::Menu_Enable(false);"),
        )
        self.assertIn("registered original CombatGameMode owner", runtime)
        self.assertIn("frontend_menu_mode_registered_for_handoff", runtime)
        self.assertIn("retained original Menu mode through Combat handoff", runtime)
        self.assertIn("removed retained Menu mode after Combat handoff", runtime)
        self.assertIn('GameModeManager::Find("Menu") == &frontend_menu_mode', runtime)
        self.assertIn("StyleMgrClass::Initialize_From_INI(kStyleManagerIni);", runtime[handoff_index:direct_route_index])
        final_style_index = runtime.index(
            "StyleMgrClass::Initialize_From_INI(kStyleManagerIni);",
            handoff_index,
        )
        text_display_index = runtime.index(
            "original TextDisplayGameMode init after final StyleMgr",
            handoff_index,
        )
        self.assertLess(final_style_index, text_display_index)
        self.assertLess(text_display_index, direct_route_index)
        combat_deactivate_index = runtime.index("frontend_combat_mode.Deactivate();")
        player_remove_index = runtime.index("cPlayerManager::Remove_All();")
        combat_remove_index = runtime.index("GameModeManager::Remove(&frontend_combat_mode);")
        menu_remove_index = runtime.rindex("GameModeManager::Remove(&frontend_menu_mode);")
        self.assertLess(combat_deactivate_index, menu_remove_index)
        self.assertLess(menu_remove_index, player_remove_index)
        self.assertLess(player_remove_index, combat_remove_index)
        self.assertIn(
            "retained inactive Combat mode through player/session teardown", runtime
        )
        self.assertIn(
            "removed original Combat mode after player/session teardown", runtime
        )
        self.assertIn("A4_Frontend_Latch_Start_Game", gameinit)
        self.assertIn("Validate_Frontend_Tutorial_Start_Latch", host)
        self.assertIn("frontend_tutorial_start_latched", host)
        self.assertIn("frontend_tutorial_latched_map", host)

    def test_native_console_never_suppresses_original_menu_or_movie_rendering(self):
        console_stub = (ROOT / "port" / "compatibility" / "include" / "a31_console_stub.h").read_text()
        game_mode = (ROOT / "staging" / "commando" / "gamemode.cpp").read_text()
        runtime = (ROOT / "port" / "platform" / "vita" / "a31_vita_runtime.cpp").read_text()

        # The original manager intentionally does not call any game-mode Render
        # while the desktop console owns the presentation surface.  Vita has no
        # such surface, so its boundary must release that original gate before
        # it enters the original intro/menu loop.
        self.assertIn("ConsoleModeClass(void) : Exclusive(false)", console_stub)
        self.assertIn("if (!ConsoleBox.Is_Exclusive())", game_mode)
        self.assertIn("ConsoleBox.Set_Exclusive(false);", runtime)
        self.assertIn(
            "native presentation console_exclusive=%d; original WWUI and Bink rendering enabled",
            runtime,
        )
        self.assertLess(
            runtime.index("ConsoleBox.Set_Exclusive(false);"),
            runtime.rindex("Run_Original_Frontend_Intro_And_Menu("),
        )

    def test_intro_movie_provider_uses_original_owner_and_vita_ffmpeg(self):
        movie = (ROOT / "staging" / "commando" / "movie.cpp").read_text()
        bink = (ROOT / "port" / "platform" / "a4_binkmovie_boundary.cpp").read_text()
        runtime = (ROOT / "port" / "platform" / "vita" / "a31_vita_runtime.cpp").read_text()
        host = (ROOT / "tools" / "host_a30_definitions" / "a31_interactive_main.cpp").read_text()
        known_gaps = (ROOT / "reports" / "KNOWN_GAPS.md").read_text()
        dependency_build = (ROOT / "tools" / "build_ffmpeg_bink_vita.sh").read_text()

        for token in (
            "MovieGameModeClass::Startup_Movies",
            "Start_Movie( \"DATA\\\\MOVIES\\\\EA_WW.BIK\" )",
            "Start_Movie( \"DATA\\\\MOVIES\\\\R_INTRO.BIK\" )",
            "RenegadeDialogMgrClass::Goto_Location (RenegadeDialogMgrClass::LOC_MAIN_MENU)",
        ):
            self.assertIn(token, movie)

        self.assertIn("BINKMovie::Play", bink)
        self.assertIn("A4_Frontend_Record_Bink_Play(filename);", bink)
        self.assertIn("A4_Frontend_Record_Bink_Skip(filename);", bink)
        for token in (
            "Renegade_Resolve_Path",
            "Build_FFmpeg_File_URL",
            "file:%s",
            "#include <psp2/ctrl.h>",
            "SCE_CTRL_START",
            "SCE_CTRL_CROSS",
            "SCE_CTRL_CIRCLE",
            "SCE_CTRL_TRIANGLE",
            "sceCtrlPeekBufferPositive",
            "Prime_Skip_Button_Latch",
            "Check_Skip_Request",
            "A4 Bink: skip requested buttons=%08X",
            "kUpdateBudgetUs",
            "update budget yield",
            "avformat_open_input",
            "avcodec_find_decoder",
            "g_packet_pending",
            "Submit_Video_Packet",
            "Submit_Audio_Packet",
            "result == AVERROR(EAGAIN)",
            "sws_scale",
			"AV_PIX_FMT_RGB565LE",
			"kVideoUploadBytesPerPixel = 2U",
			"GL_UNSIGNED_SHORT_5_6_5",
			"upload_format=rgb565",
            "swr_convert",
            "sceAudioOutOpenPort",
            "SCE_AUDIO_OUT_PORT_TYPE_MAIN",
            "SCE_AUDIO_OUT_PORT_TYPE_VOICE",
            "SCE_AUDIO_OUT_PORT_TYPE_BGM",
            "SCE_AUDIO_OUT_ERROR_PORT_FULL",
            "all audio output ports unavailable",
            "audio ring unavailable/full capacity=%u count=%u samples=%u movie=%s",
            "const size_t available = capacity - g_audio_count;",
            "capacity > 0U ? std::min(output.size(), g_audio_count) : 0U",
            "A4 Bink: audio output thread entry port=%d ring_samples=%u",
            "A4 Bink: audio output first buffer port=%d copied=%u drained=%d waits=%llu movie=%s",
            "Never submit a zero-filled startup/starvation buffer.",
            "const bool full_output_ready = capacity > 0U &&",
            "g_audio_count >= output.size();",
            "g_audio_wait_count.fetch_add(1U, std::memory_order_relaxed);",
            "sceKernelDelayThread(1000U);",
			"A4 Bink: playback stats reason=%s movie=%s upload_format=rgb565 wall_ms=%llu",
            "audio_waits=%llu output_buffers/samples/partial=%llu/%llu/%llu",
            "audio_decode_calls/total/worst_us=%llu/%llu/%llu",
            "video_decode_calls/total/worst_us=%llu/%llu/%llu",
            "video_upload_calls/total/worst_us=%llu/%llu/%llu",
            "A4 Bink: update entry movie=%s audio=%d pending_packet=%d pending_video=%d texture=%d",
            "A4 Bink: first av_read_frame entry movie=%s",
            "A4 Bink: render entry movie=%s texture=%d pending_video=%d",
            "glTexSubImage2D",
            "Next_Power_Of_Two",
            "g_texture_width = Next_Power_Of_Two(g_video_width);",
            "g_texture_height = Next_Power_Of_Two(g_video_height);",
			"static_cast<size_t>(g_texture_width) *",
			"g_texture_height * kVideoUploadBytesPerPixel",
            "const int intended_texture_width = g_texture_allocated ?",
            "const GLenum setup_error = glGetError();",
            "A4 Bink: texture setup failed error=%08X stale_error=%08X video=%dx%d storage=%dx%d texture=%u movie=%s",
            "A4 Bink: texture upload failed error=%08X stale_error=%08X video=%dx%d storage=%dx%d movie=%s",
            "A failure belongs to this movie.",
            "static_cast<GLfloat>(g_video_width) / static_cast<GLfloat>(g_texture_width)",
            "static_cast<GLfloat>(g_video_height) / static_cast<GLfloat>(g_texture_height)",
            "const GLfloat scale = std::min(960.0F / static_cast<GLfloat>(g_video_width)",
            "texture0_enabled = glIsEnabled(GL_TEXTURE_2D);",
            "RenegadeVitaRenderer::Invalidate_Texture_State_Cache();",
            "movie open path logical=%s physical=%s url=%s",
        ):
            self.assertIn(token, bink)
        self.assertLess(
            bink.index("Build_FFmpeg_File_URL"),
            bink.index("avformat_open_input"),
        )
        self.assertLess(
            bink.index("Renegade_Resolve_Path"),
            bink.index("avformat_open_input"),
        )
        self.assertNotIn("kRealtimeBinkPlaybackEnabled", bink)
        self.assertNotIn("disables slow software Bink playback", bink)
        self.assertNotIn("g_movie_decode_disabled_after_upload_failure", bink)
        self.assertLess(
            bink.index("if (Check_Skip_Request()) return;"),
            bink.index("const int64_t elapsed_us"),
        )
        self.assertLess(
            bink.index("update_elapsed_us >= kUpdateBudgetUs"),
            bink.index("av_read_frame"),
        )
        self.assertLess(
            bink.index("if (capacity == 0U || g_audio_count >= capacity)"),
            bink.index("const size_t available = capacity - g_audio_count;"),
        )
        audio_output = bink.index("void *Audio_Output_Thread(void *)")
        self.assertLess(
            bink.index("const bool full_output_ready = capacity > 0U &&", audio_output),
            bink.index("const int result = sceAudioOutOutput", audio_output),
        )
        self.assertLess(
            bink.index("g_audio_wait_count.fetch_add(1U", audio_output),
            bink.index("const int result = sceAudioOutOutput", audio_output),
        )
        upload = bink.index("bool Upload_Pending_Video()")
        self.assertNotIn("GL_UNPACK_ALIGNMENT", bink)
        self.assertNotIn("glPixelStorei", bink)
        self.assertLess(
            bink.index("glGetError();", upload),
			bink.index("glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, g_texture_width, g_texture_height", upload),
        )
        self.assertLess(
            bink.index("const GLenum setup_error = glGetError();", upload),
			bink.index("glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, g_texture_width, g_texture_height", upload),
        )
        self.assertLess(
            bink.index("const int intended_texture_width = g_texture_allocated ?", upload),
            bink.index("const GLenum setup_error = glGetError();", upload),
        )
        self.assertLess(
            bink.index("const GLenum upload_error = glGetError();", upload),
            bink.index("g_texture_allocated = true;", upload),
        )
        self.assertLess(
            bink.index("g_texture_width = Next_Power_Of_Two(g_video_width);", upload),
			bink.index("glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, g_texture_width, g_texture_height", upload),
        )
        self.assertLess(
            bink.index("glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, g_video_width, g_video_height", upload),
            bink.index("const GLenum upload_error = glGetError();", upload),
        )
        self.assertNotIn("capacity - g_audio_count);", bink)
        self.assertIn("strchr(resolved.physical, ':')", bink)
        video_retry = bink.index("bool Submit_Video_Packet()")
        audio_retry = bink.index("bool Submit_Audio_Packet()")
        update = bink.index("void BINKMovie::Update()")
        render = bink.index("void BINKMovie::Render()")
        self.assertLess(video_retry, update)
        self.assertLess(audio_retry, update)
        self.assertLess(bink.index("if (!g_packet_pending)", update), bink.index("g_packet_pending = true;", update))
        self.assertLess(bink.index("if (!packet_consumed)", update), bink.index("av_packet_unref(g_packet);", update))
        self.assertLess(
            bink.index("glActiveTexture(GL_TEXTURE0);", render),
            bink.index("texture0_enabled = glIsEnabled(GL_TEXTURE_2D);", render),
        )
        self.assertLess(
            bink.index("texture0_enabled = glIsEnabled(GL_TEXTURE_2D);", render),
            bink.index("glEnable(GL_TEXTURE_2D);", render),
        )
        self.assertLess(
            bink.index("glBindTexture(GL_TEXTURE_2D, static_cast<GLuint>(previous_texture));", render),
            bink.index("glActiveTexture(static_cast<GLenum>(previous_active_texture));", render),
        )
        self.assertLess(
            bink.index("glBindTexture(GL_TEXTURE_2D, g_video_texture);", render),
            bink.index("RenegadeVitaRenderer::Invalidate_Texture_State_Cache();", render),
        )
        self.assertLess(
            bink.index("glActiveTexture(static_cast<GLenum>(previous_active_texture));", render),
            bink.rindex("RenegadeVitaRenderer::Invalidate_Texture_State_Cache();", render),
        )
        self.assertIn("decoder provider unavailable; original menu route continues", bink)
        self.assertIn("--enable-demuxer=bink", dependency_build)
        self.assertIn("--enable-decoder=bink,binkaudio_dct,binkaudio_rdft", dependency_build)
        self.assertIn("MovieGameModeClass frontend_movie_mode", runtime)
        for token in (
            "A4 frontend: first menu loop frame entry",
            "A4 frontend: first menu loop after TimeManager::Update",
            "A4 frontend: first menu loop after Input::Update",
            "A4 frontend: first menu loop after WWUI key pump",
            "A4 frontend: first menu loop after GameModeManager::Think",
            "A4 frontend: first menu loop after GameModeManager::Render",
            "A4 frontend: first menu loop after WWAudio On_Frame_Update",
        ):
            self.assertIn(token, runtime)
        self.assertIn("frontend_movie_provider_fail_closed", host)
        self.assertIn("Bink movie ownership is implemented", known_gaps)
        self.assertIn("historical dev82 candidate disabled", known_gaps)
        self.assertIn("re-enable the provider", known_gaps)
        self.assertNotIn("realtime movie playback is disabled", known_gaps)
        self.assertIn("empty startup/starvation audio buffer", known_gaps)

    def test_post_intro_main_menu_transition_is_guarded_and_logged(self):
        movie = (ROOT / "staging" / "commando" / "movie.cpp").read_text()
        dialogmgr = (ROOT / "staging" / "commando" / "renegadedialogmgr.cpp").read_text()
        mainmenu = (ROOT / "staging" / "commando" / "dlgmainmenu.cpp").read_text()
        menudialog = (ROOT / "staging" / "wwui" / "menudialog.cpp").read_text()
        backdrop = (ROOT / "staging" / "wwui" / "menubackdrop.cpp").read_text()
        patch = (
            ROOT / "port" / "patches" / "a4-post-movie-mainmenu-hardening.patch"
        ).read_text()

        for source in (movie, patch):
            self.assertIn("A4 MovieGameMode: Movie_Done entry", source)
            self.assertIn("A4 MovieGameMode: stopping current movie audio=%p", source)
            self.assertIn("audio singleton unavailable during movie stop", source)
            self.assertIn("A4 MovieGameMode: routing to main menu location", source)
            self.assertIn("A4 MovieGameMode: dialog route returned", source)
            self.assertLess(
                source.index("Movie_Done entry"),
                source.index("routing to main menu location"),
            )

        for source in (dialogmgr, patch):
            self.assertIn("const bool console_exclusive = ConsoleBox.Is_Exclusive();", source)
            self.assertIn("const bool force_dialog_init = true;", source)
            self.assertIn("if (!console_exclusive || force_dialog_init)", source)
            self.assertIn("DialogMgrClass::Initialize (STYLE_MGR_INI);", source)
            self.assertIn("initialized dialog/menu systems console_exclusive=%d", source)
            self.assertIn("MenuDialogClass::Get_BackDrop ()", source)

        for source in (mainmenu, patch):
            self.assertIn("A4 main menu: Display entry", source)
            self.assertIn("A4 main menu: constructed this=%p", source)
            self.assertIn("A4 main menu: animated backdrop setup", source)
            self.assertIn("A4 main menu: Start_Dialog returned", source)
            self.assertIn("A4 main menu: transition in this=%p", source)
            self.assertIn("A4 main menu: transition out this=%p", source)
            self.assertNotIn("transition in bypassed on Vita", source)
            self.assertNotIn("transition out bypassed on Vita", source)
            self.assertIn("backdrop != NULL ? backdrop->Peek_Scene () : NULL", source)
            self.assertIn("backdrop != NULL ? backdrop->Peek_Camera () : NULL", source)
            self.assertIn("transition in disabled title=%p camera=%p", source)
            self.assertIn("transition out disabled title=%p camera=%p", source)
            self.assertIn("transition->Set_Type (DialogTransitionClass::SCREEN_IN);", source)
            self.assertIn("transition->Set_Type (DialogTransitionClass::SCREEN_OUT);", source)
        self.assertNotIn("Get_BackDrop()->Peek_Scene()->Add_Render_Object", mainmenu)
        self.assertNotIn("dialog->Get_BackDrop ()->Peek_Model ()", mainmenu)

        for source in (menudialog, patch):
            self.assertIn("A4 menu dialog: Initialize backdrop=%p", source)
            self.assertIn("render skipped because backdrop is unavailable", source)
            self.assertIn("if (BackDrop == NULL)", source)

        for source in (backdrop, patch):
            self.assertIn("A4 menu backdrop: constructed this=%p", source)
            self.assertIn("SimpleScene allocation failed", source)
            self.assertIn("Camera allocation failed", source)
            self.assertIn("render skipped scene=%p camera=%p", source)
            self.assertIn("Set_Model name=%s model=%p scene=%p camera=%p", source)
            self.assertIn("if (Scene != NULL)", source)
            self.assertIn("if (camera_bone_index > 0 && Camera != NULL)", source)

    def test_vita_freetype_glyph_load_avoids_hinting_crash_path(self):
        provider = (
            ROOT / "port" / "renderer" / "vita" / "renegade_freetype_font_provider.cpp"
        ).read_text()

        for token in (
            "kVitaFontGlyphLoadFlags",
            "FT_LOAD_NO_HINTING",
            "FT_LOAD_NO_AUTOHINT",
            "FT_Select_Charmap(entry.face, FT_ENCODING_UNICODE)",
            "font->face == nullptr",
            "FT_Load_Char(font->face, character, kVitaFontGlyphLoadFlags)",
        ):
            self.assertIn(token, provider)

        load_glyph = provider[provider.index("bool Load_Glyph"):]
        self.assertNotIn("FT_LOAD_DEFAULT", load_glyph)
        self.assertLess(
            provider.index("FT_Select_Charmap(entry.face, FT_ENCODING_UNICODE)"),
            provider.index("g_faces.push_back(std::move(entry));"),
        )
        self.assertLess(
            provider.index("kVitaFontGlyphLoadFlags"),
            provider.index("FT_Load_Char(font->face, character, kVitaFontGlyphLoadFlags)"),
        )

    def test_vita_fontchars_keeps_the_original_asset_manager_owner(self):
        staged_asset_manager = (ROOT / "staging" / "ww3d2" / "assetmgr.cpp").read_text()
        fontchars_start = staged_asset_manager.index(
            "FontCharsClass *\tWW3DAssetManager::Get_FontChars"
        )
        fontchars_end = staged_asset_manager.index(
            "/***********************************************************************************************",
            fontchars_start + 1,
        )
        fontchars = staged_asset_manager[fontchars_start:fontchars_end]

        self.assertNotIn("return NULL;", fontchars)
        self.assertIn("FontCharsList[i]->Is_Font", fontchars)
        self.assertIn("font->Initialize_GDI_Font( name, point_size, is_bold );", fontchars)
        self.assertIn("FontCharsList.Add( font );", fontchars)


if __name__ == "__main__":
    unittest.main()
