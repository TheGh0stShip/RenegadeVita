import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class A4OriginalFrontendContractTests(unittest.TestCase):
    def test_cmake_selects_original_frontend_and_boundary_sources(self):
        cmake = (ROOT / "CMakeLists.txt").read_text()
        host_cmake = (ROOT / "tools" / "host_a30_definitions" / "CMakeLists.txt").read_text()

        self.assertIn("option(RENEGADE_A4_ORIGINAL_FRONTEND", cmake)
        for token in (
            "--rc",
            "--resource-h",
            "--dialog-resource-h",
            "--out",
        ):
            self.assertIn(token, cmake)
        for stale_token in (
            "--resource-script",
            "--resource-header",
            "--dialogresource-header",
            "--output",
        ):
            self.assertNotIn(stale_token, cmake)

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
            "${RENEGADE_STAGE}/commando/radiocommanddisplay.cpp",
            "${RENEGADE_STAGE}/commando/commandosaveload.cpp",
            "${RENEGADE_STAGE}/commando/loadingevent.cpp",
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
        self.assertIn("${RV_STAGE}/commando/loadingscreen.cpp", host_cmake)
        self.assertIn("${RV_STAGE}/commando/radiocommanddisplay.cpp", host_cmake)
        self.assertIn("${RV_STAGE}/commando/commandosaveload.cpp", host_cmake)
        self.assertIn("${RV_STAGE}/commando/loadingevent.cpp", host_cmake)
        self.assertIn("${RV_ROOT}/port/platform/a4_binkmovie_boundary.cpp", host_cmake)
        lifecycle = (ROOT / "port" / "platform" / "a4_frontend_lifecycle_boundary.cpp").read_text()
        network_boundary = (ROOT / "port" / "platform" / "a31_network_options_boundary.cpp").read_text()
        renderer_boundary = (ROOT / "port" / "renderer" / "vita" / "ww3d_dx8_boundary.cpp").read_text()
        self.assertIn("WWAudioClass::Temp_Disable_Audio", lifecycle)
        self.assertIn("CNCServerInfoDialogClass::CNCServerInfoDialogClass", lifecycle)
        self.assertIn("MPIngameChatPopupClass::MPIngameChatPopupClass", lifecycle)
        self.assertIn("CSAnnouncement::CSAnnouncement", lifecycle)
        self.assertIn("void cDiagnostics::Render(void) {}", lifecycle)
        self.assertIn("void DX8RendererDebugger::Update(void) {}", lifecycle)
        self.assertIn("void cBandwidthGraph::Render(void) {}", network_boundary)
        self.assertIn("bool DX8Wrapper::_EnableTriangleDraw = true;", renderer_boundary)
        self.assertIn("bool SortingRendererClass::_EnableTriangleDraw = true;", renderer_boundary)

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
            "Set_Button(DIKeyboardButtons, DIK_UP, (buttons & SCE_CTRL_UP) != 0);",
            "Set_Button(DIKeyboardButtons, DIK_DOWN, (buttons & SCE_CTRL_DOWN) != 0);",
            "Set_Button(DIKeyboardButtons, DIK_LEFT, (buttons & SCE_CTRL_LEFT) != 0);",
            "Set_Button(DIKeyboardButtons, DIK_RIGHT, (buttons & SCE_CTRL_RIGHT) != 0);",
            "Set_Button(DIKeyboardButtons, DIK_E, (buttons & SCE_CTRL_TRIANGLE) != 0);",
            "Set_Button(DIKeyboardButtons, DIK_R, (buttons & SCE_CTRL_SQUARE) != 0);",
        ):
            self.assertIn(token, directinput)

        self.assertIn("A4_Frontend_Pump_WWUI_Key_Transitions", header)
        self.assertIn("g_frontend_key_dispatcher.ProcessMessage(NULL, message", lifecycle)
        self.assertIn("WM_KEYDOWN", lifecycle)
        self.assertIn("WM_KEYUP", lifecycle)
        self.assertIn("D-pad navigates the original WWUI focus", controls_doc)

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
        self.assertIn("registered original CombatGameMode owner", runtime)
        self.assertIn("StyleMgrClass::Initialize_From_INI(kStyleManagerIni);", runtime[handoff_index:direct_route_index])
        self.assertIn("A4_Frontend_Latch_Start_Game", gameinit)
        self.assertIn("Validate_Frontend_Tutorial_Start_Latch", host)
        self.assertIn("frontend_tutorial_start_latched", host)
        self.assertIn("frontend_tutorial_latched_map", host)

    def test_intro_movie_provider_uses_original_movie_owner_and_fails_closed(self):
        movie = (ROOT / "staging" / "commando" / "movie.cpp").read_text()
        bink = (ROOT / "port" / "platform" / "a4_binkmovie_boundary.cpp").read_text()
        runtime = (ROOT / "port" / "platform" / "vita" / "a31_vita_runtime.cpp").read_text()
        host = (ROOT / "tools" / "host_a30_definitions" / "a31_interactive_main.cpp").read_text()
        known_gaps = (ROOT / "reports" / "KNOWN_GAPS.md").read_text()

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
        self.assertIn("decoder provider unavailable; original menu route continues", bink)
        self.assertIn("MovieGameModeClass frontend_movie_mode", runtime)
        self.assertIn("frontend_movie_provider_fail_closed", host)
        self.assertIn("Bink movie decode/playback remains fail-closed", known_gaps)


if __name__ == "__main__":
    unittest.main()
