#!/usr/bin/env python3
"""Source-level contract for the candidate runtime evidence lifecycle."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RuntimeLogContractTest(unittest.TestCase):
    def test_session_log_is_append_only_and_durable(self) -> None:
        source = (ROOT / "port/platform/vita/a30_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        reset_start = source.index("int A30_Vita_Log_Reset()")
        append_start = source.index("int A30_Vita_Log(const char *format", reset_start)
        reset = source[reset_start:append_start]
        append_end = source.index("bool A30_Vita_Render_Loaded_World", append_start)
        append = source[append_start:append_end]
        self.assertIn("SCE_O_APPEND", reset)
        self.assertNotIn("SCE_O_TRUNC", reset)
        self.assertIn("[LIFECYCLE] START", reset)
        self.assertIn("sceIoSyncByFd", reset)
        self.assertIn("SCE_O_APPEND", append)
        self.assertIn("sceIoSyncByFd", append)
        self.assertIn("sceIoClose", append)

    def test_runtime_phases_have_durable_breadcrumbs(self) -> None:
        main = (ROOT / "port/platform/vita/a30_main.cpp").read_text(encoding="utf-8")
        world = (ROOT / "port/platform/vita/a30_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        interactive = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("Runtime identity: candidate=%s display=%s path=%s", main)
        self.assertIn("#include <psp2/display.h>", main)
        self.assertIn("void Flush_Bootstrap_Display(unsigned frames)", main)
        self.assertIn("void Hold_Bootstrap_Display(unsigned milliseconds)", main)
        self.assertIn("sceDisplayWaitVblankStart();", main)
        self.assertIn("void Print_Bootstrap_Progress(int screen_result)", main)
        self.assertIn("Starting native Vita runtime...", main)
        self.assertIn("visible bootstrap status precedes retail pre-cache", main)
        self.assertLess(
            main.index("Print_Bootstrap_Progress(screen_result);"),
            main.index("Vita_Initialize_Filesystem();"),
        )
        self.assertLess(
            main.index("Hold_Bootstrap_Display(250U);"),
            main.index("Vita_Initialize_Filesystem();"),
        )
        self.assertIn("Stage: loaded-world callback entry", world)
        self.assertIn("#include <psp2/display.h>", interactive)
        self.assertIn("void Flush_Debug_Status(unsigned frames)", interactive)
        self.assertIn("sceDisplayWaitVblankStart();", interactive)
        self.assertIn("void Draw_Engine_Setup_Screen", interactive)
        self.assertIn("Original engine setup / frontend handoff", interactive)
        self.assertIn("This screen stays active until vitaGL owns display.", interactive)
        self.assertLess(
            interactive.index("Run_Visible_Startup_Precache_Phase("),
            interactive.index('"Starting original audio provider"'),
        )
        self.assertLess(
            interactive.index('"Starting vitaGL renderer"'),
            interactive.index("psvDebugScreenFinish();"),
        )
        self.assertLess(
            interactive.index("psvDebugScreenFinish();"),
            interactive.index("ww3d_initialized = WW3D::Init(NULL, NULL, true)"),
        )
        self.assertIn("first original Combat update", interactive)
        self.assertNotIn("first-interactive-player-frame", interactive)
        self.assertNotIn("first_interactive_capture_pending", interactive)
        self.assertIn("automatic first-frame screenshot disabled", interactive)
        self.assertIn("const bool requested_capture_ready =", interactive)
        self.assertIn("mission_progress.player_control_enabled", interactive)
        self.assertIn("render_trace.post_render_completed", interactive)
        self.assertIn("reason=manual-select-visible-gameplay", interactive)
        self.assertIn("encode that SELECT edge at the fixed checkpoint", interactive)
        self.assertIn("reason=pre-clean-exit", interactive)
        self.assertIn("reason=best-effort-fatal-snapshot", interactive)
        self.assertIn("[LIFECYCLE] END status=clean", main)


if __name__ == "__main__":
    unittest.main()
