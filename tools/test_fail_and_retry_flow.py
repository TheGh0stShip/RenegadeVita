#!/usr/bin/env python3
"""Source contract for the campaign fail-and-retry flow (host only, no build).

Pins the invariants documented in reports/campaign/FAIL_AND_RETRY_FLOW.md:
the failure/death popups always give a way forward, and nothing the original
scripts can latch process-wide survives an in-session restart.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "port/platform/vita/a31_vita_runtime.cpp"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8", errors="replace")


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace : index + 1]
    raise AssertionError("unterminated function: " + signature)


class TimeScaleDoesNotLeakIntoRestartTests(unittest.TestCase):
    def test_original_boss_sequence_is_the_only_slow_motion_owner(self) -> None:
        # Premise: the original sets a process-global TimeScale that neither
        # Core_Shutdown nor Load_Level restores, so the Vita boundary must.
        mendoza = read("staging/combat/mendozabossgameobj.cpp")
        self.assertIn("TimeManager::Set_Time_Scale (0.25F)", mendoza)
        self.assertIn("TimeManager::Set_Time_Scale (0.5F)", mendoza)
        for path in ("staging/commando/combatgmode.cpp", "staging/combat/combat.cpp",
                     "staging/commando/level.cpp", "staging/commando/god.cpp"):
            self.assertNotIn("Set_Time_Scale", read(path), path)

    def test_death_popup_pump_resets_scale_but_eva_pause_keeps_it(self) -> None:
        body = function_body(RUNTIME.read_text(encoding="utf-8"),
                             "bool Run_Original_Gameplay_Pause_Menu(")
        self.assertIn("if (death_dialog) TimeManager::Set_Time_Scale(1.0F);", body)
        # The EVA pause resumes the same world, so it must not reset the scale
        # unconditionally.
        self.assertEqual(body.count("Set_Time_Scale"), 1)
        # Reset happens before the first TimeManager::Update of the pump.
        self.assertLess(body.index("Set_Time_Scale"), body.index("TimeManager::Update()"))

    def test_campaign_restart_resets_scale_before_original_restart(self) -> None:
        source = RUNTIME.read_text(encoding="utf-8")
        match = re.search(
            r"if \(campaign_restart\) \{\s*//[^\n]*\n\s*//[^\n]*\n"
            r"\s*TimeManager::Set_Time_Scale\(1\.0F\);\s*cGod::Restart\(\);", source)
        self.assertIsNotNone(match, "restart must reset TimeScale right before cGod::Restart")

    def test_every_session_still_starts_at_normal_speed(self) -> None:
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("TimeManager::Set_Time_Scale(1.0F);", source)


class RestartOwnershipTests(unittest.TestCase):
    def test_restart_is_only_requested_by_the_two_original_popups(self) -> None:
        # Both popups pass through the death-dialog pump, which now owns the
        # TimeScale reset; any new requester must route through it as well.
        callers = []
        for path in (ROOT / "staging").rglob("*.cpp"):
            text = path.read_text(encoding="utf-8", errors="replace")
            callers += [path.name for _ in re.finditer(r"(?<!void )cGod::Request_Restart\s*\(", text)]
        self.assertEqual(sorted(callers), ["dialogtests.cpp", "dialogtests.cpp"])

    def test_failed_popup_ignores_cancel_and_death_popup_quits(self) -> None:
        dialogs = read("staging/commando/dialogtests.cpp")
        failed = dialogs[dialogs.index("FailedOptionsPopupClass::On_Command"):]
        failed = failed[: failed.index("PopupDialogClass::On_Command")]
        self.assertRegex(failed, r"case IDCANCEL:\s*allow_default_processing = false;")
        death = dialogs[dialogs.index("DeathOptionsPopupClass::On_Command"):]
        death = death[: death.index("FailedOptionsPopupClass::On_Init_Dialog")]
        self.assertRegex(death, r"case IDCANCEL:\s*case IDC_DEATH_OPTION_QUIT:")
        self.assertIn("GameInitMgrClass::Set_Needs_Game_Exit(true);", death)

    def test_load_keeps_combat_suspended_so_the_pump_hands_off_the_load_menu(self) -> None:
        god = read("staging/commando/god.cpp")
        load = god[god.index("void cGod::Load_Game"):]
        load = load[: load.index("void cGod::Mission_Failed")]
        self.assertIn("combat_mode->Suspend()", load)
        self.assertIn("LOC_LOAD_GAME", load)


class NoStaleStateAcrossRestartTests(unittest.TestCase):
    def test_level_load_resets_presentation_state(self) -> None:
        combat = read("staging/combat/combat.cpp")
        pre = function_body(combat, "void	CombatManager::Pre_Load_Level(")
        for needle in ("HUDClass::Enable( true )", "HUDClass::Reset()",
                       "IsGamePaused = false", "ScreenFadeManager::Enable_Letterbox( 0, 0 )",
                       "ScreenFadeManager::Set_Screen_Overlay_Opacity( 0, 0 )",
                       "SmartGameObj::Set_Global_Sight_Range_Scale( 1.0f )"):
            self.assertIn(needle, pre)
        unload = function_body(combat, "void	CombatManager::Unload_Level(")
        self.assertIn("MainCamera->Set_Host_Model(NULL)", unload)
        self.assertIn("GameObjManager::Activate_Cinematic_Freeze(false)", unload)
        self.assertIn("HitReticleEnabled", combat)

    def test_host_release_clears_cinematic_sniper_and_conversations_reset(self) -> None:
        camera = read("staging/combat/ccamera.cpp")
        self.assertIn("CinematicSnipingEnabled = false;\n\t\tCinematicSnipingDesiredZoom = 0;", camera)
        level = read("staging/commando/level.cpp")
        self.assertIn("ConversationMgrClass::Reset_Active_Conversations ()", level)
        self.assertIn("TransitionManager::Reset()", level)

    def test_load_level_discards_pending_success_and_rearms_the_latch(self) -> None:
        gmode = read("staging/commando/combatgmode.cpp")
        self.assertIn("PendingCampaignContinue	= false;", gmode)
        self.assertIn("A31_Interactive_Restart_Mission_Completion_Observation()", gmode)

    def test_autosave_request_defers_while_dead_and_dies_with_the_session(self) -> None:
        gmode = read("staging/commando/combatgmode.cpp")
        body = function_body(gmode, "void CombatGameModeClass::Process_Autosave_Request()")
        gate = body.index("cGod::Can_Save_Current_State()")
        self.assertLess(gate, body.index("Request_Autosave( false )"))
        self.assertIn("return;", body[gate:body.index("Request_Autosave( false )")])
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("cleared unconsumed autosave request at session end", runtime)


class DeathDialogAlwaysHasAWayForwardTests(unittest.TestCase):
    def test_pump_cannot_end_with_combat_suspended_and_no_exit(self) -> None:
        body = function_body(RUNTIME.read_text(encoding="utf-8"),
                             "bool Run_Original_Gameplay_Pause_Menu(")
        # Cancelled load menu after death returns to the menu, never a dead world.
        self.assertRegex(body, r"death_dialog && combat_mode->Is_Suspended\(\) && !exit_requested &&\s*"
                               r"!reload_requested && !cGod::Has_Pending_Restart\(\) &&\s*"
                               r"DialogMgrClass::Get_Dialog_Count\(\) == 0")
        self.assertIn("GameInitMgrClass::Set_Needs_Game_Exit(true);", body)
        self.assertIn("GameInitMgrClass::Continue_Game();", body)

    def test_main_loop_ends_session_or_defers_to_pending_owner_after_the_popup(self) -> None:
        source = RUNTIME.read_text(encoding="utf-8")
        marker = "A4 death: original popup active dialogs"
        branch = source[source.index(marker):]
        branch = branch[: branch.index("A4 death: deferred original exit/restart pending")]
        self.assertIn("original popup closed without active Combat; ending session", branch)
        self.assertRegex(branch, r"!GameInitMgrClass::Has_Pending_Game_Exit\(\) && "
                                 r"!cGod::Has_Pending_Restart\(\)")
        self.assertIn("GameInitMgrClass::Set_Needs_Game_Exit(true);", branch)

    def test_popups_are_navigable_with_vita_buttons(self) -> None:
        directinput = read("port/platform/renegade_directinput.cpp")
        for needle in (
            "dialog_navigation && (buttons & SCE_CTRL_UP) != 0",
            "dialog_navigation && (buttons & SCE_CTRL_DOWN) != 0",
            "Set_Virtual_Key(VK_RETURN, (buttons & SCE_CTRL_CROSS) != 0)",
            "Set_Virtual_Key(VK_ESCAPE, (buttons & SCE_CTRL_CIRCLE) != 0)",
            "DialogMgrClass::Get_Dialog_Count() != 0",
        ):
            self.assertIn(needle, directinput)
        # Held buttons at the moment the popup opens must not select an option.
        pump = function_body(RUNTIME.read_text(encoding="utf-8"),
                             "bool Run_Original_Gameplay_Pause_Menu(")
        self.assertLess(pump.index("A4_Frontend_Prime_WWUI_Key_Transitions()"),
                        pump.index("menu_mode.Think()"))


if __name__ == "__main__":
    unittest.main()
