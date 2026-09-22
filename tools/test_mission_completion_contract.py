#!/usr/bin/env python3
"""Focused ownership contract for the direct-M00 completion transition."""

from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MissionCompletionContractTests(unittest.TestCase):
    def test_dependency_free_latch_preserves_first_terminal_result(self) -> None:
        source = textwrap.dedent(
            r"""
            #include <cassert>
            #include "port/platform/a31_mission_completion_latch.h"

            int main() {
                A31MissionCompletionLatch latch;
                A31MissionCompletionState state = latch.State();
                assert(!state.completion_observed);
                assert(!state.mission_succeeded);
                assert(!state.star_killed_observed);

                latch.Mission_Complete(true);
                latch.Mission_Complete(false);
                state = latch.State();
                assert(state.completion_observed);
                assert(state.mission_succeeded);
                assert(!state.star_killed_observed);

                latch.Reset();
                latch.Mission_Complete(false);
                latch.Star_Killed();
                state = latch.State();
                assert(state.completion_observed);
                assert(!state.mission_succeeded);
                assert(state.star_killed_observed);
                return 0;
            }
            """
        )
        with tempfile.TemporaryDirectory(prefix="renegade-mission-latch-") as tmp:
            test_cpp = Path(tmp) / "mission_latch_test.cpp"
            executable = Path(tmp) / "mission_latch_test"
            test_cpp.write_text(source, encoding="utf-8")
            subprocess.run(
                [
                    "g++",
                    "-std=c++11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(ROOT),
                    str(test_cpp),
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            subprocess.run([str(executable)], check=True)

    def test_vita_adapter_uses_original_combat_misc_handler_seam(self) -> None:
        boundary = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "class A31VitaCombatMiscHandler final : public CombatMiscHandlerClass",
            boundary,
        )
        self.assertIn(
            "CombatManager::Set_Combat_Misc_Handler(&g_vita_combat_misc_handler)",
            boundary,
        )
        self.assertIn("CombatManager::Set_Combat_Misc_Handler(NULL)", boundary)
        self.assertNotIn("CombatManager::Mission_Complete(", boundary)
        self.assertNotIn("Commands->Mission_Complete", boundary)
        self.assertNotIn("PendingCampaignContinue", boundary)

    def test_runtime_observes_callback_after_original_simulation(self) -> None:
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        simulation = runtime.index("A31_Interactive_Run_Simulation_Frame();")
        observation = runtime.index(
            "A31_Interactive_Get_Mission_Completion_State();", simulation
        )
        self.assertGreater(observation, simulation)
        self.assertIn(
            "original Combat event observed success=%d frame=%u", runtime
        )
        self.assertIn(
            "result.mission_completion_observed && result.mission_succeeded",
            runtime,
        )
        diagnostic_guard = (
            "#if !RENEGADE_VITA_M00_DEMO && "
            "RENEGADE_VITA_DEVELOPMENT_CHECKPOINT\n"
        )
        diagnostic_call = runtime.index("CombatManager::Mission_Complete(true);", simulation)
        diagnostic_start = runtime.rindex(diagnostic_guard, simulation, diagnostic_call)
        diagnostic_end = runtime.index("#endif", diagnostic_start) + len("#endif")
        diagnostic_only = runtime[diagnostic_start:diagnostic_end]
        self.assertIn("CombatManager::Mission_Complete(true);", diagnostic_only)
        normal_runtime = runtime[:diagnostic_start] + runtime[diagnostic_end:]
        self.assertNotIn("CombatManager::Mission_Complete(", normal_runtime)
        self.assertNotIn("Commands->Mission_Complete", runtime)

    def test_process_success_requires_orderly_original_runtime_exit(self) -> None:
        main = (ROOT / "port/platform/vita/a30_main.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("const bool gameplay_ok = interactive.attempted", main)
        self.assertIn("runtime_ok = gameplay_ok || (interactive.frontend_exit_requested", main)
        self.assertIn("interactive.clean_exit_requested", main)
        self.assertIn("interactive.teardown_completed", main)
        self.assertIn("const int exit_code = runtime_ok ? 0 : 1", main)

    def test_progress_flight_recorder_is_read_only_and_control_gated(self) -> None:
        boundary = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text(
            encoding="utf-8"
        )
        progress = boundary.split(
            "A31MissionProgressState A31_Interactive_Get_Mission_Progress_State()",
            1,
        )[1].split("void A31_Interactive_Run_Simulation_Frame()", 1)[0]
        self.assertIn("ObjectiveManager::Get_Objective_Count()", progress)
        self.assertIn("ObjectiveManager::Get_Objective(index)", progress)
        self.assertIn("star->Is_Control_Enabled()", progress)
        self.assertIn("ConversationMgrClass::Get_Active_Conversation_Count()", progress)
        for mutation in (
            "Set_Objective_Status",
            "Add_Objective",
            "->Control_Enable(",
            "Start_Conversation",
            "Mission_Complete",
        ):
            self.assertNotIn(mutation, progress)

        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "original player control available for route activation", runtime
        )
        control_gate = runtime.split(
            "if (!tutorial_control_ready_observed", 1
        )[1].split("}", 1)[0]
        self.assertIn("mission_progress.player_control_enabled", control_gate)
        self.assertNotIn("mission_progress.objective_status[0] == 0", control_gate)


if __name__ == "__main__":
    unittest.main()
