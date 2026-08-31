import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class StageSourcesIncrementalContractTests(unittest.TestCase):
    def test_stage_sources_has_opt_in_content_preserving_mode(self):
        script = (ROOT / "tools" / "stage_sources.sh").read_text(encoding="utf-8")
        self.assertIn("RENEGADE_INCREMENTAL_STAGE", script)
        self.assertIn('mktemp -d "$rv_root/build/staging-incremental.XXXXXX"', script)
        self.assertIn('rv_incremental_temp="$rv_stage"', script)
        self.assertIn('rm -rf -- "$rv_incremental_temp"', script)
        self.assertIn("tools/sync_staged_tree.py", script)
        self.assertIn("--managed-dir", script)
        self.assertRegex(script, re.compile(r"rv_stage_target=.*/staging"))
        self.assertIn("commando-a35-shared-loadingscreen-owner.patch", script)
        self.assertIn("commando-a35-combatgmode-vita-load-finalization.patch", script)
        self.assertIn("commando-a35-loading-status-text.patch", script)
        self.assertIn("commando-a35-loading-status-render.patch", script)
        self.assertIn("wwtranslatedb-a35-empty-string-wide-abi.patch", script)
        self.assertIn("ww3d2-a35-render2d-dynamic-fvf-init.patch", script)
        self.assertIn("ww3d2-a35-render2d-viewport-restore.patch", script)
        self.assertIn("combat-a35-vita-hud-think-presentation.patch", script)
        self.assertIn("combat-a35-vita-messagewindow-presentation.patch", script)
        self.assertIn("combat-a35-weaponview-reload-visible-fallback.patch", script)

    def test_shared_loading_screen_patch_is_durable_staging_input(self):
        patch = (ROOT / "port" / "patches" / "commando-a35-shared-loadingscreen-owner.patch").read_text(encoding="utf-8")
        self.assertIn("+++ b/loadingscreen.cpp", patch)
        self.assertIn("+++ b/loadingscreen.h", patch)
        self.assertIn("#include \"loadingscreen.h\"", patch)
        self.assertIn("Commando_Create_Original_Loading_Screen", patch)
        self.assertIn("WW3D::Begin_Render( true, true", patch)
        self.assertIn("CombatManager::Get_Load_Progress()", patch)

    def test_m00_ui_patch_is_durable_staging_input(self):
        patch = (ROOT / "port" / "patches" / "combat-a35-m00-ui-hud-subtitles.patch").read_text(encoding="utf-8")
        reload_motion = (ROOT / "port" / "patches" / "combat-a35-weaponview-reload-motion.patch").read_text(encoding="utf-8")
        reload_visible = (ROOT / "port" / "patches" / "combat-a35-weaponview-reload-visible-fallback.patch").read_text(encoding="utf-8")
        combatgmode = (ROOT / "port" / "patches" / "commando-a35-combatgmode-vita-load-finalization.patch").read_text(encoding="utf-8")
        hud_think = (ROOT / "port" / "patches" / "combat-a35-vita-hud-think-presentation.patch").read_text(encoding="utf-8")
        message_window = (ROOT / "port" / "patches" / "combat-a35-vita-messagewindow-presentation.patch").read_text(encoding="utf-8")
        render2d_fvf = (ROOT / "port" / "patches" / "ww3d2-a35-render2d-dynamic-fvf-init.patch").read_text(encoding="utf-8")
        render2d_viewport = (ROOT / "port" / "patches" / "ww3d2-a35-render2d-viewport-restore.patch").read_text(encoding="utf-8")
        translatedb_wide = (ROOT / "port" / "patches" / "wwtranslatedb-a35-empty-string-wide-abi.patch").read_text(encoding="utf-8")
        self.assertIn("TextRect.Bottom", patch)
        self.assertIn("display_text = true;", patch)
        self.assertIn("weapon->Get_Can_Snipe()", patch)
        self.assertIn("ReloadAnimationViewTimer", reload_motion)
        self.assertIn("WWMath::Sin(phase * WWMATH_PI)", reload_motion)
        self.assertIn("kVitaReloadViewSeconds", reload_visible)
        self.assertIn("visible reload fallback complete", reload_visible)
        self.assertIn("+\t\tTranslatedStrings.Add (WideStringClass ());", translatedb_wide)
        self.assertNotIn("+\t\tTranslatedStrings.Add (WideStringClass (L\"\"));", translatedb_wide)
        self.assertIn("fi.Get_Normal_Offset()", render2d_fvf)
        self.assertIn("fi.Get_Tex_Offset(1)", render2d_fvf)
        self.assertIn("previous_viewport", render2d_viewport)
        self.assertIn("GetViewport(&previous_viewport)", render2d_viewport)
        self.assertIn("DX8Wrapper::Set_Viewport(&previous_viewport);", render2d_viewport)
        self.assertIn("Vita_Begin_Level_Load", combatgmode)
        self.assertIn("Vita_Finalize_Loaded_Level", combatgmode)
        self.assertIn("GameObjManager::Init_Buildings();", combatgmode)
        self.assertIn("The_Game()->On_Game_Begin();", combatgmode)
        self.assertIn("A31ScopedVitaHUDThinkPresentation", hud_think)
        self.assertIn("HUDClass::Think", hud_think)
        self.assertIn("A31_Vita_Begin_Original_HUD_Render();", hud_think)
        self.assertIn("A31_Vita_End_Original_HUD_Render();", hud_think)
        self.assertIn("A31ScopedVitaMessageWindowPresentation", message_window)
        self.assertIn("MessageWindowClass::On_Frame_Update", message_window)
        self.assertIn("MessageWindowClass::Update_Window_Rectangle", message_window)
        self.assertIn("A31_Vita_Begin_Original_HUD_Render();", message_window)
        self.assertIn("A31_Vita_End_Original_HUD_Render();", message_window)

    def test_fast_candidate_restages_incrementally_by_default(self):
        script = (ROOT / "tools" / "build_fast_candidate.sh").read_text(encoding="utf-8")
        self.assertIn('RENEGADE_INCREMENTAL_STAGE="${RENEGADE_INCREMENTAL_STAGE:-1}"', script)
        self.assertIn('bash "$rv_root/tools/stage_sources.sh"', script)
        self.assertLess(
            script.index('bash "$rv_root/tools/stage_sources.sh"'),
            script.index('echo "Running focused fast contracts..."'),
        )


if __name__ == "__main__":
    unittest.main()
