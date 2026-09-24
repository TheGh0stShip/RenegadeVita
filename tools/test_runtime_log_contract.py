#!/usr/bin/env python3
"""Source-level contract for the candidate runtime evidence lifecycle."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RuntimeLogContractTest(unittest.TestCase):
    def test_session_log_is_append_only_with_profile_scoped_durability(self) -> None:
        source = (ROOT / "port/platform/vita/a30_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        ensure_start = source.index("int Ensure_Runtime_Log_File()")
        write_start = source.index("int Write_Runtime_Log_Line", ensure_start)
        ensure = source[ensure_start:write_start]
        write_end = source.index("int Sync_Runtime_Log_File", write_start)
        write = source[write_start:write_end]
        reset_start = source.index("int A30_Vita_Log_Reset()")
        append_start = source.index("int A30_Vita_Log(const char *format", reset_start)
        reset = source[reset_start:append_start]
        append_end = source.index("int A30_Vita_Log_Flush()", append_start)
        append = source[append_start:append_end]
        flush_end = source.index("bool A30_Vita_Render_Loaded_World", append_end)
        flush = source[append_end:flush_end]
        self.assertIn("SCE_O_APPEND", ensure)
        self.assertIn("gA30RuntimeLogFile >= 0", ensure)
        self.assertIn("sceIoSyncByFd", write)
        self.assertIn("#if RENEGADE_VITA_M00_DEMO", write)
        self.assertNotIn("sceIoClose", write)
        self.assertIn("SCE_O_APPEND", reset)
        self.assertNotIn("SCE_O_TRUNC", reset)
        self.assertIn("[LIFECYCLE] START", reset)
        self.assertIn("Sync_Runtime_Log_File", reset)
        self.assertIn("Write_Runtime_Log_Line", append)
        self.assertIn("char line[2048]", append)
        self.assertNotIn("SCE_O_TRUNC", append)
        self.assertIn("int A30_Vita_Log_Flush()", flush)
        self.assertIn("Sync_Runtime_Log_File", flush)

    def test_campaign_log_flushes_after_checkpoint_and_terminal_records(self) -> None:
        interactive = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text(
            encoding="utf-8"
        )
        checkpoint = interactive.index('A35_Campaign_Flight_Flush("checkpoint")')
        fatal = interactive.index('A35_Campaign_Flight_Flush("best-effort-fatal-snapshot")')
        final = interactive.index('A35_Campaign_Flight_Flush("final")')
        self.assertIn("A30_Vita_Log_Flush();", interactive[checkpoint:checkpoint + 150])
        self.assertIn("A30_Vita_Log_Flush();", interactive[fatal:fatal + 150])
        self.assertIn("A30_Vita_Log_Flush();", interactive[final:final + 100])

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
        self.assertIn("#include <atomic>", interactive)
        self.assertIn("void Flush_Debug_Status(unsigned frames)", interactive)
        self.assertIn("sceDisplayWaitVblankStart();", interactive)
        self.assertIn("kStartupStatusRepaintIntervalUs = 250000U", interactive)
        self.assertIn("std::atomic<int> g_startup_status_repaint_active(0)", interactive)
        self.assertIn("class A31ScopedStartupStatusRepaint", interactive)
        self.assertIn("Startup_Status_Repaint_Thread", interactive)
        self.assertIn("Set_Startup_Status_Repaint_Phase", interactive)
        self.assertIn("verbose status repaint started before_vitagl=1", interactive)
        self.assertIn("verbose status repaint active tick=%u", interactive)
        self.assertIn("visible-startup-precache-begin", interactive)
        self.assertIn("void Draw_Engine_Setup_Screen", interactive)
        self.assertIn("Original engine setup / frontend handoff", interactive)
        self.assertIn("This screen stays active until vitaGL owns display.", interactive)
        self.assertIn("visible status remains until vitaGL replaces the framebuffer", interactive)
        self.assertIn("retaining bootstrap framebuffer through WW3D::Init", interactive)
        self.assertLess(
            interactive.index("Run_Visible_Startup_Precache_Phase("),
            interactive.index('"Starting original audio provider"'),
        )
        self.assertLess(
            interactive.index('"Starting vitaGL renderer"'),
            interactive.index("ww3d_initialized = WW3D::Init(NULL, NULL, true)"),
        )
        self.assertNotIn("psvDebugScreenFinish();", interactive)
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
