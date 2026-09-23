"""Execute the actual application handoff loop with bounded session doubles."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DemoMenuReturnTests(unittest.TestCase):
    def test_completed_session_returns_but_failure_does_not(self):
        source = (ROOT / "port/platform/vita/a30_main.cpp").read_text()
        loop = source.split("\tA31VitaInteractiveResult interactive = {};", 1)[1]
        loop = "A31VitaInteractiveResult interactive = {};" + loop.split("\tif (runtime_ok) {", 1)[0]
        program = r'''
#include "a31_vita_runtime.h"
#include <cassert>
#include <cstdarg>
#include <cstddef>
#include <cstring>
#include <limits>
struct WWAudioClass { static WWAudioClass *Get_Instance() { return nullptr; } };
void A30_Vita_Log(const char *, ...) {}
int mode, calls;
A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime(
    int, bool menu, const char *reload, const char *campaign_source,
    const uint8_t *campaign_state, uint32_t campaign_state_size) {
    assert(calls < 3);
    assert(menu == (calls > 0));
    assert(campaign_source == nullptr);
    assert(campaign_state == nullptr);
    assert(campaign_state_size == 0);
    if (calls == 0) assert(reload == nullptr);
    else if (mode >= 3) assert(reload && strcmp(reload, "save/manual.sav") == 0);
    else assert(reload == nullptr);
    A31VitaInteractiveResult r = {};
    if (calls++ == 0) {
        r.attempted = r.initialized = r.transport_established = r.level_loaded = true;
        r.player_created = r.player_registered = r.commando_created = true;
        r.first_frame_completed = r.first_frame_geometry = r.clean_exit_requested = true;
        r.mission_completion_observed = r.mission_succeeded = true;
        r.return_to_menu_requested = true;
        r.teardown_completed = mode != 1;
        r.render_error = mode == 2;
        if (mode >= 3) {
            r.mission_completion_observed = r.mission_succeeded = false;
            r.return_to_menu_requested = false;
            strcpy(r.reload_source, "save/manual.sav");
            r.teardown_completed = mode != 4;
        }
    } else {
        r.frontend_exit_requested = r.clean_exit_requested = r.teardown_completed = true;
    }
    return r;
}
bool run() {
    int screen_result = 0;
    LOOP
    return runtime_ok;
}
int main() {
    mode = 0; calls = 0; assert(run() && calls == 2);
    mode = 1; calls = 0; assert(!run() && calls == 1);
    mode = 2; calls = 0; assert(!run() && calls == 1);
    mode = 3; calls = 0; assert(run() && calls == 2);
    mode = 4; calls = 0; assert(!run() && calls == 1);
}
'''.replace("LOOP", loop)
        with tempfile.TemporaryDirectory(prefix="demo-menu-return-") as folder:
            cpp, exe = Path(folder) / "test.cpp", Path(folder) / "test"
            cpp.write_text(program)
            result = subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                                     "-I", str(ROOT / "port/platform/vita"),
                                     "-I", str(ROOT / "port/platform"), str(cpp), "-o", str(exe)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
