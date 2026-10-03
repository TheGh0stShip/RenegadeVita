import re
import unittest
from pathlib import Path

from tools.check_m13_script_coverage import selected_owners


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream" / "CnC_Renegade" / "Code"


class ScriptProviderContractTests(unittest.TestCase):
    def test_callback_abi_headers_are_identical(self):
        for name in (
            "scriptcommands.h",
            "scriptevents.h",
            "actionparams.h",
            "gameobjobserver.h",
            "combatsound.h",
        ):
            combat = (UPSTREAM / "Combat" / name).read_bytes()
            provider = (UPSTREAM / "Scripts" / name).read_bytes()
            self.assertEqual(combat, provider, name)

    def test_mission00_translation_unit_is_the_exact_tutorial_registration_set(self):
        source = (UPSTREAM / "Scripts" / "Mission00.cpp").read_text(
            encoding="utf-8", errors="strict"
        )
        registered = re.findall(
            r"DECLARE_SCRIPT\s*\(\s*([A-Za-z_][A-Za-z_0-9]*)\s*,", source
        )
        self.assertEqual(
            registered,
            [
                "MTU_Tutorial_Controller",
                "MTU_Tutorial_Instructor",
                "MTU_Trigger_Zone",
                "MTU_GDI_Soldier",
                "MTU_Commando",
                "MTU_Commando_Startup",
                "MTU_PowerUp_Health",
                "MTU_PowerUp_Armor",
                "MTU_Nod_Apache",
                "MTU_Range_Target",
                "MTU_Range_Target_Path_Mid",
                "MTU_Range_Target_Path_Right",
                "MTU_Range_Target_Path_Left",
                "MTU_Range_Target_Miss_Commando",
                "MTU_Range_Powerup",
                "MTU_GDI_Vehicle",
                "MTU_Building_Controller",
                "MTU_Nod_Soldier",
                "MTU_Flyover",
                "MSK_Controller",
                "MSK_Soldier",
                "MSK_Info_Zone",
            ],
        )

    def test_provider_closes_all_literal_mission00_script_attachments(self):
        mission = (UPSTREAM / "Scripts" / "Mission00.cpp").read_text(
            encoding="utf-8", errors="strict"
        )
        attached = set(
            re.findall(
                r'Attach_Script\s*\([^,]+,\s*"([A-Za-z_][A-Za-z_0-9]*)"',
                mission,
            )
        )
        provider_sources = {
            "Mission00.cpp",
            "Test_Cinematic.cpp",
            "Toolkit_Powerup.cpp",
        }
        registered = set()
        for source_name in provider_sources:
            source = (UPSTREAM / "Scripts" / source_name).read_text(
                encoding="utf-8", errors="strict"
            )
            registered.update(
                re.findall(
                    r"DECLARE_SCRIPT\s*\(\s*([A-Za-z_][A-Za-z_0-9]*)\s*,",
                    source,
                )
            )
        self.assertEqual(set(), attached - registered)
        self.assertIn("Test_Cinematic", registered)
        self.assertIn("M00_Soldier_Powerup_Disable", registered)

    def test_static_binding_preserves_original_registrar_and_command_table(self):
        adapter = (
            ROOT / "port" / "platform" / "renegade_script_static_provider.cpp"
        ).read_text(encoding="utf-8")
        combat_patch = (
            ROOT / "port" / "patches" / "combat-a31-script-dll-boundary.patch"
        ).read_text(encoding="utf-8")
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        original_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "cmake").glob("A*OriginalSources.cmake"))
        )
        self.assertIn("ScriptRegistrar::CreateScript(name)", adapter)
        self.assertIn("Commands = commands->Commands", adapter)
        self.assertIn("Get_Script_Commands()", combat_patch)
        self.assertIn("Set_Script_Commands(&commands)", combat_patch)
        self.assertIn("ScriptCreateFunct = &::Create_Script", combat_patch)
        for target, owners in selected_owners(ROOT).items():
            self.assertTrue({"Mission00.cpp", "Test_Cinematic.cpp", "Toolkit_Powerup.cpp",
                             "Mission01.cpp", "MissionX0.cpp", "Test_DLS.cpp", "strtrim.cpp"}
                            <= owners, target)
        self.assertIn("${RENEGADE_STAGE}/wwlib/trim.cpp", original_sources)
        self.assertIn("${RENEGADE_SCRIPT_SOURCE}/Mission01.cpp", cmake)
        self.assertIn("${RENEGADE_SCRIPT_SOURCE}/MissionX0.cpp", cmake)
        self.assertIn("${RENEGADE_STAGE}/combat/cinematicgameobj.cpp", cmake)
        self.assertRegex(
            cmake,
            r"list\(APPEND RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCES[^)]*"
            r"\$\{RENEGADE_SCRIPT_DSP_SOURCES\}\s*"
            r"\$\{RENEGADE_STAGE\}/combat/cinematicgameobj\.cpp",
        )

    def test_gcc_default_argument_bridge_is_callsite_only(self):
        bridge = (
            ROOT
            / "port"
            / "compatibility"
            / "include"
            / "renegade_script_call_defaults.h"
        ).read_text(encoding="utf-8")
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn("original script translation units", bridge)
        blocks = re.findall(r"set_property\(SOURCE\s+([^)]*)\)", cmake)
        shared = [block for block in blocks
                  if 'renegade_script_call_defaults.h' in block]
        self.assertEqual(len(shared), 1)
        self.assertIn("${RENEGADE_SCRIPT_DSP_SOURCES}", shared[0])
        for target, owners in selected_owners(ROOT).items():
            self.assertTrue({"MissionX0.cpp", "Test_DLS.cpp", "Toolkit.cpp", "Toolkit_Objects.cpp",
                             "Mission03.cpp", "Mission11.cpp", "Test_DAK.cpp",
                             "Test_RMV_Toolkit.cpp", "Toolkit_Sounds.cpp"} <= owners, target)
        area2 = [block for block in blocks
                 if 'renegade_m13_area2_script_defaults.h' in block]
        self.assertEqual(len(area2), 1)
        self.assertIn("${RENEGADE_SCRIPT_SOURCE}/Test_RAD.cpp", area2[0])
        self.assertIn(
            "Create_Explosion_At_Bone(explosion, object, bone, NULL)", bridge
        )
        self.assertIn("Create_Conversation(name, 0, 0.0F, true)", bridge)
        self.assertIn("Enable_Enemy_Seen(object, true)", bridge)
        self.assertIn("Give_PowerUp(object, preset, false)", bridge)
        self.assertIn("Send_Custom_Event(from, to, type, param, 0.0F)", bridge)
        self.assertIn(
            "Join_Conversation(object, conversation, allow_move, allow_head_turn, true)",
            bridge,
        )
        self.assertIn("Apply_Damage(object, amount, warhead, NULL)", bridge)
        self.assertIn(
            "Set_Animation(object, animation, looping, sub_object, start_frame, end_frame, false)",
            bridge,
        )
        self.assertIn(
            "RENEGADE_SCRIPT_SET_ANIMATION_2(animation, looping)", bridge
        )

    def test_original_scripts_are_staged_and_array_freed_symmetrically(self):
        stage = (ROOT / "tools" / "stage_sources.sh").read_text(encoding="utf-8")
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        patch = (
            ROOT / "port" / "patches" / "scripts-a35-parameter-array-delete.patch"
        ).read_text(encoding="utf-8")
        self.assertIn('$rv_stage/scripts', stage)
        self.assertIn('scripts-a35-parameter-array-delete.patch', stage)
        self.assertIn('set(RENEGADE_SCRIPT_SOURCE "${RENEGADE_STAGE}/scripts")', cmake)
        self.assertIn("delete[] mArgV", patch)
        staged_source = (ROOT / "staging" / "scripts" / "scripts.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("delete[] mArgV", staged_source)
        self.assertNotIn("delete (void*)mArgV", staged_source)


if __name__ == "__main__":
    unittest.main()
