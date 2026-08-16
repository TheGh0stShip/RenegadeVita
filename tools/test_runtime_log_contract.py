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
        self.assertIn("Stage: loaded-world callback entry", world)
        self.assertIn("first original Combat update", interactive)
        self.assertIn("reason=first-interactive-player-frame", interactive)
        self.assertIn("reason=pre-clean-exit", interactive)
        self.assertIn("reason=best-effort-fatal-snapshot", interactive)
        self.assertIn("[LIFECYCLE] END status=clean", main)


if __name__ == "__main__":
    unittest.main()
